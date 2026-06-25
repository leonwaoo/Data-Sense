import pandas as pd

from app.services.date_utils import date_parse_ratio, parse_common_dates


def test_parse_common_dates_accepts_brazilian_periods_and_quarters() -> None:
    values = pd.Series(["jan/2024", "marco-24", "Q1/2025", "2025-T3"])

    parsed = parse_common_dates(values)

    assert parsed.dt.strftime("%Y-%m").tolist() == ["2024-01", "2024-03", "2025-01", "2025-07"]


def test_parse_common_dates_accepts_unix_seconds_and_milliseconds() -> None:
    parsed = parse_common_dates(pd.Series([1704067200, 1704067200000]))

    assert parsed.dt.strftime("%Y-%m-%d").tolist() == ["2024-01-01", "2024-01-01"]


def test_date_parse_ratio_counts_period_text() -> None:
    assert date_parse_ratio(pd.Series(["01-JAN", "02-FEV", "texto solto"])) >= 2 / 3
