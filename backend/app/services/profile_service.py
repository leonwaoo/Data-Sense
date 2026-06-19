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
