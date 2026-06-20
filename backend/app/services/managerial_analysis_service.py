import re
import unicodedata
from typing import Any

import pandas as pd

from app.models import DatasetSession
from app.services.date_utils import parse_common_dates
from app.services.profile_service import build_profile


DOMAIN_RULES = [
    {
        "type": "estoque_operacao",
        "label": "Estoque e operacao",
        "terms": ["estoque", "inventario", "volume", "industrializado", "producao", "fabrica", "ton", "sku", "produto", "custo"],
        "primary_metrics": ["estoque_total", "estoque", "saldo_estoque", "inventario", "stock"],
        "support_groups": {
            "estoque_fabrica": ["estoque_fabrica", "fabrica", "warehouse", "factory_stock"],
            "volume_operacional": ["volume", "industrializado", "producao", "quantidade", "qtd"],
            "custo": ["custo", "cost", "preco", "price"],
        },
        "dimensions": ["produto", "sku", "categoria", "fy_gaap", "gaap", "fabrica", "local", "familia"],
    },
    {
        "type": "vendas",
        "label": "Vendas e receita",
        "terms": ["venda", "receita", "faturamento", "cliente", "produto", "canal", "valor_total"],
        "primary_metrics": ["valor_total", "receita", "faturamento", "valor_venda", "venda", "sales", "revenue"],
        "support_groups": {
            "quantidade": ["quantidade", "qtd", "volume", "unidade"],
            "desconto": ["desconto", "abatimento"],
            "custo": ["custo", "cost"],
        },
        "dimensions": ["produto", "cliente", "categoria", "canal", "regiao", "vendedor"],
    },
    {
        "type": "compras",
        "label": "Compras e fornecedores",
        "terms": ["compra", "fornecedor", "custo", "despesa", "pedido", "prazo"],
        "primary_metrics": ["valor_compra", "compra", "custo", "despesa", "gasto", "valor_total"],
        "support_groups": {
            "quantidade": ["quantidade", "qtd", "volume", "unidade"],
            "prazo": ["prazo", "lead_time", "dias"],
        },
        "dimensions": ["fornecedor", "produto", "categoria", "comprador", "status"],
    },
    {
        "type": "financeiro",
        "label": "Financeiro",
        "terms": ["receita", "despesa", "custo", "lucro", "margem", "saldo", "valor"],
        "primary_metrics": ["receita", "despesa", "custo", "lucro", "saldo", "valor_total", "valor"],
        "support_groups": {
            "margem": ["margem", "margin"],
            "quantidade": ["quantidade", "qtd", "volume"],
        },
        "dimensions": ["categoria", "centro_custo", "conta", "cliente", "fornecedor"],
    },
]

TIME_TERMS = ["data", "date", "periodo", "competencia", "mes", "month", "ano", "year"]
YEAR_TERMS = ["ano", "year", "exercicio"]
MONTH_TERMS = ["mes", "month", "competencia"]
MONTH_ALIASES = {
    "jan": 1,
    "fev": 2,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "apr": 4,
    "mai": 5,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "aug": 8,
    "set": 9,
    "sep": 9,
    "out": 10,
    "oct": 10,
    "nov": 11,
    "dez": 12,
    "dec": 12,
}


def build_managerial_analysis(dataset: DatasetSession) -> dict:
    df = dataset.dataframe.copy()
    profile = build_profile(dataset)
    domain = _detect_analysis_domain(profile["column_names"])
    metric_map = _map_metrics(df, profile, domain)
    time_context = _build_time_context(df, profile)
    dimensions = _select_dimensions(profile["column_names"], domain)

    context = {
        "domain": domain,
        "metric_map": metric_map,
        "time": {
            "available": bool(time_context["available"]),
            "label": time_context.get("label"),
            "columns": time_context.get("columns", []),
        },
        "dimensions": dimensions,
        "limitations": _context_limitations(metric_map, time_context, dimensions),
    }

    if not metric_map["primary_metric"] or not time_context["available"]:
        return _fallback_analysis(dataset, profile, context)

    diagnostic = _build_variation_diagnostic(df, metric_map, time_context, dimensions, domain)
    return {
        "mode": "managerial_deep_dive",
        "title": "Analise gerencial profunda",
        "summary": diagnostic["summary"],
        "context": context,
        "kpis": diagnostic["kpis"],
        "insights": diagnostic["insights"],
        "variations": diagnostic["variations"],
        "driver_evidence": diagnostic["driver_evidence"],
        "alerts": diagnostic["alerts"],
        "recommendations": diagnostic["recommendations"],
        "suggested_questions": _suggested_questions(domain["type"], metric_map, dimensions),
        "ai_evidence_package": diagnostic["ai_evidence_package"],
    }


