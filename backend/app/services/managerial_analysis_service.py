from functools import partial
from typing import Any

import pandas as pd

from app.models import DatasetSession
from app.services.column_heuristics import (
    format_number,
    normalize_text as _normalize_text,
)
from app.services.managerial_context_service import (
    build_time_context as _build_time_context,
    detect_analysis_domain as _detect_analysis_domain,
    map_metrics as _map_metrics,
    select_dimensions as _select_dimensions,
)
from app.services.profile_service import build_profile

_format_number = partial(format_number, none_text="n/d", compact_large=True)


def build_managerial_analysis(dataset: DatasetSession) -> dict:
    df = dataset.dataframe.copy()
    profile = build_profile(dataset)
    domain = _detect_analysis_domain(profile["column_names"])
    metric_map = _map_metrics(df, profile, domain)
    time_context = _build_time_context(df, profile)
    dimensions = _select_dimensions(profile, domain)

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
        "root_cause_analysis": diagnostic["root_cause_analysis"],
        "dimension_narratives": diagnostic["dimension_narratives"],
        "monthly_comparisons": diagnostic["monthly_comparisons"],
        "comparative_summary": diagnostic["comparative_summary"],
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
    recommendations = _recommendations(domain["type"], focus, primary_metric, driver_evidence, abnormal_periods)
    monthly_comparisons = _monthly_comparisons(period_metrics, metric_map, domain)
    comparative_summary = _comparative_summary(period_metrics, primary_metric)
    root_cause_analysis = _root_cause_analysis(prepared, period_metrics, metric_map, dimensions, domain, focus, driver_evidence)
    dimension_narratives = root_cause_analysis.get("dimension_narratives", [])
    alerts = _deduplicate(
        [
            *_alerts(abnormal_periods, focus, metric_map, period_metrics, root_cause_analysis),
            *root_cause_analysis.get("concentration_alerts", []),
        ]
    )

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
        "root_cause_analysis": root_cause_analysis,
        "dimension_narratives": dimension_narratives,
        "monthly_comparisons": monthly_comparisons,
        "comparative_summary": comparative_summary,
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
            "root_cause_analysis": root_cause_analysis,
            "dimension_narratives": dimension_narratives,
            "monthly_comparisons": monthly_comparisons[-12:],
            "comparative_summary": comparative_summary,
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


def _root_cause_analysis(
    prepared: pd.DataFrame,
    period_metrics: pd.DataFrame,
    metric_map: dict,
    dimensions: list[dict],
    domain: dict,
    focus: pd.Series,
    driver_evidence: list[dict],
) -> dict:
    primary_metric = metric_map["primary_metric"]
    focus_period = str(focus["periodo"])
    previous_period = _previous_period(period_metrics, focus_period)
    current_value = _safe_float(focus.get("valor"))
    variation = _safe_float(focus.get("variacao"))
    previous_value = None if current_value is None or variation is None else current_value - variation
    variation_pct = _safe_float(focus.get("variacao_pct"))
    direction = "alta" if (variation or 0) >= 0 else "queda"

    dimension_drivers = _root_dimension_drivers(
        prepared,
        dimensions,
        focus_period,
        previous_period,
        variation,
        period_metrics,
    )
    dimension_impact_ranking = _dimension_impact_ranking(dimension_drivers, focus_period)
    concentration_alerts = _dimension_concentration_alerts(dimension_drivers)
    primary_dimension = next((item for item in dimension_drivers if item.get("contributors")), None)
    top_contributor = primary_dimension["contributors"][0] if primary_dimension else None
    waterfall = _waterfall_payload(previous_value, current_value, focus_period, previous_period, top_contributor, primary_dimension)
    historical_mean = _safe_float(focus.get("media_historica"))
    historical_delta = None if current_value is None or historical_mean is None else current_value - historical_mean
    historical_pct = historical_delta / abs(historical_mean) if historical_delta is not None and historical_mean else None

    summary = _root_cause_summary(
        primary_metric,
        focus_period,
        previous_period,
        direction,
        variation,
        variation_pct,
        top_contributor,
        historical_mean,
        historical_delta,
        driver_evidence,
    )
    dimension_narratives = _dimension_narratives(
        dimension_drivers,
        domain["type"],
        primary_metric,
        focus_period,
        previous_period,
        variation,
        variation_pct,
    )

    return {
        "title": f"Causa raiz provavel da {direction} em {focus_period}",
        "metric": primary_metric,
        "period": focus_period,
        "previous_period": previous_period,
        "movement": {
            "current_value": _round_or_none(current_value),
            "previous_value": _round_or_none(previous_value),
            "variation": _round_or_none(variation),
            "variation_pct": _round_or_none(variation_pct),
            "direction": direction,
        },
        "responsible_month": {
            "period": focus_period,
            "label": f"{focus_period} concentrou a maior {direction} detectada na serie.",
            "historical_mean": _round_or_none(historical_mean),
            "historical_delta": _round_or_none(historical_delta),
            "historical_delta_pct": _round_or_none(historical_pct),
            "z_score": _round_or_none(focus.get("z_score")),
        },
        "primary_contributor": top_contributor,
        "dimension_drivers": dimension_drivers,
        "dimension_impact_ranking": dimension_impact_ranking,
        "dimension_narratives": dimension_narratives,
        "concentration_alerts": concentration_alerts,
        "supporting_metrics": driver_evidence[:4],
        "waterfall": waterfall,
        "summary": summary,
        "confidence": _root_cause_confidence(top_contributor, driver_evidence, primary_dimension),
        "recommendation": _root_cause_recommendation(domain["type"], direction, top_contributor),
    }


