import re
import warnings
from typing import Any

import pandas as pd

MONTH_ALIASES = {
    "jan": 1,
    "janeiro": 1,
    "feb": 2,
    "fev": 2,
    "fevereiro": 2,
    "mar": 3,
    "marco": 3,
    "marco": 3,
    "apr": 4,
    "abr": 4,
    "abril": 4,
    "may": 5,
    "mai": 5,
    "maio": 5,
    "jun": 6,
    "junho": 6,
    "jul": 7,
    "julho": 7,
    "aug": 8,
    "ago": 8,
    "agosto": 8,
    "sep": 9,
    "set": 9,
    "setembro": 9,
    "oct": 10,
    "out": 10,
    "outubro": 10,
    "nov": 11,
    "novembro": 11,
    "dec": 12,
    "dez": 12,
    "dezembro": 12,
}


def parse_common_dates(series: pd.Series) -> pd.Series:
    values = series if isinstance(series, pd.Series) else pd.Series(series)
    parsed = _best_pandas_datetime(values)
    missing_mask = parsed.isna()
    if not missing_mask.any():
        return parsed

    period_dates = values[missing_mask].map(_parse_period_text)
    parsed.loc[missing_mask] = period_dates
    missing_mask = parsed.isna()
    if not missing_mask.any():
        return parsed

    unix_dates = values[missing_mask].map(_parse_unix_timestamp)
    parsed.loc[missing_mask] = unix_dates
    return parsed


def date_parse_ratio(series: pd.Series) -> float:
    sample = series.dropna()
    if sample.empty:
        return 0.0
    parsed = parse_common_dates(sample)
    return float(parsed.notna().sum() / len(sample))


def looks_like_period_text(value: Any) -> bool:
    return pd.notna(_parse_period_text(value))


def _best_pandas_datetime(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed_default = pd.to_datetime(series, errors="coerce")
        parsed_dayfirst = pd.to_datetime(series, errors="coerce", dayfirst=True)

    return parsed_dayfirst if parsed_dayfirst.notna().sum() > parsed_default.notna().sum() else parsed_default


def _parse_period_text(value: Any):
    if pd.isna(value):
        return pd.NaT

    text = str(value).strip().lower()
    if not text:
        return pd.NaT

    normalized = (
        text.replace("ç", "c")
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
    )

    match = re.fullmatch(r"(\d{4})[/-](\d{1,2})", normalized)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        return _timestamp_from_year_month(year, month)

    match = re.fullmatch(r"(\d{1,2})[/-](\d{4})", normalized)
    if match:
        month = int(match.group(1))
        year = int(match.group(2))
        return _timestamp_from_year_month(year, month)

    match = re.fullmatch(r"([a-z]{3,12})[\s_/-]*(\d{2,4})", normalized)
    if match:
        month = MONTH_ALIASES.get(match.group(1)[:3], MONTH_ALIASES.get(match.group(1)))
        year = _normalize_year(match.group(2))
        return _timestamp_from_year_month(year, month) if month else pd.NaT

    match = re.fullmatch(r"(\d{4})[\s_/-]*(?:q|t|tri|trim)([1-4])", normalized)
    if match:
        year = int(match.group(1))
        quarter = int(match.group(2))
        return _timestamp_from_year_month(year, (quarter - 1) * 3 + 1)

    match = re.fullmatch(r"(?:q|t|tri|trim)([1-4])[\s_/-]*(\d{2,4})", normalized)
    if match:
        quarter = int(match.group(1))
        year = _normalize_year(match.group(2))
        return _timestamp_from_year_month(year, (quarter - 1) * 3 + 1)

    match = re.fullmatch(r"([1-4])[\s_/-]*(?:q|t)(\d{2,4})", normalized)
    if match:
        quarter = int(match.group(1))
        year = _normalize_year(match.group(2))
        return _timestamp_from_year_month(year, (quarter - 1) * 3 + 1)

    return pd.NaT


def _parse_unix_timestamp(value: Any):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return pd.NaT

    absolute = abs(number)
    if 946684800 <= absolute <= 4102444800:
        return pd.to_datetime(number, unit="s", errors="coerce")
    if 946684800000 <= absolute <= 4102444800000:
        return pd.to_datetime(number, unit="ms", errors="coerce")
    return pd.NaT


def _timestamp_from_year_month(year: int, month: int | None):
    if not month or month < 1 or month > 12 or year < 1900 or year > 2200:
        return pd.NaT
    return pd.Timestamp(year=year, month=month, day=1)


def _normalize_year(value: str) -> int:
    year = int(value)
    if year < 100:
        return 2000 + year if year < 70 else 1900 + year
    return year