def _build_variation_diagnostic(
    df: pd.DataFrame,
    metric_map: dict,
    time_context: dict,
    dimensions: list[dict],
    domain: dict,
) -> dict:
    primary_metric = metric_map["primary_metric"]
    period_series = time_context["series"]
    prepared = df.copy()
    prepared["_periodo"] = period_series.dt.to_period("M").astype(str)
    prepared["_periodo_data"] = period_series
    prepared["_valor_principal"] = pd.to_numeric(prepared[primary_metric], errors="coerce")
    prepared = prepared[prepared["_periodo"].ne("NaT") & prepared["_valor_principal"].notna()]

    if prepared.empty:
        return _empty_diagnostic(metric_map, domain, "A coluna de tempo foi detectada, mas nao gerou periodos validos para diagnostico.")

    period_metrics = _period_metrics(prepared, metric_map)
    period_metrics["variacao"] = period_metrics["valor"].diff()
    period_metrics["variacao_pct"] = period_metrics["valor"].pct_change().replace([float("inf"), float("-inf")], pd.NA)
    period_metrics["media_historica"] = period_metrics["valor"].expanding(min_periods=2).mean().shift(1)
    period_metrics["desvio_historico"] = period_metrics["valor"].expanding(min_periods=3).std().shift(1)
    period_metrics["z_score"] = (
        (period_metrics["valor"] - period_metrics["media_historica"]) / period_metrics["desvio_historico"]
    ).replace([float("inf"), float("-inf")], pd.NA)

    movement_rows = period_metrics.dropna(subset=["variacao"])
    if movement_rows.empty:
        return _empty_diagnostic(metric_map, domain, "Ha apenas um periodo valido; ainda nao e possivel comparar variacoes.")

    latest = movement_rows.iloc[-1]
    largest_increase = movement_rows.sort_values("variacao", ascending=False).iloc[0]
    largest_drop = movement_rows.sort_values("variacao", ascending=True).iloc[0]
    focus = largest_drop if abs(float(largest_drop["variacao"])) >= abs(float(largest_increase["variacao"])) else largest_increase
    dimension_evidence = _dimension_evidence(prepared, primary_metric, focus["periodo"], dimensions)
    driver_evidence = _driver_evidence(period_metrics, metric_map, focus)
    abnormal_periods = _abnormal_periods(movement_rows)

    focus_insight = _managerial_insight(
        focus,
        primary_metric,
        domain,
        dimension_evidence,
        driver_evidence,
    )
    latest_insight = _managerial_insight(
        latest,
        primary_metric,
        domain,
        _dimension_evidence(prepared, primary_metric, latest["periodo"], dimensions),
        _driver_evidence(period_metrics, metric_map, latest),
        insight_id="movimento_recente",
    )

    insights = [focus_insight]
    if latest["periodo"] != focus["periodo"]:
        insights.append(latest_insight)
    insights.extend(_abnormal_insights(abnormal_periods, primary_metric))

    summary = _executive_summary(period_metrics, primary_metric, domain, focus, latest, driver_evidence)
    alerts = _alerts(abnormal_periods, focus, metric_map, period_metrics)
    recommendations = _recommendations(domain["type"], focus, primary_metric, driver_evidence, abnormal_periods)

    return {
        "summary": summary,
        "kpis": _kpis(period_metrics, primary_metric, latest, largest_increase, largest_drop),
        "insights": insights[:5],
        "variations": {
            "latest": _movement_payload(latest),
            "largest_increase": _movement_payload(largest_increase),
            "largest_drop": _movement_payload(largest_drop),
            "abnormal_periods": [_movement_payload(row) for _, row in abnormal_periods.head(5).iterrows()],
            "trend": _trend_payload(period_metrics),
        },
        "driver_evidence": driver_evidence,
        "alerts": alerts,
        "recommendations": recommendations,
        "ai_evidence_package": {
            "domain": domain,
            "metric_map": metric_map,
            "period_movements": [_movement_payload(row) for _, row in movement_rows.tail(12).iterrows()],
            "largest_movements": {
                "increase": _movement_payload(largest_increase),
                "drop": _movement_payload(largest_drop),
            },
            "driver_evidence": driver_evidence,
            "abnormal_periods": [_movement_payload(row) for _, row in abnormal_periods.head(8).iterrows()],
            "limitations": [],
        },
    }


def _period_metrics(prepared: pd.DataFrame, metric_map: dict) -> pd.DataFrame:
    aggregations = {"valor": ("_valor_principal", "sum")}
    for group_name, column in metric_map["support_metrics"].items():
        prepared[f"_support_{group_name}"] = pd.to_numeric(prepared[column], errors="coerce")
        aggregations[group_name] = (f"_support_{group_name}", "sum" if _is_additive_support(group_name) else "mean")

    result = (
        prepared.groupby("_periodo", as_index=False)
        .agg(**aggregations)
        .rename(columns={"_periodo": "periodo"})
        .sort_values("periodo")
        .reset_index(drop=True)
    )
    return result