def _root_dimension_drivers(
    prepared: pd.DataFrame,
    dimensions: list[dict],
    focus_period: str,
    previous_period: str | None,
    total_variation: float | None,
    period_metrics: pd.DataFrame,
) -> list[dict]:
    drivers = []
    if not previous_period:
        return drivers

    for dimension in dimensions[:4]:
        column = dimension["column"]
        if column not in prepared.columns:
            continue

        current = prepared[prepared["_periodo"] == focus_period].groupby(column)["_valor_principal"].sum()
        previous = prepared[prepared["_periodo"] == previous_period].groupby(column)["_valor_principal"].sum()
        index = current.index.union(previous.index)
        comparison = pd.DataFrame(
            {
                "name": index.astype(str),
                "current_value": current.reindex(index).fillna(0).to_numpy(),
                "previous_value": previous.reindex(index).fillna(0).to_numpy(),
            }
        )
        if comparison.empty:
            continue

        comparison["variation"] = comparison["current_value"] - comparison["previous_value"]
        comparison["variation_pct_vs_previous"] = comparison.apply(
            lambda row: _safe_pct(row["variation"], row["previous_value"]),
            axis=1,
        )
        abs_total = comparison["variation"].abs().sum()
        comparison["share_of_abs_change"] = comparison["variation"].abs() / abs_total if abs_total else 0
        comparison["share_of_total_change"] = comparison["variation"] / total_variation if total_variation else None
        history = _dimension_history(prepared, column)
        comparison = comparison.merge(history, on="name", how="left")
        comparison["historical_delta"] = comparison["current_value"] - comparison["historical_mean"]
        comparison["concentration_level"] = comparison["share_of_abs_change"].apply(_concentration_level)
        comparison["recurrence_flag"] = comparison.apply(
            lambda row: _recurrence_flag(prepared, column, str(row["name"]), focus_period),
            axis=1,
        )
        comparison = comparison.sort_values("variation", key=lambda values: values.abs(), ascending=False)
        contributors = [
            {
                "name": str(row["name"]),
                "current_value": _round_or_none(row["current_value"]),
                "previous_value": _round_or_none(row["previous_value"]),
                "variation": _round_or_none(row["variation"]),
                "variation_pct_vs_previous": _round_or_none(row["variation_pct_vs_previous"]),
                "share_of_abs_change": _round_or_none(row["share_of_abs_change"]),
                "share_of_total_change": _round_or_none(row["share_of_total_change"]),
                "historical_mean": _round_or_none(row["historical_mean"]),
                "historical_delta": _round_or_none(row["historical_delta"]),
                "concentration_level": row["concentration_level"],
                "recurrence_flag": row["recurrence_flag"],
            }
            for _, row in comparison.head(8).iterrows()
        ]
        drivers.append(
            {
                "dimension": column,
                "label": dimension.get("label", column),
                "contributors": contributors,
                "coverage": _round_or_none(sum(item["share_of_abs_change"] or 0 for item in contributors[:5])),
            }
        )

    return drivers


