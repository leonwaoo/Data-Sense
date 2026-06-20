from app.models import DatasetSession


def build_quality_report(dataset: DatasetSession) -> dict:
    df = dataset.dataframe
    missing_by_column = df.isna().sum().astype(int)
    total_cells = max(df.shape[0] * df.shape[1], 1)
    missing_total = int(missing_by_column.sum())
    duplicate_rows = int(df.duplicated().sum())
    empty_columns = [column for column in df.columns if df[column].isna().all()]
    outliers, outlier_details = _detect_numeric_outliers(dataset)

    missing_penalty = min(45.0, (missing_total / total_cells) * 45)
    duplicate_penalty = min(25.0, (duplicate_rows / max(df.shape[0], 1)) * 25)
    empty_column_penalty = min(20.0, (len(empty_columns) / max(df.shape[1], 1)) * 20)
    outlier_penalty = min(10.0, (sum(outliers.values()) / max(df.shape[0], 1)) * 10)
    score_breakdown = [
        _score_item("Valores ausentes", 45, missing_penalty, f"{missing_total} celula(s) vazia(s) em {total_cells} celula(s)."),
        _score_item("Linhas duplicadas", 25, duplicate_penalty, f"{duplicate_rows} linha(s) duplicada(s)."),
        _score_item("Colunas vazias", 20, empty_column_penalty, f"{len(empty_columns)} coluna(s) totalmente vazia(s)."),
        _score_item("Outliers numericos", 10, outlier_penalty, f"{sum(outliers.values())} valor(es) fora do padrao IQR."),
    ]
    penalties = sum(item["lost_points"] for item in score_breakdown)
    score = max(0, round(100 - penalties))

    return {
        "score": score,
        "score_breakdown": score_breakdown,
        "missing_total": missing_total,
        "missing_by_column": missing_by_column.to_dict(),
        "duplicate_rows": duplicate_rows,
        "empty_columns": empty_columns,
        "numeric_outliers": outliers,
        "numeric_outlier_details": outlier_details,
        "recommendations": _build_recommendations(dataset, missing_total, duplicate_rows, empty_columns, outliers, outlier_details),
    }


def _detect_numeric_outliers(dataset: DatasetSession) -> tuple[dict[str, int], list[dict]]:
    outliers: dict[str, int] = {}
    details: list[dict] = []
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
        mask = (series < lower) | (series > upper)
        if not bool(mask.any()):
            mask, lower, upper = _ratio_outlier_mask(series, lower, upper)
        count = int(mask.sum())
        if count:
            outliers[column] = count
            details.extend(_outlier_detail_rows(column, series, mask, lower, upper))

    details.sort(key=lambda item: item["deviation_ratio"], reverse=True)
    return outliers, details[:12]


def _ratio_outlier_mask(series, lower: float, upper: float):
    if len(series) < 3:
        return series.astype(bool) & False, lower, upper

    median = float(series.median())
    if median == 0:
        return series.astype(bool) & False, lower, upper

    high_threshold = median * 5 if median > 0 else median / 5
    low_threshold = median / 5 if median > 0 else median * 5
    mask = (series > high_threshold) | (series < low_threshold)
    return mask, float(low_threshold), float(high_threshold)


def _outlier_detail_rows(column: str, series, mask, lower: float, upper: float) -> list[dict]:
    mean = float(series.mean())
    median = float(series.median())
    outlier_values = series[mask].copy()
    if outlier_values.empty:
        return []

    outlier_values = outlier_values.reindex((outlier_values - median).abs().sort_values(ascending=False).index)
    rows: list[dict] = []
    for index, value in outlier_values.head(3).items():
        numeric_value = float(value)
        baseline = abs(mean) if mean else max(abs(median), 1.0)
        deviation_ratio = abs(numeric_value - mean) / baseline
        try:
            row_index = int(index) + 1
        except (TypeError, ValueError):
            row_index = str(index)
        rows.append(
            {
                "column": column,
                "row_index": row_index,
                "value": round(numeric_value, 4),
                "mean": round(mean, 4),
                "deviation_ratio": round(float(deviation_ratio), 2),
                "lower_bound": round(float(lower), 4),
                "upper_bound": round(float(upper), 4),
            }
        )
    return rows


def _score_item(label: str, weight: int, lost_points: float, detail: str) -> dict:
    return {
        "label": label,
        "weight": weight,
        "lost_points": round(float(lost_points), 2),
        "detail": detail,
    }


def _build_recommendations(
    dataset: DatasetSession,
    missing_total: int,
    duplicate_rows: int,
    empty_columns: list[str],
    outliers: dict[str, int],
    outlier_details: list[dict],
) -> list[str]:
    recommendations: list[str] = []
    ingest_warnings = (dataset.ingest_report or {}).get("warnings", [])
    for warning in ingest_warnings[:2]:
        recommendations.append(f"Ingestao: {warning}")
    if missing_total:
        recommendations.append("Revisar colunas com valores ausentes antes de gerar conclusoes.")
    if duplicate_rows:
        recommendations.append("Validar linhas duplicadas para evitar contagem ou soma duplicada.")
    if empty_columns:
        recommendations.append("Remover ou preencher colunas totalmente vazias.")
    if outliers:
        if outlier_details:
            first = outlier_details[0]
            recommendations.append(
                f"Investigar outliers como {first['column']} na linha {first['row_index']} "
                f"(valor {first['value']})."
            )
        else:
            recommendations.append("Investigar outliers numericos que podem distorcer medias e totais.")

    if not recommendations:
        recommendations.append("Nenhum problema critico encontrado na auditoria inicial.")
    return recommendations