def _managerial_insight(
    movement: pd.Series,
    primary_metric: str,
    domain: dict,
    dimension_evidence: dict | None,
    driver_evidence: list[dict],
    insight_id: str = "principal_variacao",
) -> dict:
    variation = float(movement["variacao"])
    pct = _safe_float(movement.get("variacao_pct"))
    direction = "subiu" if variation >= 0 else "caiu"
    severity = _movement_severity(variation, pct)
    period_label = str(movement["periodo"])
    previous = float(movement["valor"] - variation)
    driver_lines = [driver["interpretation"] for driver in driver_evidence[:2] if driver.get("interpretation")]
    where = dimension_evidence.get("where") if dimension_evidence else "Movimento avaliado no total do dataset."

    possible_causes = driver_lines or [_generic_cause(domain["type"], direction)]
    return {
        "id": insight_id,
        "title": f"{'Alta' if variation >= 0 else 'Queda'} {severity['label'].lower()} em {primary_metric} em {period_label}",
        "severity": severity["tone"],
        "metric": primary_metric,
        "period": period_label,
        "what_changed": f"{primary_metric} {direction} em {period_label}.",
        "how_much": (
            f"Passou de {_format_number(previous)} para {_format_number(float(movement['valor']))}, "
            f"variacao de {_format_signed_number(variation)} ({_format_pct(pct)})."
        ),
        "where": where,
        "possible_causes": possible_causes,
        "managerial_impact": _managerial_impact(domain["type"], direction, severity["tone"]),
        "recommendation": _primary_recommendation(domain["type"], direction),
        "confidence": _confidence_level(driver_evidence, dimension_evidence, movement),
        "evidence": _movement_evidence(movement, driver_evidence, dimension_evidence),
    }


def _driver_evidence(period_metrics: pd.DataFrame, metric_map: dict, movement: pd.Series) -> list[dict]:
    drivers: list[dict] = []
    focus_index = int(movement.name) if isinstance(movement.name, int) else period_metrics.index[period_metrics["periodo"] == movement["periodo"]][0]
    previous_row = period_metrics.iloc[focus_index - 1] if focus_index > 0 else None
    direction = "subiu" if float(movement["variacao"]) >= 0 else "caiu"

    for group_name, column in metric_map["support_metrics"].items():
        if group_name not in period_metrics.columns:
            continue

        current_value = _safe_float(movement.get(group_name))
        previous_value = _safe_float(previous_row.get(group_name) if previous_row is not None else None)
        variation = None if current_value is None or previous_value is None else current_value - previous_value
        corr = _safe_corr(period_metrics["valor"], period_metrics[group_name])
        interpretation = _driver_interpretation(group_name, column, direction, current_value, previous_value, variation, corr)
        drivers.append(
            {
                "driver": group_name,
                "column": column,
                "current_value": current_value,
                "previous_value": previous_value,
                "variation": variation,
                "correlation_with_metric": corr,
                "interpretation": interpretation,
            }
        )

    drivers.sort(key=lambda item: abs(item["correlation_with_metric"] or 0), reverse=True)
    return drivers


def _dimension_evidence(prepared: pd.DataFrame, primary_metric: str, period: str, dimensions: list[dict]) -> dict | None:
    if not dimensions:
        return None

    dimension = dimensions[0]["column"]
    current = prepared[prepared["_periodo"] == period]
    if current.empty or dimension not in prepared.columns:
        return None

    previous_periods = sorted(prepared["_periodo"].dropna().unique().tolist())
    try:
        period_index = previous_periods.index(period)
    except ValueError:
        return None
    if period_index == 0:
        return None

    previous_period = previous_periods[period_index - 1]
    previous = prepared[prepared["_periodo"] == previous_period]
    current_grouped = current.groupby(dimension)["_valor_principal"].sum()
    previous_grouped = previous.groupby(dimension)["_valor_principal"].sum()
    movement = (current_grouped - previous_grouped).dropna().sort_values(key=lambda values: values.abs(), ascending=False)
    if movement.empty:
        top_current = current_grouped.sort_values(ascending=False).head(1)
        if top_current.empty:
            return None
        name = str(top_current.index[0])
        return {
            "dimension": dimension,
            "where": f"Principal recorte em {dimension}: {name}, com {_format_number(float(top_current.iloc[0]))}.",
            "top": [{"name": name, "variation": None, "current_value": float(top_current.iloc[0])}],
        }

    top = movement.head(3)
    top_payload = [
        {
            "name": str(name),
            "variation": round(float(value), 4),
            "current_value": round(float(current_grouped.get(name, 0)), 4),
            "previous_value": round(float(previous_grouped.get(name, 0)), 4),
        }
        for name, value in top.items()
    ]
    return {
        "dimension": dimension,
        "where": f"Maior contribuicao em {dimension}: {top_payload[0]['name']} ({_format_signed_number(top_payload[0]['variation'])}).",
        "top": top_payload,
    }