def _dimension_impact_ranking(dimension_drivers: list[dict], focus_period: str) -> list[dict]:
    ranking = []
    for driver in dimension_drivers:
        for contributor in driver.get("contributors", [])[:5]:
            variation = _safe_float(contributor.get("variation"))
            share_abs = _safe_float(contributor.get("share_of_abs_change"))
            if variation is None:
                continue
            ranking.append(
                {
                    "dimension": driver.get("dimension"),
                    "label": driver.get("label"),
                    "name": contributor.get("name"),
                    "current_value": contributor.get("current_value"),
                    "previous_value": contributor.get("previous_value"),
                    "variation": _round_or_none(variation),
                    "variation_pct_vs_previous": contributor.get("variation_pct_vs_previous"),
                    "share_of_abs_change": _round_or_none(share_abs),
                    "share_of_total_change": contributor.get("share_of_total_change"),
                    "historical_mean": contributor.get("historical_mean"),
                    "historical_delta": contributor.get("historical_delta"),
                    "concentration_level": contributor.get("concentration_level"),
                    "recurrence_flag": contributor.get("recurrence_flag"),
                    "reading": (
                        f"{contributor.get('name')} em {driver.get('label')} respondeu por "
                        f"{_format_pct(share_abs)} da variacao absoluta em {focus_period}, com "
                        f"{contributor.get('recurrence_flag', 'peso pontual')} e concentracao "
                        f"{contributor.get('concentration_level', 'baixa')}."
                    ),
                }
            )
    ranking.sort(
        key=lambda item: (
            abs(_safe_float(item.get("share_of_abs_change")) or 0),
            abs(_safe_float(item.get("variation")) or 0),
            abs(_safe_float(item.get("historical_delta")) or 0),
        ),
        reverse=True,
    )
    return ranking[:12]


def _dimension_history(prepared: pd.DataFrame, column: str) -> pd.DataFrame:
    grouped = (
        prepared.groupby(["_periodo", column], as_index=False)["_valor_principal"]
        .sum()
        .rename(columns={column: "name", "_valor_principal": "value"})
    )
    if grouped.empty:
        return pd.DataFrame(columns=["name", "historical_mean"])
    history = grouped.groupby("name", as_index=False)["value"].mean().rename(columns={"value": "historical_mean"})
    history["name"] = history["name"].astype(str)
    return history


def _recurrence_flag(prepared: pd.DataFrame, column: str, name: str, focus_period: str) -> str:
    grouped = (
        prepared.groupby(["_periodo", column], as_index=False)["_valor_principal"]
        .sum()
        .rename(columns={column: "name", "_valor_principal": "value"})
    )
    if grouped.empty:
        return "pontual"
    pivot = grouped.pivot(index="_periodo", columns="name", values="value").fillna(0).sort_index()
    if name not in pivot.columns:
        return "pontual"
    recent = pivot.diff().abs().dropna()
    if recent.empty:
        return "pontual"
    relevant_periods = [period for period in recent.index if period <= focus_period][-3:]
    appearances = 0
    for period in relevant_periods:
        period_row = recent.loc[period].sort_values(ascending=False).head(3)
        if name in period_row.index:
            appearances += 1
    return "recorrente" if appearances >= 2 else "pontual"


def _concentration_level(share_abs: float | None) -> str:
    value = share_abs or 0
    if value >= 0.8:
        return "alta"
    if value >= 0.6:
        return "media"
    return "baixa"


def _safe_pct(delta: Any, base: Any) -> float | None:
    delta_value = _safe_float(delta)
    base_value = _safe_float(base)
    if delta_value is None or base_value in (None, 0):
        return None
    return delta_value / abs(base_value)


def _dimension_narrative_text(
    domain_type: str,
    dimension_label: str,
    primary_metric: str,
    focus_period: str,
    previous_period: str | None,
    top: dict,
    total_variation: float | None,
    total_variation_pct: float | None,
) -> str:
    name = top.get("name") or "recorte principal"
    variation = _format_signed_number(top.get("variation"))
    variation_pct = _format_pct(_safe_float(top.get("variation_pct_vs_previous")))
    share = _format_pct(_safe_float(top.get("share_of_abs_change")))
    base = (
        f"Em {focus_period}, {name} foi o principal vetor em {dimension_label}: "
        f"{variation} em {primary_metric} contra {previous_period or 'o periodo anterior'} "
        f"({variation_pct}), respondendo por {share} da variacao absoluta."
    )
    if domain_type == "estoque_operacao":
        return (
            f"{base} A leitura sugere concentracao operacional entre consumo, reposicao, transferencia "
            f"ou ruptura de estoque nesse recorte."
        )
    if domain_type == "vendas":
        return f"{base} O movimento aponta mudanca de mix, cliente ou canal com impacto comercial direto."
    if domain_type == "compras":
        return f"{base} O sinal e compativel com dependencia de fornecedor, item critico ou variacao de prazo/custo."
    if domain_type == "financeiro":
        return f"{base} O desvio merece validacao em centros de custo, contas ou eventos nao recorrentes."
    overall = _format_signed_number(total_variation)
    overall_pct = _format_pct(total_variation_pct)
    return f"{base} No consolidado, a serie teve {overall} ({overall_pct}), entao esse recorte merece verificacao gerencial."


