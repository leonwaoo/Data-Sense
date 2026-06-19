import re
import unicodedata

import pandas as pd
from pandas import Series

from app.models import DatasetSession


def build_profile(dataset: DatasetSession) -> dict:
    df = dataset.dataframe
    column_types = {column: _infer_type(df[column]) for column in df.columns}

    return {
        "dataset_id": dataset.dataset_id,
        "file_name": dataset.file_name,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "column_types": column_types,
        "numeric_columns": [column for column, kind in column_types.items() if kind == "numeric"],
        "categorical_columns": [column for column, kind in column_types.items() if kind == "categorical"],
        "datetime_columns": [column for column, kind in column_types.items() if kind == "datetime"],
        "date_conversion_suggestions": _date_conversion_suggestions(df, column_types),
        "missing_values": df.isna().sum().astype(int).to_dict(),
        "numeric_summary": _numeric_summary(df),
    }


def _infer_type(series: Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    sample = series.dropna().astype(str).head(50)
    if sample.empty:
        return "categorical"

    iso_date_like = sample.str.match(r"^\d{4}-\d{1,2}-\d{1,2}$")
    br_date_like = sample.str.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$")
    date_like = iso_date_like | br_date_like
    if date_like.mean() < 0.8:
        return "categorical"

    dayfirst = iso_date_like.mean() < 0.8
    parsed_dates = pd.to_datetime(sample, errors="coerce", dayfirst=dayfirst)
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

        series = df[column]
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue

        suggestion = _date_conversion_suggestion(column, series)
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
        sample.str.match(r"^(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*[/-]?\d{2,4}$", case=False).mean(),
    )
    quarter_ratio = max(
        sample.str.match(r"^\d{4}[-_/ ]?(t|q|tri|trim)\d$", case=False).mean(),
        sample.str.match(r"^(t|q|tri|trim)\d[-_/ ]?\d{2,4}$", case=False).mean(),
        sample.str.match(r"^\d[tq]\d{2,4}$", case=False).mean(),
    )

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

    return None


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-zA-Z0-9_]+", "_", text.lower())
    return re.sub(r"_+", "_", text).strip("_")