def _detect_analysis_domain(column_names: list[str]) -> dict:
    normalized = [_normalize_text(column) for column in column_names]
    scores = []
    for rule in DOMAIN_RULES:
        hits = sorted({term for term in rule["terms"] for column in normalized if term in column})
        metric_hits = sorted({term for term in rule["primary_metrics"] for column in normalized if term in column})
        score = len(hits) + len(metric_hits) * 2
        scores.append((score, rule, hits[:6], metric_hits[:4]))

    score, rule, hits, metric_hits = max(scores, key=lambda item: item[0])
    if score <= 1:
        return {
            "type": "generico",
            "label": "Analise gerencial generica",
            "confidence": 0.35,
            "reasons": ["Nao foram encontrados sinais suficientes para classificar um dominio especifico."],
        }

    confidence = min(0.96, 0.42 + score * 0.07)
    reasons = []
    if hits:
        reasons.append(f"Sinais de dominio: {', '.join(hits)}")
    if metric_hits:
        reasons.append(f"Metricas reconhecidas: {', '.join(metric_hits)}")
    return {
        "type": rule["type"],
        "label": rule["label"],
        "confidence": round(confidence, 2),
        "reasons": reasons,
    }


def _map_metrics(df: pd.DataFrame, profile: dict, domain: dict) -> dict:
    numeric_columns = profile["numeric_columns"]
    rule = _domain_rule(domain["type"])
    primary_metric = _first_scored_column(numeric_columns, rule.get("primary_metrics", []), df)
    if not primary_metric and numeric_columns:
        primary_metric = _first_business_numeric(numeric_columns, df)

    support_metrics: dict[str, str] = {}
    for group_name, terms in rule.get("support_groups", {}).items():
        column = _first_scored_column(numeric_columns, terms, df, exclude={primary_metric})
        if column:
            support_metrics[group_name] = column

    return {
        "primary_metric": primary_metric,
        "support_metrics": support_metrics,
        "mapped_columns": {
            "primary_metric": primary_metric,
            **support_metrics,
        },
    }


def _build_time_context(df: pd.DataFrame, profile: dict) -> dict:
    for column in profile["datetime_columns"]:
        parsed = parse_common_dates(df[column])
        if parsed.notna().mean() >= 0.6:
            return {"available": True, "label": column, "columns": [column], "series": parsed}

    for candidate in profile.get("date_candidates", []):
        column = candidate.get("column")
        if column in df.columns:
            parsed = parse_common_dates(df[column])
            if parsed.notna().mean() >= 0.6:
                return {"available": True, "label": column, "columns": [column], "series": parsed}

    year_column = _first_matching(profile["column_names"], YEAR_TERMS)
    month_column = _first_matching([column for column in profile["column_names"] if column != year_column], MONTH_TERMS)
    if year_column and month_column:
        parsed = _parse_year_month(df[year_column], df[month_column])
        if parsed.notna().mean() >= 0.6:
            return {
                "available": True,
                "label": f"{year_column} + {month_column}",
                "columns": [year_column, month_column],
                "series": parsed,
            }

    return {"available": False, "label": None, "columns": [], "series": pd.Series(pd.NaT, index=df.index)}


def _parse_year_month(year_series: pd.Series, month_series: pd.Series) -> pd.Series:
    years = pd.to_numeric(year_series, errors="coerce")
    months = month_series.map(_month_number)
    return pd.to_datetime(
        pd.DataFrame({"year": years, "month": months, "day": 1}),
        errors="coerce",
    )


def _month_number(value: Any) -> float | None:
    if pd.isna(value):
        return None

    text = _strip_accents(str(value)).lower().strip()
    numeric_match = re.search(r"\d{1,2}", text)
    if numeric_match:
        number = int(numeric_match.group(0))
        if 1 <= number <= 12:
            return number

    text_match = re.search(r"[a-z]{3,}", text)
    if text_match:
        return MONTH_ALIASES.get(text_match.group(0)[:3])
    return None


def _select_dimensions(column_names: list[str], domain: dict) -> list[dict]:
    rule = _domain_rule(domain["type"])
    dimensions = []
    used = set()
    for term in rule.get("dimensions", []):
        column = _first_matching(column_names, [term])
        if column and column not in used:
            dimensions.append({"label": term, "column": column})
            used.add(column)
    return dimensions[:4]