def _dimension_managerial_impact(domain_type: str, top: dict, share_abs: float) -> str:
    name = top.get("name") or "recorte principal"
    if domain_type == "estoque_operacao":
        return f"{name} pode concentrar risco de ruptura, excesso localizado ou transferencia sem compensacao."
    if domain_type == "vendas":
        return f"{name} concentra parte relevante do resultado comercial e pode distorcer o mix mensal."
    if domain_type == "compras":
        return f"{name} pode elevar dependencia operacional e pressionar custo ou prazo."
    if share_abs >= 0.8:
        return f"{name} domina a mudanca e deve ser validado antes de generalizar conclusoes para toda a base."
    return f"{name} ajuda a explicar a mudanca e orienta o foco inicial da investigacao."


def _dimension_possible_causes(domain_type: str, top: dict, share_abs: float) -> list[str]:
    name = top.get("name") or "recorte principal"
    common = [f"{name} concentrou {_format_pct(share_abs)} da variacao absoluta no periodo."]
    if domain_type == "estoque_operacao":
        return common + ["Validar consumo elevado, reposicao atrasada, transferencia ou ajuste de estoque."]
    if domain_type == "vendas":
        return common + ["Revisar mix, carteira, campanha, canal ou perda de volume nesse recorte."]
    if domain_type == "compras":
        return common + ["Verificar dependencia de fornecedor, atraso, renegociacao ou mudanca de item."]
    return common + ["Checar classificacao contabil, evento pontual ou mudanca concentrada em poucas entidades."]


def _dimension_recommendation(domain_type: str, dimension_label: str, top: dict, share_abs: float) -> str:
    name = top.get("name") or "recorte principal"
    if domain_type == "estoque_operacao":
        return f"Validar movimentacoes de {name} em {dimension_label}, incluindo consumo, reposicao e transferencias do periodo."
    if domain_type == "vendas":
        return f"Revisar carteira e mix de {name} em {dimension_label}, comparando canal, cliente e ticket contra a media recente."
    if domain_type == "compras":
        return f"Auditar {name} em {dimension_label} com foco em prazo, custo e dependencia operacional."
    if share_abs >= 0.8:
        return f"Priorize {name} em {dimension_label}; ele sozinho explica a maior parte da mudanca."
    return f"Investigue {name} em {dimension_label} antes de expandir a leitura para os demais recortes."


def _dimension_narratives(
    dimension_drivers: list[dict],
    domain_type: str,
    primary_metric: str,
    focus_period: str,
    previous_period: str | None,
    total_variation: float | None,
    total_variation_pct: float | None,
) -> list[dict]:
    narratives = []
    for driver in dimension_drivers[:4]:
        contributors = driver.get("contributors") or []
        if not contributors:
            continue
        top = contributors[0]
        share = _safe_float(top.get("share_of_abs_change")) or 0
        historical_delta = _safe_float(top.get("historical_delta"))
        historical_mean = _safe_float(top.get("historical_mean"))
        narratives.append(
            {
                "dimension": driver.get("dimension"),
                "label": driver.get("label"),
                "top_movers": contributors[:3],
                "share_concentration": {
                    "top_1": _round_or_none(share),
                    "top_3": _round_or_none(sum((_safe_float(item.get("share_of_abs_change")) or 0) for item in contributors[:3])),
                    "level": _concentration_level(share),
                },
                "historical_comparison": {
                    "historical_mean": _round_or_none(historical_mean),
                    "historical_delta": _round_or_none(historical_delta),
                    "historical_delta_pct": _round_or_none(
                        historical_delta / abs(historical_mean) if historical_delta is not None and historical_mean else None
                    ),
                },
                "narrative": _dimension_narrative_text(
                    domain_type,
                    driver.get("label") or driver.get("dimension"),
                    primary_metric,
                    focus_period,
                    previous_period,
                    top,
                    total_variation,
                    total_variation_pct,
                ),
                "managerial_impact": _dimension_managerial_impact(domain_type, top, share),
                "possible_causes": _dimension_possible_causes(domain_type, top, share),
                "recommendation": _dimension_recommendation(domain_type, driver.get("label") or driver.get("dimension"), top, share),
            }
        )
    return narratives[:4]


