import re
import unicodedata

import pandas as pd
from pandas import Series

from app.models import DatasetSession
from app.services.date_utils import date_parse_ratio, parse_common_dates


def build_profile(dataset: DatasetSession) -> dict:
    df = dataset.dataframe
    column_types = {column: _infer_type(column, df[column]) for column in df.columns}
    date_suggestions = _date_conversion_suggestions(df, column_types)

    return {
        "dataset_id": dataset.dataset_id,
        "file_name": dataset.file_name,
        "ingest_report": dataset.ingest_report or {},
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "column_types": column_types,
        "numeric_columns": [column for column, kind in column_types.items() if kind == "numeric"],
        "categorical_columns": [column for column, kind in column_types.items() if kind == "categorical"],
        "datetime_columns": [column for column, kind in column_types.items() if kind == "datetime"],
        "date_candidates": _date_candidates(column_types, date_suggestions),
        "date_conversion_suggestions": date_suggestions,
        "missing_values": df.isna().sum().astype(int).to_dict(),
        "numeric_summary": _numeric_summary(df),
    }


def _infer_type(column: str, series: Series) -> str:
    normalized_column = _normalize_text(column)
    column_hint = any(
        term in normalized_column
        for term in ["data", "date", "mes", "month", "trim", "trimestre", "quarter", "periodo", "competencia", "timestamp"]
    )

    if pd.api.types.is_numeric_dtype(series):
        if column_hint and date_parse_ratio(series.dropna().head(80)) >= 0.8:
            return "datetime"
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    sample = series.dropna().astype(str).head(50)
    if sample.empty:
        return "categorical"

    period_like = max(
        sample.str.match(r"^\d{4}[/-]\d{1,2}$").mean(),
        sample.str.match(r"^\d{1,2}[/-]\d{4}$").mean(),
        sample.str.match(r"^\d{4}[-_/ ]?(t|q|tri|trim)\d$", case=False).mean(),
        sample.str.match(r"^(t|q|tri|trim)\d[-_/ ]?\d{2,4}$", case=False).mean(),
    )
    if period_like >= 0.65:
        return "categorical"

    full_date_like = (
        sample.str.match(r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}$")
        | sample.str.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$")
        | sample.str.match(r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}[ T]\d{1,2}:\d{2}")
    )
    if full_date_like.mean() < 0.65 and not column_hint:
        return "categorical"

    parsed_dates = parse_common_dates(sample)
    if len(parsed_dates) > 0 and parsed_dates.notna().mean() >= 0.8:
        return "datetime"

    return "categorical"


def _numeric_summary(df: pd.DataFrame) -> dict:
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return {}

    summary = numeric_df.describe().round(2).where(pd.notnull(numeric_df.describe()), None)
    return summary.to_dict()


def _date_conversion_suggestions(df: pd.DataFrame, column_types: dict[str, str]) -> list[dict]:
    suggestions: list[dict] = []
    for column, kind in column_types.items():
        if kind == "datetime":
            continue

        suggestion = _date_conversion_suggestion(column, df[column])
        if suggestion:
            suggestions.append(suggestion)

    return suggestions


def _date_conversion_suggestion(column: str, series: Series) -> dict | None:
    sample = series.dropna().astype(str).str.strip()
    sample = sample[sample.ne("")].head(80)
    if sample.empty:
        return None

    normalized_column = _normalize_text(column)
    month_ratio = max(
        sample.str.match(r"^\d{4}[/-]\d{1,2}$").mean(),
        sample.str.match(r"^\d{1,2}[/-]\d{4}$").mean(),
        sample.str.match(r"^(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*[\s_/-]?\d{2,4}$", case=False).mean(),
    )
    quarter_ratio = max(
        sample.str.match(r"^\d{4}[-_/ ]?(t|q|tri|trim)\d$", case=False).mean(),
        sample.str.match(r"^(t|q|tri|trim)\d[-_/ ]?\d{2,4}$", case=False).mean(),
        sample.str.match(r"^\d[\s_/-]?[tq]\d{2,4}$", case=False).mean(),
    )
    unix_ratio = sample.map(_looks_like_unix_timestamp).mean()

    column_hint = any(term in normalized_column for term in ["mes", "month", "trim", "trimestre", "quarter", "periodo", "competencia"])
    if month_ratio >= 0.65 or ("mes" in normalized_column and month_ratio >= 0.35):
        return {
            "column": column,
            "suggested_type": "month_period",
            "confidence": round(float(max(month_ratio, 0.65 if column_hint else 0)), 2),
            "message": f"A coluna {column} parece representar mes/competencia. Considere converter para periodo mensal antes de comparar tendencias.",
        }

    if quarter_ratio >= 0.65 or (("trim" in normalized_column or "trimestre" in normalized_column) and quarter_ratio >= 0.35):
        return {
            "column": column,
            "suggested_type": "quarter_period",
            "confidence": round(float(max(quarter_ratio, 0.65 if column_hint else 0)), 2),
            "message": f"A coluna {column} parece representar trimestre. Considere converter para periodo trimestral para analises de tendencia.",
        }

    if unix_ratio >= 0.8 or ("timestamp" in normalized_column and unix_ratio >= 0.35):
        return {
            "column": column,
            "suggested_type": "unix_timestamp",
            "confidence": round(float(max(unix_ratio, 0.65 if "timestamp" in normalized_column else 0)), 2),
            "message": f"A coluna {column} parece conter timestamp Unix. Considere converter para data antes de analisar eventos no tempo.",
        }

    return None


def _date_candidates(column_types: dict[str, str], suggestions: list[dict]) -> list[dict]:
    candidates = [
        {"column": column, "kind": "datetime", "confidence": 1.0}
        for column, kind in column_types.items()
        if kind == "datetime"
    ]
    candidates.extend(
        {
            "column": suggestion["column"],
            "kind": suggestion["suggested_type"],
            "confidence": suggestion["confidence"],
        }
        for suggestion in suggestions
    )
    return candidates


def _looks_like_unix_timestamp(value: str) -> bool:
    try:
        number = abs(float(str(value).strip()))
    except (TypeError, ValueError):
        return False
    return 946684800 <= number <= 4102444800 or 946684800000 <= number <= 4102444800000


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-zA-Z0-9_]+", "_", text.lower())
    return re.sub(r"_+", "_", text).strip("_")