def _fallback_analysis(dataset: DatasetSession, profile: dict, context: dict) -> dict:
    limitations = context["limitations"] or ["Nao ha combinacao suficiente de metrica e tempo para diagnosticar variacao."]
    return {
        "mode": "managerial_deep_dive",
        "title": "Analise gerencial profunda",
        "summary": [
            "O DataSense identificou a estrutura do arquivo, mas ainda nao ha base suficiente para explicar variacoes no tempo.",
            "Para uma leitura gerencial completa, envie uma metrica numerica relevante e uma coluna de data, mes, trimestre ou ano + mes.",
        ],
        "context": context,
        "kpis": [
            {"label": "Registros", "value": _format_number(profile["rows"]), "detail": f"{profile['columns']} colunas analisadas"},
            {"label": "Dominio", "value": context["domain"]["label"], "detail": f"{round(context['domain']['confidence'] * 100)}% de confianca"},
        ],
        "insights": [
            {
                "id": "analise_insuficiente",
                "title": "Analise gerencial precisa de metrica e tempo",
                "severity": "warning",
                "metric": context["metric_map"].get("primary_metric"),
                "period": None,
                "what_changed": "Nao foi possivel calcular variacao temporal.",
                "how_much": "Sem comparacao entre periodos.",
                "where": "Dataset completo.",
                "possible_causes": limitations,
                "managerial_impact": "Sem variacao temporal confiavel, o gestor recebe apenas uma leitura descritiva.",
                "recommendation": "Confirmar qual coluna representa data/periodo e qual coluna representa a metrica principal.",
                "confidence": "baixa",
                "evidence": limitations,
            }
        ],
        "variations": {},
        "driver_evidence": [],
        "alerts": limitations,
        "recommendations": ["Adicionar ou confirmar coluna de periodo para habilitar diagnostico de alta, queda e tendencia."],
        "suggested_questions": _suggested_questions(context["domain"]["type"], context["metric_map"], context["dimensions"]),
        "ai_evidence_package": {"limitations": limitations},
    }


def _empty_diagnostic(metric_map: dict, domain: dict, reason: str) -> dict:
    insight = {
        "id": "sem_variacao",
        "title": "Sem variacao temporal suficiente",
        "severity": "warning",
        "metric": metric_map.get("primary_metric"),
        "period": None,
        "what_changed": "Nao foi possivel medir variacao.",
        "how_much": reason,
        "where": "Dataset completo.",
        "possible_causes": [reason],
        "managerial_impact": "A analise fica limitada a KPIs descritivos.",
        "recommendation": "Validar periodo e granularidade do arquivo.",
        "confidence": "baixa",
        "evidence": [reason],
    }
    return {
        "summary": [reason],
        "kpis": [],
        "insights": [insight],
        "variations": {},
        "driver_evidence": [],
        "alerts": [reason],
        "recommendations": ["Validar periodo e granularidade do arquivo."],
        "ai_evidence_package": {"domain": domain, "metric_map": metric_map, "limitations": [reason]},
    }


def _executive_summary(
    period_metrics: pd.DataFrame,
    primary_metric: str,
    domain: dict,
    focus: pd.Series,
    latest: pd.Series,
    driver_evidence: list[dict],
) -> list[str]:
    first = period_metrics.iloc[0]
    last = period_metrics.iloc[-1]
    total_change = float(last["valor"] - first["valor"])
    total_pct = total_change / abs(float(first["valor"])) if float(first["valor"]) else None
    direction = "cresceu" if total_change >= 0 else "caiu"
    focus_direction = "alta" if float(focus["variacao"]) >= 0 else "queda"
    summary = [
        (
            f"{domain['label']}: {primary_metric} {direction} {_format_pct(total_pct)} "
            f"entre {first['periodo']} e {last['periodo']}."
        ),
        (
            f"Movimento mais relevante: {focus_direction} em {focus['periodo']} "
            f"de {_format_signed_number(float(focus['variacao']))} ({_format_pct(_safe_float(focus.get('variacao_pct')))})."
        ),
        (
            f"Ultimo periodo analisado: {latest['periodo']} com {_format_number(float(latest['valor']))} "
            f"e variacao de {_format_signed_number(float(latest['variacao']))}."
        ),
    ]
    if driver_evidence:
        summary.append(driver_evidence[0]["interpretation"])
    return summary


def _abnormal_periods(movement_rows: pd.DataFrame) -> pd.DataFrame:
    if movement_rows.empty:
        return movement_rows

    pct_threshold = movement_rows["variacao_pct"].abs().quantile(0.8)
    pct_threshold = max(float(pct_threshold or 0), 0.25)
    abnormal = movement_rows[
        (movement_rows["variacao_pct"].abs() >= pct_threshold)
        | (movement_rows["z_score"].abs().fillna(0) >= 2)
    ].copy()
    abnormal["abs_variacao"] = abnormal["variacao"].abs()
    return abnormal.sort_values("abs_variacao", ascending=False)