def _dimension_concentration_alerts(dimension_drivers: list[dict]) -> list[str]:
    alerts = []
    for driver in dimension_drivers:
        contributors = driver.get("contributors", [])
        if not contributors:
            continue
        top = contributors[0]
        share_abs = _safe_float(top.get("share_of_abs_change")) or 0
        if share_abs >= 0.8:
            alerts.append(
                f"{top.get('name')} concentra {_format_pct(share_abs)} da variacao em {driver.get('label')}."
            )
        elif share_abs >= 0.6:
            alerts.append(
                f"{top.get('name')} tem peso relevante em {driver.get('label')}: {_format_pct(share_abs)} da variacao."
            )
    return alerts


def _waterfall_payload(
    previous_value: float | None,
    current_value: float | None,
    focus_period: str,
    previous_period: str | None,
    top_contributor: dict | None,
    primary_dimension: dict | None,
) -> dict:
    if previous_value is None or current_value is None:
        return {"steps": []}

    steps = [
        {
            "label": previous_period or "Periodo anterior",
            "kind": "baseline",
            "value": _round_or_none(previous_value),
            "delta": None,
            "running_total": _round_or_none(previous_value),
        }
    ]
    running_total = previous_value
    contributors = (primary_dimension or {}).get("contributors", [])[:5]
    for contributor in contributors:
        delta = _safe_float(contributor.get("variation")) or 0
        running_total += delta
        steps.append(
            {
                "label": str(contributor.get("name")),
                "kind": "increase" if delta >= 0 else "decrease",
                "value": _round_or_none(running_total),
                "delta": _round_or_none(delta),
                "running_total": _round_or_none(running_total),
            }
        )

    residual = current_value - running_total
    if abs(residual) >= max(abs(current_value) * 0.01, 0.01):
        running_total += residual
        steps.append(
            {
                "label": "Outros efeitos",
                "kind": "increase" if residual >= 0 else "decrease",
                "value": _round_or_none(running_total),
                "delta": _round_or_none(residual),
                "running_total": _round_or_none(running_total),
            }
        )

    steps.append(
        {
            "label": focus_period,
            "kind": "current",
            "value": _round_or_none(current_value),
            "delta": None,
            "running_total": _round_or_none(current_value),
        }
    )
    return {
        "dimension": (primary_dimension or {}).get("dimension"),
        "top_contributor": top_contributor,
        "steps": steps,
    }


def _root_cause_summary(
    primary_metric: str,
    focus_period: str,
    previous_period: str | None,
    direction: str,
    variation: float | None,
    variation_pct: float | None,
    top_contributor: dict | None,
    historical_mean: float | None,
    historical_delta: float | None,
    driver_evidence: list[dict],
) -> list[str]:
    summary = [
        (
            f"{primary_metric} teve {direction} em {focus_period} contra {previous_period or 'periodo anterior'}, "
            f"movendo {_format_signed_number(variation)} ({_format_pct(variation_pct)})."
        )
    ]
    if top_contributor:
        summary.append(
            f"Quem mais puxou a mudanca foi {top_contributor['name']}, com contribuicao de "
            f"{_format_signed_number(top_contributor.get('variation'))}."
        )
    if historical_mean is not None:
        summary.append(
            f"Contra a media historica anterior ({_format_number(historical_mean)}), o periodo ficou "
            f"{_format_signed_number(historical_delta)} distante."
        )
    if driver_evidence:
        summary.append(driver_evidence[0]["interpretation"])
    return summary


def _root_cause_confidence(top_contributor: dict | None, driver_evidence: list[dict], primary_dimension: dict | None) -> str:
    score = 0
    if top_contributor:
        score += 1
    if driver_evidence:
        score += 1
    if (primary_dimension or {}).get("coverage", 0) >= 0.75:
        score += 1
    return "alta" if score >= 3 else "media" if score >= 1 else "baixa"


def _root_cause_recommendation(domain_type: str, direction: str, top_contributor: dict | None) -> str:
    contributor = f" para {top_contributor['name']}" if top_contributor else ""
    if domain_type == "estoque_operacao":
        if direction == "queda":
            return f"Auditar saidas, transferencias, consumo e reposicao{contributor} no periodo destacado."
        return f"Auditar entradas, producao, compras e risco de estoque parado{contributor}."
    if domain_type == "vendas":
        return f"Validar cliente, produto, canal e campanhas que concentraram a variacao{contributor}."
    if domain_type == "compras":
        return f"Validar fornecedor, pedido, prazo e itens que concentraram a variacao{contributor}."
    return f"Revisar os registros que concentraram a variacao{contributor} antes de fechar a conclusao."


