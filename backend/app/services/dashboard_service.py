import re
import unicodedata
from functools import partial

import pandas as pd

from app.models import DatasetSession
from app.services.column_heuristics import (
    format_number as _format_number,
    is_adjustment_metric as _is_adjustment_metric,
    is_metric_noise,
    looks_like_identifier as _looks_like_identifier,
    metric_score as _metric_score,
    normalize_text as _normalize_text,
    slug as _slug,
)
from app.services.date_utils import parse_common_dates
from app.services.profile_service import build_profile
from app.services.quality_service import build_quality_report

VALUE_CANDIDATES = [
    "valor_total",
    "total_venda",
    "valor_liquido",
    "valor_bruto",
    "faturamento",
    "receita",
    "receita_bruta",
    "receita_liquida",
    "venda",
    "vendas",
    "valor_venda",
    "compra",
    "compras",
    "valor_compra",
    "custo",
    "custos",
    "despesa",
    "gasto",
    "valor",
    "total",
    "preco",
    "amount",
    "price",
    "lucro",
    "margem",
]
METRIC_NOISE_TERMS = [
    "id",
    "codigo",
    "cod",
    "nf",
    "nota_fiscal",
    "numero",
    "prazo",
    "dias",
    "avaliacao",
    "rating",
    "mes",
    "ano",
    "trim",
    "trimestre",
    "percentual",
    "taxa",
]
_is_metric_noise = partial(is_metric_noise, terms=METRIC_NOISE_TERMS)
QUANTITY_CANDIDATES = ["quantidade", "qtd", "volume", "unidade", "unidades", "units"]
DATE_CANDIDATES = ["data", "date", "mes", "month", "dia", "periodo", "competencia"]
DIMENSION_CANDIDATES = [
    ("produto", ["produto", "item", "sku", "servico", "produto_servico"]),
    ("fornecedor", ["fornecedor", "supplier", "vendor"]),
    ("cliente", ["cliente", "customer", "comprador"]),
    ("categoria", ["categoria", "segmento", "tipo", "classe", "familia"]),
    ("regiao", ["regiao", "estado", "cidade", "uf", "pais", "local"]),
    ("canal", ["canal", "origem", "midia", "loja", "vendedor"]),
    ("status", ["status", "situacao", "etapa"]),
]
DOMAIN_CANDIDATES = [
    ("vendas", ["venda", "vendas", "faturamento", "receita", "cliente", "produto", "canal"]),
    ("compras", ["compra", "compras", "fornecedor", "custo", "despesa", "gasto"]),
    ("clientes", ["cliente", "customer", "comprador", "segmento", "cidade", "estado"]),
    ("estoque", ["estoque", "produto", "sku", "quantidade", "qtd", "categoria"]),
    ("financeiro", ["receita", "despesa", "custo", "lucro", "margem", "saldo", "valor"]),
]


def build_dashboard(dataset: DatasetSession, filters: dict | None = None) -> dict:
    base_profile = build_profile(dataset)
    base_domain = _detect_domain(base_profile["column_names"])
    base_date_column = _select_date_column(dataset.dataframe, base_profile["datetime_columns"], base_profile["column_names"])
    base_dimensions = _select_dimensions(base_profile["categorical_columns"])
    filtered_dataset, applied_filters = _apply_filters(dataset, filters or {}, base_date_column, base_dimensions)

    df = filtered_dataset.dataframe
    profile = build_profile(filtered_dataset)
    quality = build_quality_report(filtered_dataset)
    domain = _detect_domain(profile["column_names"])
    main_metric = _select_main_metric(df, profile["numeric_columns"], domain["type"])
    date_column = _select_date_column(df, profile["datetime_columns"], profile["column_names"])
    dimensions = _select_dimensions(profile["categorical_columns"])

    kpis = _build_kpis(filtered_dataset, quality, main_metric, date_column)
    charts, insights = _build_charts(filtered_dataset, quality, main_metric, date_column, dimensions)
    insights.extend(_quality_insights(quality))

    if not charts:
        insights.append("Envie dados com colunas numericas, datas ou categorias para montar graficos automaticos mais completos.")

    return {
        "title": "Dashboard automatico",
        "subtitle": _dashboard_subtitle(domain, main_metric, date_column, dimensions),
        "domain": domain,
        "kpis": kpis,
        "charts": charts,
        "insights": insights[:6],
        "filters": _build_filter_options(dataset, base_date_column, base_dimensions, applied_filters),
        "quality": {
            "score": quality["score"],
            "score_breakdown": quality.get("score_breakdown", []),
            "missing_total": quality["missing_total"],
            "duplicate_rows": quality["duplicate_rows"],
            "empty_columns": quality["empty_columns"],
            "numeric_outliers": quality.get("numeric_outliers", {}),
            "numeric_outlier_details": quality.get("numeric_outlier_details", []),
        },
    }


