from app.models import DatasetSession


def build_quality_report(dataset: DatasetSession) -> dict:
    df = dataset.dataframe
    missing_by_column = df.isna().sum().astype(int)
    total_cells = max(df.shape[0] * df.shape[1], 1)
    missing_total = int(missing_by_column.sum())
    duplicate_rows = int(df.duplicated().sum())
    empty_columns = [column for column in df.columns if df[column].isna().all()]
    outliers = _detect_numeric_outliers(dataset)

    penalties = (
        (missing_total / total_cells) * 45
        + (duplicate_rows / max(df.shape[0], 1)) * 25
        + (len(empty_columns) / max(df.shape[1], 1)) * 20
    )
    score = max(0, round(100 - penalties))

    return {
        "score": score,
        "missing_total": missing_total,
        "missing_by_column": missing_by_column.to_dict(),
        "duplicate_rows": duplicate_rows,
        "empty_columns": empty_columns,
        "numeric_outliers": outliers,
        "recommendations": _build_recommendations(missing_total, duplicate_rows, empty_columns, outliers),
    }


def _detect_numeric_outliers(dataset: DatasetSession) -> dict[str, int]:
    outliers: dict[str, int] = {}
    numeric_df = dataset.dataframe.select_dtypes(include="number")

    for column in numeric_df.columns:
        series = numeric_df[column].dropna()
        if series.empty:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count = int(((series < lower) | (series > upper)).sum())
        if count:
            outliers[column] = count

    return outliers


def _build_recommendations(
    missing_total: int,
    duplicate_rows: int,
    empty_columns: list[str],
    outliers: dict[str, int],
) -> list[str]:
    recommendations: list[str] = []
    if missing_total:
        recommendations.append("Revisar colunas com valores ausentes antes de gerar conclusoes.")
    if duplicate_rows:
        recommendations.append("Validar linhas duplicadas para evitar contagem ou soma duplicada.")
    if empty_columns:
        recommendations.append("Remover ou preencher colunas totalmente vazias.")
    if outliers:
        recommendations.append("Investigar outliers numericos que podem distorcer medias e totais.")

    if not recommendations:
        recommendations.append("Nenhum problema critico encontrado na auditoria inicial.")
    return recommendations