def _previous_period(period_metrics: pd.DataFrame, focus_period: str) -> str | None:
    periods = period_metrics["periodo"].astype(str).tolist()
    try:
        index = periods.index(str(focus_period))
    except ValueError:
        return None
    return periods[index - 1] if index > 0 else None


def _monthly_comparisons(period_metrics: pd.DataFrame, metric_map: dict, domain: dict) -> list[dict]:
    comparisons = []
    for _, row in period_metrics.tail(18).iterrows():
        value = _safe_float(row.get("valor"))
        variation = _safe_float(row.get("variacao"))
        variation_pct = _safe_float(row.get("variacao_pct"))
        previous_value = None if value is None or variation is None else value - variation
        drivers = _monthly_driver_changes(period_metrics, metric_map, row)
        main_driver = drivers[0] if drivers else None
        status = _monthly_status(variation, variation_pct, _safe_float(row.get("z_score")))
        comparisons.append(
            {
                "period": str(row.get("periodo")),
                "value": _round_or_none(value),
                "previous_value": _round_or_none(previous_value),
                "variation": _round_or_none(variation),
                "variation_pct": _round_or_none(variation_pct),
                "historical_mean": _round_or_none(row.get("media_historica")),
                "z_score": _round_or_none(row.get("z_score")),
                "status": status["label"],
                "severity": status["tone"],
                "managerial_reading": _monthly_reading(domain["type"], status["label"], variation, variation_pct, main_driver),
                "main_driver": main_driver,
                "drivers": drivers[:4],
            }
        )
    return comparisons


def _comparative_summary(period_metrics: pd.DataFrame, primary_metric: str) -> dict:
    if period_metrics.empty:
        return {"cards": [], "readings": []}

    metrics = period_metrics.copy()
    metrics["_period"] = metrics["periodo"].map(_safe_period)
    metrics = metrics[metrics["_period"].notna()].copy()
    if metrics.empty:
        return {"cards": [], "readings": []}

    latest = metrics.iloc[-1]
    latest_period = latest["_period"]
    latest_value = _safe_float(latest.get("valor"))
    best = metrics.sort_values("valor", ascending=False).iloc[0]
    worst = metrics.sort_values("valor", ascending=True).iloc[0]
    last_3 = metrics.tail(3)
    previous_3 = metrics.iloc[max(0, len(metrics) - 6) : max(0, len(metrics) - 3)]
    last_3_total = _safe_float(last_3["valor"].sum()) if not last_3.empty else None
    previous_3_total = _safe_float(previous_3["valor"].sum()) if not previous_3.empty else None
    last_3_delta = None if last_3_total is None or previous_3_total is None else last_3_total - previous_3_total
    last_3_pct = last_3_delta / abs(previous_3_total) if last_3_delta is not None and previous_3_total else None

    same_year = metrics[metrics["_period"].map(lambda period: period.year == latest_period.year)]
    ytd_current = _safe_float(same_year[same_year["_period"].map(lambda period: period.month <= latest_period.month)]["valor"].sum())
    previous_year = metrics[
        metrics["_period"].map(lambda period: period.year == latest_period.year - 1 and period.month <= latest_period.month)
    ]
    ytd_previous = _safe_float(previous_year["valor"].sum()) if not previous_year.empty else None
    ytd_delta = None if ytd_previous is None else ytd_current - ytd_previous
    ytd_pct = ytd_delta / abs(ytd_previous) if ytd_delta is not None and ytd_previous else None

    moving_average_3 = _safe_float(last_3["valor"].mean()) if not last_3.empty else None
    latest_vs_average = None if latest_value is None or moving_average_3 is None else latest_value - moving_average_3
    latest_vs_average_pct = latest_vs_average / abs(moving_average_3) if latest_vs_average is not None and moving_average_3 else None

    cards = [
        {
            "label": "Ultimos 3 meses",
            "value": _format_number(last_3_total),
            "detail": f"{_format_signed_number(last_3_delta)} vs 3 meses anteriores ({_format_pct(last_3_pct)})",
            "tone": _comparison_tone(last_3_delta),
        },
        {
            "label": "Acumulado do ano",
            "value": _format_number(ytd_current),
            "detail": (
                f"{_format_signed_number(ytd_delta)} vs ano anterior ({_format_pct(ytd_pct)})"
                if ytd_previous is not None
                else "Sem ano anterior equivalente"
            ),
            "tone": _comparison_tone(ytd_delta),
        },
        {
            "label": "Media movel 3M",
            "value": _format_number(moving_average_3),
            "detail": f"Mes atual {_format_signed_number(latest_vs_average)} contra a media ({_format_pct(latest_vs_average_pct)})",
            "tone": _comparison_tone(latest_vs_average),
        },
        {
            "label": "Melhor mes",
            "value": str(best["periodo"]),
            "detail": _format_number(best.get("valor")),
            "tone": "good",
        },
        {
            "label": "Pior mes",
            "value": str(worst["periodo"]),
            "detail": _format_number(worst.get("valor")),
            "tone": "warning",
        },
    ]
    readings = [
        f"Nos ultimos 3 meses, {primary_metric} somou {_format_number(last_3_total)}; comparado aos 3 meses anteriores, a diferenca foi {_format_signed_number(last_3_delta)}.",
        f"No acumulado de {latest_period.year}, {primary_metric} soma {_format_number(ytd_current)} ate {latest_period.month:02d}/{latest_period.year}.",
        f"O mes atual ficou {_format_signed_number(latest_vs_average)} em relacao a media movel de 3 meses.",
        f"Melhor mes da serie: {best['periodo']} com {_format_number(best.get('valor'))}. Pior mes: {worst['periodo']} com {_format_number(worst.get('valor'))}.",
    ]
    return {"cards": cards, "readings": readings}