def _build_kpis(
    dataset: DatasetSession,
    quality: dict,
    main_metric: str | None,
    date_column: str | None,
) -> list[dict]:
    df = dataset.dataframe
    total_cells = max(df.shape[0] * df.shape[1], 1)
    missing_rate = quality["missing_total"] / total_cells
    duplicate_rate = quality["duplicate_rows"] / max(df.shape[0], 1)

    kpis = [
        {
            "label": "Registros",
            "value": _format_number(df.shape[0]),
            "detail": f"{df.shape[1]} colunas no dataset",
            "tone": "neutral",
        },
        {
            "label": "Score de qualidade",
            "value": f"{quality['score']}/100",
            "detail": _quality_label(quality["score"]),
            "tone": "good" if quality["score"] >= 85 else "warning" if quality["score"] >= 65 else "danger",
        },
        {
            "label": "Valores nulos",
            "value": _format_number(quality["missing_total"]),
            "detail": f"{missing_rate:.1%} das celulas",
            "tone": "good" if quality["missing_total"] == 0 else "warning",
        },
        {
            "label": "Duplicatas",
            "value": _format_number(quality["duplicate_rows"]),
            "detail": f"{duplicate_rate:.1%} das linhas",
            "tone": "good" if quality["duplicate_rows"] == 0 else "warning",
        },
    ]

    if main_metric:
        series = pd.to_numeric(df[main_metric], errors="coerce").dropna()
        if not series.empty:
            kpis.insert(
                1,
                {
                    "label": f"Total de {main_metric}",
                    "value": _format_number(round(float(series.sum()), 2)),
                    "detail": f"Media: {_format_number(round(float(series.mean()), 2))}",
                    "tone": "accent",
                },
            )

    if date_column:
        parsed_dates = _parse_dates(df[date_column]).dropna()
        if not parsed_dates.empty:
            kpis.append(
                {
                    "label": "Periodo",
                    "value": str(parsed_dates.dt.to_period("M").nunique()),
                    "detail": f"{parsed_dates.min().date()} ate {parsed_dates.max().date()}",
                    "tone": "neutral",
                }
            )

    return kpis[:6]


def _build_charts(
    dataset: DatasetSession,
    quality: dict,
    main_metric: str | None,
    date_column: str | None,
    dimensions: list[tuple[str, str]],
) -> tuple[list[dict], list[str]]:
    charts: list[dict] = []
    insights: list[str] = []

    if main_metric and date_column:
        monthly = _monthly_chart(dataset, date_column, main_metric)
        if monthly:
            charts.append(monthly["chart"])
            insights.append(monthly["insight"])

    if main_metric:
        for label, column in dimensions[:3]:
            ranking = _ranking_chart(dataset, column, main_metric, label)
            if ranking:
                charts.append(ranking["chart"])
                insights.append(ranking["insight"])

    missing_chart = _missing_chart(dataset, quality)
    if missing_chart:
        charts.append(missing_chart)

    charts.append(_quality_chart(dataset, quality))
    return charts[:5], insights


def _monthly_chart(dataset: DatasetSession, date_column: str, metric_column: str) -> dict | None:
    df = dataset.dataframe.copy()
    df["_periodo"] = _parse_dates(df[date_column]).dt.to_period("M").astype(str)
    df["_valor"] = pd.to_numeric(df[metric_column], errors="coerce")
    df = df[df["_periodo"].ne("NaT") & df["_valor"].notna()]
    if df.empty:
        return None

    result = (
        df.groupby("_periodo", as_index=False)["_valor"]
        .sum()
        .rename(columns={"_periodo": "periodo", "_valor": "total"})
        .sort_values("periodo")
        .round(2)
    )
    if result.empty:
        return None

    best = result.sort_values("total", ascending=False).iloc[0]
    movement = _monthly_movement(result)
    return {
        "chart": {
            "id": "evolucao_mensal",
            "title": "Evolucao por mes",
            "subtitle": f"Soma de {metric_column} por {date_column}",
            "type": "line",
            "x": "periodo",
            "y": "total",
            "data": result.to_dict(orient="records"),
            "insight": movement or f"Maior periodo: {best['periodo']} com {_format_number(best['total'])}.",
            "available_types": ["line", "area", "bar"],
        },
        "insight": movement or f"Oportunidade: a maior soma mensal de {metric_column} aparece em {best['periodo']}.",
    }