def _abnormal_insights(abnormal_periods: pd.DataFrame, primary_metric: str) -> list[dict]:
    insights = []
    for _, row in abnormal_periods.head(2).iterrows():
        insights.append(
            {
                "id": f"periodo_fora_padrao_{row['periodo']}",
                "title": f"Periodo fora do padrao em {row['periodo']}",
                "severity": "warning",
                "metric": primary_metric,
                "period": str(row["periodo"]),
                "what_changed": f"{primary_metric} teve movimento acima do padrao historico.",
                "how_much": f"Variacao de {_format_signed_number(float(row['variacao']))} ({_format_pct(_safe_float(row.get('variacao_pct')))}).",
                "where": "Serie temporal completa.",
                "possible_causes": ["O periodo se destacou em relacao ao historico e merece validacao operacional."],
                "managerial_impact": "Pode indicar ruptura, excesso, mudanca operacional ou efeito de carga/registro.",
                "recommendation": "Comparar o periodo com entradas, saidas, vendas, compras ou movimentacoes internas.",
                "confidence": "media",
                "evidence": [
                    f"Valor do periodo: {_format_number(float(row['valor']))}",
                    f"Media historica anterior: {_format_number(_safe_float(row.get('media_historica')))}",
                ],
            }
        )
    return insights


def _kpis(period_metrics: pd.DataFrame, primary_metric: str, latest: pd.Series, largest_increase: pd.Series, largest_drop: pd.Series) -> list[dict]:
    return [
        {
            "label": "Metrica principal",
            "value": primary_metric,
            "detail": "Base da analise gerencial",
        },
        {
            "label": "Ultimo periodo",
            "value": str(latest["periodo"]),
            "detail": f"{_format_number(float(latest['valor']))} no periodo",
        },
        {
            "label": "Variacao recente",
            "value": _format_signed_number(float(latest["variacao"])),
            "detail": _format_pct(_safe_float(latest.get("variacao_pct"))),
        },
        {
            "label": "Maior alta",
            "value": str(largest_increase["periodo"]),
            "detail": _format_signed_number(float(largest_increase["variacao"])),
        },
        {
            "label": "Maior queda",
            "value": str(largest_drop["periodo"]),
            "detail": _format_signed_number(float(largest_drop["variacao"])),
        },
        {
            "label": "Periodos analisados",
            "value": _format_number(int(period_metrics.shape[0])),
            "detail": f"{period_metrics.iloc[0]['periodo']} ate {period_metrics.iloc[-1]['periodo']}",
        },
    ]


def _alerts(abnormal_periods: pd.DataFrame, focus: pd.Series, metric_map: dict, period_metrics: pd.DataFrame) -> list[str]:
    alerts = []
    if not abnormal_periods.empty:
        alerts.append(f"{abnormal_periods.shape[0]} periodo(s) tiveram variacao acima do padrao historico.")
    if abs(_safe_float(focus.get("variacao_pct")) or 0) >= 0.5:
        alerts.append(f"Movimento critico em {focus['periodo']}: {_format_pct(_safe_float(focus.get('variacao_pct')))}.")
    for support_name in metric_map["support_metrics"]:
        if support_name in period_metrics.columns and period_metrics[support_name].isna().mean() > 0.2:
            alerts.append(f"A metrica de apoio {support_name} possui lacunas e reduz a confianca da explicacao.")
    return alerts or ["Nenhum alerta critico adicional na leitura gerencial inicial."]


def _recommendations(domain_type: str, focus: pd.Series, primary_metric: str, driver_evidence: list[dict], abnormal_periods: pd.DataFrame) -> list[str]:
    direction = "alta" if float(focus["variacao"]) >= 0 else "queda"
    recommendations = [_primary_recommendation(domain_type, "subiu" if direction == "alta" else "caiu")]
    if driver_evidence:
        recommendations.append(f"Validar o driver mais associado: {driver_evidence[0]['column']}.")
    if not abnormal_periods.empty:
        recommendations.append("Priorizar a revisao dos periodos fora do padrao antes de fechar conclusoes.")
    recommendations.append(f"Confirmar regra de negocio para interpretar {primary_metric} antes de tomar acao operacional.")
    return _deduplicate(recommendations)


def _suggested_questions(domain_type: str, metric_map: dict, dimensions: list[dict]) -> list[str]:
    metric = metric_map.get("primary_metric") or "a metrica principal"
    dimension = dimensions[0]["column"] if dimensions else "categoria"
    questions = [
        f"Por que {metric} variou no ultimo periodo?",
        f"Qual foi a maior queda de {metric}?",
        f"Qual foi a maior alta de {metric}?",
        f"Quais periodos ficaram fora do padrao?",
        f"Qual {dimension} mais contribuiu para a variacao?",
    ]
    if domain_type == "estoque_operacao":
        questions.extend(
            [
                "Existe risco de ruptura ou excesso de estoque?",
                "O volume industrializado explica a variacao do estoque?",
                "O custo mudou junto com o estoque?",
            ]
        )
    return questions[:8]