def _safe_period(value: object):
    try:
        return pd.Period(str(value), freq="M")
    except (TypeError, ValueError):
        return None


def _comparison_tone(value: float | None) -> str:
    if value is None:
        return "neutral"
    return "good" if value > 0 else "warning" if value < 0 else "neutral"


def _monthly_driver_changes(period_metrics: pd.DataFrame, metric_map: dict, movement: pd.Series) -> list[dict]:
    drivers = []
    focus_index = int(movement.name) if isinstance(movement.name, int) else period_metrics.index[period_metrics["periodo"] == movement["periodo"]][0]
    previous_row = period_metrics.iloc[focus_index - 1] if focus_index > 0 else None
    if previous_row is None:
        return drivers

    for group_name, column in metric_map["support_metrics"].items():
        if group_name not in period_metrics.columns:
            continue
        current_value = _safe_float(movement.get(group_name))
        previous_value = _safe_float(previous_row.get(group_name))
        if current_value is None or previous_value is None:
            continue
        variation = current_value - previous_value
        variation_pct = variation / abs(previous_value) if previous_value else None
        drivers.append(
            {
                "driver": group_name,
                "column": column,
                "current_value": _round_or_none(current_value),
                "previous_value": _round_or_none(previous_value),
                "variation": _round_or_none(variation),
                "variation_pct": _round_or_none(variation_pct),
                "reading": f"{column} variou {_format_signed_number(variation)} ({_format_pct(variation_pct)}).",
            }
        )

    drivers.sort(
        key=lambda item: max(abs(item.get("variation_pct") or 0), abs(item.get("variation") or 0) / 1000),
        reverse=True,
    )
    return drivers


def _monthly_status(variation: float | None, variation_pct: float | None, z_score: float | None) -> dict:
    if variation is None:
        return {"label": "Base inicial", "tone": "neutral"}
    if z_score is not None and abs(z_score) >= 2:
        return {"label": "Fora do padrao", "tone": "warning"}
    severity = _movement_severity(variation, variation_pct)
    if severity["tone"] == "danger":
        return {"label": "Movimento critico", "tone": "danger"}
    if severity["tone"] == "warning":
        return {"label": "Movimento relevante", "tone": "warning"}
    if variation > 0:
        return {"label": "Alta mensal", "tone": "info"}
    if variation < 0:
        return {"label": "Queda mensal", "tone": "info"}
    return {"label": "Estavel", "tone": "neutral"}