def _ranking_chart(dataset: DatasetSession, group_column: str, metric_column: str, label: str) -> dict | None:
    df = dataset.dataframe.copy()
    df["_grupo"] = df[group_column].astype("string")
    df["_valor"] = pd.to_numeric(df[metric_column], errors="coerce")
    df = df[df["_grupo"].notna() & df["_valor"].notna()]
    if df.empty:
        return None

    result = (
        df.groupby("_grupo", as_index=False)["_valor"]
        .sum()
        .rename(columns={"_grupo": "grupo", "_valor": "total"})
        .sort_values("total", ascending=False)
        .head(8)
        .round(2)
    )
    if result.empty:
        return None

    top = result.iloc[0]
    share = float(top["total"] / result["total"].sum()) if float(result["total"].sum()) else 0
    return {
        "chart": {
            "id": f"ranking_{_slug(label)}",
            "title": f"Ranking por {label}",
            "subtitle": f"Soma de {metric_column} por {group_column}",
            "type": "bar",
            "x": "grupo",
            "y": "total",
            "data": result.to_dict(orient="records"),
            "insight": f"Principal {label}: {top['grupo']} com {_format_number(top['total'])} ({share:.1%} do top 8).",
            "available_types": ["bar", "line", "pie"],
        },
        "insight": f"Oportunidade: {top['grupo']} lidera o ranking por {label} com {share:.1%} do top 8.",
    }


def _missing_chart(dataset: DatasetSession, quality: dict) -> dict | None:
    missing = pd.Series(quality.get("missing_by_column", {}), dtype="int64").sort_values(ascending=False).head(8)
    if missing.empty:
        return None

    if int(missing.sum()) == 0:
        data = [{"coluna": "Sem nulos", "valores_ausentes": 0}]
    else:
        data = (
            missing.reset_index()
            .rename(columns={"index": "coluna", 0: "valores_ausentes"})
            .to_dict(orient="records")
        )

    return {
        "id": "nulos_por_coluna",
        "title": "Nulos por coluna",
        "subtitle": _display_label(dataset.file_name, 64),
        "type": "bar",
        "x": "coluna",
        "y": "valores_ausentes",
        "data": data,
        "insight": "Colunas com mais vazios aparecem primeiro.",
        "available_types": ["bar"],
    }


def _quality_chart(dataset: DatasetSession, quality: dict) -> dict:
    df = dataset.dataframe
    total_cells = max(df.shape[0] * df.shape[1], 1)
    missing_rate = round((quality["missing_total"] / total_cells) * 100, 2)
    duplicate_rate = round((quality["duplicate_rows"] / max(df.shape[0], 1)) * 100, 2)
    outlier_count = sum(quality.get("numeric_outliers", {}).values())
    outlier_rate = round((outlier_count / max(df.shape[0], 1)) * 100, 2)

    return {
        "id": "score_qualidade",
        "title": "Score de qualidade",
        "subtitle": "Score, nulos, duplicatas e outliers em pontos percentuais",
        "type": "bar",
        "x": "indicador",
        "y": "valor",
        "data": [
            {"indicador": "Qualidade", "valor": int(quality["score"])},
            {"indicador": "Nulos %", "valor": missing_rate},
            {"indicador": "Duplicatas %", "valor": duplicate_rate},
            {"indicador": "Outliers %", "valor": outlier_rate},
        ],
        "insight": _quality_label(quality["score"]),
        "available_types": ["bar"],
    }


def _quality_insights(quality: dict) -> list[str]:
    insights: list[str] = []
    if quality["missing_total"]:
        insights.append(f"Qualidade: existem {_format_number(quality['missing_total'])} valores nulos para revisar.")
    if quality["duplicate_rows"]:
        insights.append(f"Risco: existem {_format_number(quality['duplicate_rows'])} linhas duplicadas.")
    if quality["score"] < 75:
        insights.append("Risco: o score de qualidade recomenda validar a base antes de tomar decisoes.")
    outlier_details = quality.get("numeric_outlier_details", [])
    if outlier_details:
        first = outlier_details[0]
        insights.append(
            f"Outlier: {first['column']} na linha {first['row_index']} tem valor {_format_number(first['value'])}."
        )
    if not insights:
        insights.append("Qualidade: a auditoria inicial nao encontrou nulos ou duplicatas relevantes.")
    return insights