def _movement_payload(row: pd.Series) -> dict:
    return {
        "period": str(row.get("periodo")),
        "value": _round_or_none(row.get("valor")),
        "variation": _round_or_none(row.get("variacao")),
        "variation_pct": _round_or_none(row.get("variacao_pct")),
        "historical_mean": _round_or_none(row.get("media_historica")),
        "z_score": _round_or_none(row.get("z_score")),
    }


def _trend_payload(period_metrics: pd.DataFrame) -> dict:
    tail = period_metrics.tail(min(6, period_metrics.shape[0]))
    if tail.shape[0] < 2:
        return {"direction": "indefinida", "periods": tail["periodo"].astype(str).tolist()}
    start = float(tail.iloc[0]["valor"])
    end = float(tail.iloc[-1]["valor"])
    change = end - start
    return {
        "direction": "alta" if change > 0 else "queda" if change < 0 else "estavel",
        "change": round(change, 4),
        "change_pct": round(change / abs(start), 4) if start else None,
        "periods": tail["periodo"].astype(str).tolist(),
    }


def _movement_evidence(movement: pd.Series, drivers: list[dict], dimension: dict | None) -> list[str]:
    evidence = [
        f"Periodo: {movement['periodo']}",
        f"Valor: {_format_number(float(movement['valor']))}",
        f"Variacao: {_format_signed_number(float(movement['variacao']))} ({_format_pct(_safe_float(movement.get('variacao_pct')))}).",
    ]
    if dimension:
        evidence.append(dimension["where"])
    for driver in drivers[:2]:
        evidence.append(driver["interpretation"])
    return evidence


def _driver_interpretation(
    group_name: str,
    column: str,
    metric_direction: str,
    current_value: float | None,
    previous_value: float | None,
    variation: float | None,
    corr: float | None,
) -> str:
    if current_value is None:
        return f"{column} nao teve valores suficientes para explicar o movimento."

    driver_direction = "subiu" if variation is not None and variation >= 0 else "caiu"
    relation = ""
    if corr is not None:
        if corr <= -0.35:
            relation = " A relacao historica com a metrica principal e negativa, entao movimentos opostos podem ser relevantes."
        elif corr >= 0.35:
            relation = " A relacao historica com a metrica principal e positiva, entao movimentos na mesma direcao podem ser relevantes."

    if group_name == "volume_operacional":
        if metric_direction == "caiu" and driver_direction == "subiu":
            return (
                f"{column} subiu de {_format_number(previous_value)} para {_format_number(current_value)}, "
                "o que sugere consumo/saida operacional maior pressionando a queda."
            )
        if metric_direction == "subiu" and driver_direction == "caiu":
            return (
                f"{column} caiu para {_format_number(current_value)} enquanto a metrica subiu, "
                "sugerindo menor consumo, acumulacao ou reposicao acima da saida."
            )
    if group_name == "custo":
        return (
            f"{column} {driver_direction} para {_format_number(current_value)} no periodo analisado."
            f"{relation}"
        )
    if group_name == "estoque_fabrica":
        return (
            f"{column} ficou em {_format_number(current_value)} no periodo, ajudando a diferenciar estoque total de estoque em fabrica."
        )

    return (
        f"{column} {driver_direction} de {_format_number(previous_value)} para {_format_number(current_value)}."
        f"{relation}"
    )


def _context_limitations(metric_map: dict, time_context: dict, dimensions: list[dict]) -> list[str]:
    limitations = []
    if not metric_map.get("primary_metric"):
        limitations.append("Nao foi detectada uma metrica numerica principal clara.")
    if not time_context.get("available"):
        limitations.append("Nao foi detectada coluna de tempo ou combinacao ano + mes confiavel.")
    if not dimensions:
        limitations.append("Nao foi detectada dimensao clara para localizar onde a variacao ocorreu.")
    return limitations


def _domain_rule(domain_type: str) -> dict:
    for rule in DOMAIN_RULES:
        if rule["type"] == domain_type:
            return rule
    return {
        "type": "generico",
        "label": "Generico",
        "terms": [],
        "primary_metrics": ["valor_total", "valor", "total", "quantidade", "qtd", "volume"],
        "support_groups": {},
        "dimensions": ["produto", "categoria", "cliente", "fornecedor", "status"],
    }


def _first_scored_column(columns: list[str], terms: list[str], df: pd.DataFrame, exclude: set[str | None] | None = None) -> str | None:
    exclude = exclude or set()
    scored = []
    for column in columns:
        if column in exclude:
            continue
        normalized = _normalize_text(column)
        score = sum(100 - index * 4 for index, term in enumerate(terms) if term in normalized)
        if _looks_like_identifier(column):
            score -= 500
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            score -= 200
        if score > 0:
            scored.append((score, column))
    scored.sort(reverse=True)
    return scored[0][1] if scored else None