def _monthly_reading(
    domain_type: str,
    status: str,
    variation: float | None,
    variation_pct: float | None,
    main_driver: dict | None,
) -> str:
    if variation is None:
        return "Mes base para comparacoes posteriores."

    direction = "alta" if variation >= 0 else "queda"
    driver_text = f" Variavel de apoio com maior mudanca: {main_driver['reading']}" if main_driver else ""
    if domain_type == "estoque_operacao":
        if direction == "queda":
            return (
                f"{status}: estoque em queda de {_format_signed_number(variation)} ({_format_pct(variation_pct)}), "
                "avaliar consumo, saidas, transferencias e reposicao."
                f"{driver_text}"
            )
        return (
            f"{status}: estoque em alta de {_format_signed_number(variation)} ({_format_pct(variation_pct)}), "
            "avaliar entradas, producao, menor consumo e risco de capital parado."
            f"{driver_text}"
        )
    if domain_type == "vendas":
        return (
            f"{status}: receita/valor em {direction} de {_format_signed_number(variation)} ({_format_pct(variation_pct)}), "
            "validar mix, cliente, produto e campanha do mes."
            f"{driver_text}"
        )
    if domain_type == "compras":
        return (
            f"{status}: compras/custos em {direction} de {_format_signed_number(variation)} ({_format_pct(variation_pct)}), "
            "validar pedidos, fornecedor e abastecimento."
            f"{driver_text}"
        )
    return (
        f"{status}: metrica em {direction} de {_format_signed_number(variation)} ({_format_pct(variation_pct)})."
        f"{driver_text}"
    )


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
        "root_cause_analysis": None,
        "dimension_narratives": [],
        "monthly_comparisons": [],
        "comparative_summary": {"cards": [], "readings": []},
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
        "root_cause_analysis": None,
        "dimension_narratives": [],
        "monthly_comparisons": [],
        "comparative_summary": {"cards": [], "readings": []},
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


def _alerts(
    abnormal_periods: pd.DataFrame,
    focus: pd.Series,
    metric_map: dict,
    period_metrics: pd.DataFrame,
    root_cause_analysis: dict | None = None,
) -> list[str]:
    alerts = []
    period_label = str(focus.get("periodo") or "periodo analisado")
    variation_pct = _safe_float(focus.get("variacao_pct")) or 0
    if not abnormal_periods.empty:
        alerts.append(f"{abnormal_periods.shape[0]} periodo(s) tiveram variacao acima do padrao historico.")
    if abs(variation_pct) >= 0.5:
        alerts.append(f"Movimento critico em {period_label}: {_format_pct(variation_pct)}.")
        if variation_pct <= -0.5:
            alerts.append(f"Queda superior a 50% em {period_label}; priorizar validacao operacional imediata.")
        elif variation_pct >= 0.5:
            alerts.append(f"Alta superior a 50% em {period_label}; validar risco de excesso, pico artificial ou mudanca pontual.")
    for support_name in metric_map["support_metrics"]:
        if support_name in period_metrics.columns and period_metrics[support_name].isna().mean() > 0.2:
            alerts.append(f"A metrica de apoio {support_name} possui lacunas e reduz a confianca da explicacao.")
    alerts.extend(_support_metric_alerts(period_metrics, metric_map, focus))
    alerts.extend(_dimension_alerts(root_cause_analysis or {}))
    return alerts or ["Nenhum alerta critico adicional na leitura gerencial inicial."]


def _support_metric_alerts(period_metrics: pd.DataFrame, metric_map: dict, focus: pd.Series) -> list[str]:
    alerts = []
    focus_index = int(focus.name) if isinstance(focus.name, int) else period_metrics.index[period_metrics["periodo"] == focus["periodo"]][0]
    previous_row = period_metrics.iloc[focus_index - 1] if focus_index > 0 else None
    if previous_row is None:
        return alerts

    cost_group = next((group for group in metric_map["support_metrics"] if "custo" in group), None)
    volume_group = next((group for group in metric_map["support_metrics"] if "volume" in group), None)
    if cost_group and volume_group and cost_group in period_metrics.columns and volume_group in period_metrics.columns:
        current_cost = _safe_float(focus.get(cost_group))
        previous_cost = _safe_float(previous_row.get(cost_group))
        current_volume = _safe_float(focus.get(volume_group))
        previous_volume = _safe_float(previous_row.get(volume_group))
        if None not in {current_cost, previous_cost, current_volume, previous_volume}:
            cost_delta = current_cost - previous_cost
            volume_delta = current_volume - previous_volume
            if cost_delta > 0 and volume_delta < 0:
                alerts.append(
                    f"Custo subiu enquanto volume caiu em {focus['periodo']}; revisar eficiencia, mix ou pressao de custo."
                )
    return alerts


def _dimension_alerts(root_cause_analysis: dict) -> list[str]:
    alerts = []
    ranking = root_cause_analysis.get("dimension_impact_ranking") or []
    if ranking:
        top = ranking[0]
        share_abs = _safe_float(top.get("share_of_abs_change")) or 0
        if share_abs >= 0.8:
            alerts.append(
                f"{top.get('name')} concentra mais de 80% da variacao em {top.get('label')}; validar dependencia excessiva."
            )
    return alerts


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