def _monthly_movement(result: pd.DataFrame) -> str | None:
    if result.shape[0] < 2:
        return None

    first = result.iloc[0]
    last = result.iloc[-1]
    first_total = float(first["total"] or 0)
    last_total = float(last["total"] or 0)
    if first_total == 0:
        return f"Tendencia: o ultimo periodo fechou em {_format_number(last_total)}."

    variation = (last_total - first_total) / abs(first_total)
    direction = "cresceu" if variation >= 0 else "caiu"
    return f"Tendencia: de {first['periodo']} a {last['periodo']}, o total {direction} {abs(variation):.1%}."


def _apply_filters(
    dataset: DatasetSession,
    filters: dict,
    date_column: str | None,
    dimensions: list[tuple[str, str]],
) -> tuple[DatasetSession, dict]:
    df = dataset.dataframe.copy()
    applied: dict = {
        "date_from": None,
        "date_to": None,
        "categories": {},
        "applied_count": 0,
        "rows_before_filter": int(dataset.dataframe.shape[0]),
    }

    date_from = str(filters.get("date_from") or "").strip()
    date_to = str(filters.get("date_to") or "").strip()
    if date_column and (date_from or date_to):
        parsed_dates = _parse_dates(df[date_column])
        if date_from:
            start = pd.to_datetime(date_from, errors="coerce")
            if pd.notna(start):
                df = df[parsed_dates >= start]
                applied["date_from"] = str(start.date())
                applied["applied_count"] += 1
        if date_to:
            end = pd.to_datetime(date_to, errors="coerce")
            if pd.notna(end):
                df = df[parsed_dates <= end]
                applied["date_to"] = str(end.date())
                applied["applied_count"] += 1

    category_filters = filters.get("categories") if isinstance(filters.get("categories"), dict) else {}
    available_dimension_columns = {column for _, column in dimensions}
    for column, selected_values in category_filters.items():
        if column not in available_dimension_columns or not isinstance(selected_values, list) or not selected_values:
            continue

        values = {str(value) for value in selected_values if str(value).strip()}
        if not values:
            continue

        df = df[df[column].astype("string").isin(values)]
        applied["categories"][column] = sorted(values)
        applied["applied_count"] += 1

    applied["rows_after_filter"] = int(df.shape[0])
    return DatasetSession(
        dataset_id=dataset.dataset_id,
        file_name=dataset.file_name,
        dataframe=df.reset_index(drop=True),
        ingest_report=dataset.ingest_report,
    ), applied


def _build_filter_options(
    dataset: DatasetSession,
    date_column: str | None,
    dimensions: list[tuple[str, str]],
    applied_filters: dict,
) -> dict:
    date_filter = None
    if date_column:
        parsed_dates = _parse_dates(dataset.dataframe[date_column]).dropna()
        if not parsed_dates.empty:
            date_filter = {
                "column": date_column,
                "min": str(parsed_dates.min().date()),
                "max": str(parsed_dates.max().date()),
                "selected_from": applied_filters.get("date_from"),
                "selected_to": applied_filters.get("date_to"),
            }

    category_filters: list[dict] = []
    for label, column in dimensions[:4]:
        series = dataset.dataframe[column].dropna().astype(str)
        if series.empty:
            continue

        values = [
            {"value": str(value), "count": int(count)}
            for value, count in series.value_counts().head(10).items()
        ]
        category_filters.append(
            {
                "label": label,
                "column": column,
                "values": values,
                "selected": applied_filters.get("categories", {}).get(column, []),
            }
        )

    return {
        "date": date_filter,
        "categories": category_filters,
        "applied_count": applied_filters["applied_count"],
        "rows_before_filter": applied_filters["rows_before_filter"],
        "rows_after_filter": applied_filters["rows_after_filter"],
    }