def _first_business_numeric(columns: list[str], df: pd.DataFrame) -> str | None:
    candidates = [column for column in columns if not _looks_like_identifier(column)]
    candidates = candidates or columns
    if not candidates:
        return None
    return max(candidates, key=lambda column: pd.to_numeric(df[column], errors="coerce").abs().sum(skipna=True))


def _first_matching(columns: list[str], terms: list[str]) -> str | None:
    for term in terms:
        for column in columns:
            if term in _normalize_text(column):
                return column
    return None


def _safe_corr(left: pd.Series, right: pd.Series) -> float | None:
    valid = pd.DataFrame({"left": pd.to_numeric(left, errors="coerce"), "right": pd.to_numeric(right, errors="coerce")}).dropna()
    if valid.shape[0] < 3 or valid["left"].nunique() < 2 or valid["right"].nunique() < 2:
        return None
    return round(float(valid["left"].corr(valid["right"])), 3)


def _safe_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_or_none(value: Any) -> float | None:
    parsed = _safe_float(value)
    return None if parsed is None else round(parsed, 4)


def _movement_severity(variation: float, pct: float | None) -> dict:
    abs_pct = abs(pct or 0)
    if abs_pct >= 0.5:
        return {"tone": "danger", "label": "critica"}
    if abs_pct >= 0.25:
        return {"tone": "warning", "label": "relevante"}
    if abs(variation) > 0:
        return {"tone": "info", "label": "moderada"}
    return {"tone": "neutral", "label": "estavel"}


def _confidence_level(driver_evidence: list[dict], dimension: dict | None, movement: pd.Series) -> str:
    score = 1
    if driver_evidence:
        score += 1
    if dimension:
        score += 1
    if _safe_float(movement.get("variacao_pct")) is not None:
        score += 1
    return "alta" if score >= 4 else "media" if score >= 2 else "baixa"


def _managerial_impact(domain_type: str, direction: str, severity: str) -> str:
    if domain_type == "estoque_operacao":
        if direction == "caiu":
            return "Pode indicar consumo acelerado, transferencia, venda, ruptura futura ou falha de reposicao."
        return "Pode indicar acumulacao, reposicao acima da saida, menor consumo ou risco de capital parado."
    if domain_type == "vendas":
        return "Afeta receita, concentracao comercial e previsibilidade do periodo."
    if domain_type == "compras":
        return "Afeta caixa, abastecimento, dependencia de fornecedor e custo operacional."
    return "Pode alterar a leitura executiva e a prioridade de acao no periodo."


def _primary_recommendation(domain_type: str, direction: str) -> str:
    if domain_type == "estoque_operacao":
        if direction == "caiu":
            return "Verificar saidas, vendas, transferencias e regra de reposicao do periodo."
        return "Verificar entradas, compras, producao e risco de estoque parado."
    if domain_type == "vendas":
        return "Validar mix de produtos/clientes e campanhas ou eventos que expliquem o movimento."
    if domain_type == "compras":
        return "Validar pedidos, fornecedores e prazos que concentraram o movimento."
    return "Validar os principais registros do periodo e confirmar a regra de negocio da metrica."


def _generic_cause(domain_type: str, direction: str) -> str:
    if domain_type == "estoque_operacao":
        return "Possivel efeito de entradas, saidas, consumo operacional, transferencia ou reposicao."
    return f"Possivel efeito de mix, volume, sazonalidade ou mudanca operacional; a metrica {direction} no periodo."


def _is_additive_support(group_name: str) -> bool:
    return group_name not in {"custo", "prazo", "margem"}


def _looks_like_identifier(column: str) -> bool:
    normalized = _normalize_text(column)
    return any(term == normalized or normalized.startswith(f"{term}_") or normalized.endswith(f"_{term}") for term in ["id", "codigo", "cod", "sku", "nf"])


def _format_number(value: Any) -> str:
    parsed = _safe_float(value)
    if parsed is None:
        return "n/d"
    if abs(parsed) >= 1000:
        return f"{parsed:,.0f}".replace(",", ".")
    if parsed == int(parsed):
        return str(int(parsed))
    return f"{parsed:.2f}".replace(".", ",")


def _format_signed_number(value: float | None) -> str:
    if value is None:
        return "n/d"
    sign = "+" if value >= 0 else "-"
    return f"{sign}{_format_number(abs(value))}"


def _format_pct(value: float | None) -> str:
    if value is None:
        return "n/d"
    return f"{value:.1%}".replace(".", ",")


def _deduplicate(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        key = _normalize_text(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _strip_accents(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(character for character in text if not unicodedata.combining(character))


def _normalize_text(value: str) -> str:
    text = _strip_accents(str(value))
    text = re.sub(r"[^a-zA-Z0-9_]+", "_", text.lower())
    return re.sub(r"_+", "_", text).strip("_")