def _detect_domain(column_names: list[str]) -> dict:
    normalized_columns = [_normalize_text(column) for column in column_names]
    scores: list[tuple[str, int, list[str]]] = []

    for domain, candidates in DOMAIN_CANDIDATES:
        hits = sorted({candidate for candidate in candidates for column in normalized_columns if candidate in column})
        scores.append((domain, len(hits), hits[:4]))

    domain, score, hits = max(scores, key=lambda item: item[1])
    if score == 0:
        return {
            "type": "generico",
            "label": "Dataset generico",
            "confidence": 0.35,
            "reasons": ["Nao foram encontradas colunas de dominio claras."],
        }

    confidence = min(0.95, 0.48 + score * 0.12)
    return {
        "type": domain,
        "label": f"Dataset de {domain}",
        "confidence": round(confidence, 2),
        "reasons": [f"Colunas reconhecidas: {', '.join(hits)}"],
    }


def _select_main_metric(df: pd.DataFrame, numeric_columns: list[str], domain: str) -> str | None:
    if not numeric_columns:
        return None

    domain_candidates = {
        "vendas": ["faturamento", "receita", "venda", "vendas", "valor"],
        "compras": ["compra", "compras", "custo", "despesa", "gasto", "valor"],
        "financeiro": ["receita", "despesa", "custo", "lucro", "margem", "valor"],
        "estoque": ["valor", "quantidade", "qtd", "estoque", "preco"],
        "clientes": ["valor", "receita", "venda", "compras"],
    }.get(domain, VALUE_CANDIDATES)

    scored_columns = [
        (
            _metric_score(
                df,
                column,
                domain=domain,
                domain_candidates=domain_candidates,
                value_candidates=VALUE_CANDIDATES,
                metric_noise_terms=METRIC_NOISE_TERMS,
                zero_sum_penalty=True,
            ),
            column,
        )
        for column in numeric_columns
    ]
    scored_columns.sort(reverse=True)
    if scored_columns and scored_columns[0][0] > 0:
        return scored_columns[0][1]

    non_identifier_columns = [column for column in numeric_columns if not _looks_like_identifier(column)]
    non_noise_columns = [
        column
        for column in non_identifier_columns
        if not _is_metric_noise(column) and not _is_adjustment_metric(column)
    ]
    candidates = non_noise_columns or non_identifier_columns or numeric_columns
    return max(candidates, key=lambda column: pd.to_numeric(df[column], errors="coerce").clip(lower=0).sum(skipna=True))


def _select_date_column(df: pd.DataFrame, datetime_columns: list[str], column_names: list[str]) -> str | None:
    preferred = _first_matching(datetime_columns, DATE_CANDIDATES)
    if preferred:
        return preferred
    if datetime_columns:
        return datetime_columns[0]

    for column in column_names:
        if not _first_matching([column], DATE_CANDIDATES):
            continue
        parsed = _parse_dates(df[column])
        if parsed.notna().mean() >= 0.6:
            return column

    return None


def _select_dimensions(categorical_columns: list[str]) -> list[tuple[str, str]]:
    dimensions: list[tuple[str, str]] = []
    used: set[str] = set()
    for label, candidates in DIMENSION_CANDIDATES:
        column = _first_matching(categorical_columns, candidates)
        if column and column not in used:
            dimensions.append((label, column))
            used.add(column)

    for column in categorical_columns:
        if column not in used:
            dimensions.append(("grupo", column))
            used.add(column)

    return dimensions


def _dashboard_subtitle(
    domain: dict,
    main_metric: str | None,
    date_column: str | None,
    dimensions: list[tuple[str, str]],
) -> str:
    parts = [domain["label"]]
    if main_metric:
        parts.append(f"metrica principal: {_display_label(main_metric, 36)}")
    if date_column:
        parts.append(f"tempo: {_display_label(date_column, 36)}")
    if dimensions:
        parts.append(f"ranking: {_display_label(dimensions[0][1], 36)}")
    return " | ".join(parts)


def _parse_dates(series: pd.Series) -> pd.Series:
    return parse_common_dates(series)


def _first_matching(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        for column in columns:
            if candidate in _normalize_text(column):
                return column
    return None


def _quality_label(score: int) -> str:
    if score >= 90:
        return "Base muito consistente"
    if score >= 75:
        return "Base boa com pontos de atencao"
    if score >= 55:
        return "Base exige revisao antes de decisoes"
    return "Base critica para analise"


def _display_label(value: str, limit: int = 64) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.category(character).startswith("C"))
    text = re.sub(r"[^\w\s.,:/()%-]+", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 3, 1)].rstrip()}..."
