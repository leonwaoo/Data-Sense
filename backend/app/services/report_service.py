from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import partial
from io import BytesIO
from math import ceil
from pathlib import Path
from textwrap import wrap

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.models import DatasetSession
from app.services.dashboard_service import build_dashboard
from app.services.chart_service import suggest_charts
from app.services.column_heuristics import format_number
from app.services.date_utils import parse_common_dates
from app.services.managerial_context_service import looks_like_month_without_year
from app.services.managerial_analysis_service import build_managerial_analysis
from app.services.profile_service import build_profile
from app.services.quality_service import build_quality_report

_format_number = partial(format_number, none_text="n/d", compact_large=True)

MONTH_NAMES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


@dataclass(frozen=True)
class ReportChart:
    title: str
    chart_type: str
    labels: list[str]
    values: list[float]
    note: str


@dataclass(frozen=True)
class ReportContext:
    file_name: str
    generated_at: str
    profile: dict
    quality: dict
    managerial_analysis: dict
    insights: list[str]
    recommendations: list[str]
    charts: list[ReportChart]
    dashboard_kpis: list[dict]


def build_report_pdf(dataset: DatasetSession) -> bytes:
    context = build_report_context(dataset)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 18 * mm
    y = height - margin

    y = _pdf_header(pdf, context, margin, y, width)
    y = _pdf_section(pdf, "Resumo executivo", _managerial_summary_items(context), margin, y, width, height)
    y = _pdf_section(pdf, "Principais mudancas", _managerial_variation_items(context), margin, y, width, height)
    y = _pdf_section(pdf, "Causa raiz", _managerial_root_cause_items(context), margin, y, width, height)
    y = _pdf_section(pdf, "Leituras por dimensao", _managerial_dimension_items(context), margin, y, width, height)
    y = _pdf_section(pdf, "Alertas", _managerial_alert_items(context), margin, y, width, height)
    y = _pdf_section(pdf, "Recomendacoes", _managerial_recommendation_items(context), margin, y, width, height)

    for chart in context.charts:
        needed = 96 * mm
        if y - needed < margin:
            _pdf_footer(pdf, width)
            pdf.showPage()
            y = height - margin
        y = _pdf_chart(pdf, chart, margin, y, width)

    y = _pdf_section(pdf, "Detalhes tecnicos", _technical_detail_items(context), margin, y, width, height)
    if context.profile.get("date_conversion_suggestions"):
        y = _pdf_section(pdf, "Sugestoes de conversao de datas", _date_suggestion_items(context), margin, y, width, height)

    _pdf_footer(pdf, width)
    pdf.save()
    return buffer.getvalue()


def build_report_png(dataset: DatasetSession) -> bytes:
    context = build_report_context(dataset)
    managerial_count = sum(
        len(items)
        for items in [
            _managerial_summary_items(context),
            _managerial_variation_items(context),
            _managerial_root_cause_items(context),
            _managerial_dimension_items(context),
            _managerial_alert_items(context),
            _managerial_recommendation_items(context),
            _technical_detail_items(context),
        ]
    )
    canvas_height = (
        2100
        + managerial_count * 58
        + len(context.charts) * 380
        + len(context.insights) * 42
        + len(context.recommendations) * 42
    )
    image = Image.new("RGB", (1400, max(2600, canvas_height)), "#eef3f8")
    draw = ImageDraw.Draw(image)
    fonts = _load_fonts()
    x = 70
    y = 54
    max_width = 1260

    draw.rounded_rectangle((x, y, x + max_width, y + 220), radius=10, fill="#ffffff", outline="#dbe5ef")
    draw.text((x + 28, y + 28), "DataSense", fill="#0f766e", font=fonts["label"])
    draw.text((x + 28, y + 60), "Relatorio Analitico", fill="#0f172a", font=fonts["title"])
    draw.text((x + 28, y + 132), f"Arquivo: {_truncate(context.file_name, 72)}", fill="#334155", font=fonts["body"])
    draw.text((x + 28, y + 164), f"Gerado em: {context.generated_at}", fill="#64748b", font=fonts["small"])
    y += 250

    y = _png_section(draw, "Resumo executivo", _managerial_summary_items(context), fonts, x, y, max_width)
    y = _png_section(draw, "Principais mudancas", _managerial_variation_items(context), fonts, x, y, max_width)
    y = _png_section(draw, "Causa raiz", _managerial_root_cause_items(context), fonts, x, y, max_width)
    y = _png_section(draw, "Leituras por dimensao", _managerial_dimension_items(context), fonts, x, y, max_width)
    y = _png_section(draw, "Alertas", _managerial_alert_items(context), fonts, x, y, max_width)
    y = _png_section(draw, "Recomendacoes", _managerial_recommendation_items(context), fonts, x, y, max_width)

    for chart in context.charts:
        y = _png_chart(draw, chart, fonts, x, y, max_width)

    y = _png_section(draw, "Detalhes tecnicos", _technical_detail_items(context), fonts, x, y, max_width)
    if context.profile.get("date_conversion_suggestions"):
        y = _png_section(draw, "Sugestoes de conversao de datas", _date_suggestion_items(context), fonts, x, y, max_width)

    cropped = image.crop((0, 0, 1400, min(image.height, y + 70)))
    output = BytesIO()
    cropped.save(output, format="PNG", optimize=True)
    return output.getvalue()


def build_report_context(dataset: DatasetSession) -> ReportContext:
    profile = build_profile(dataset)
    quality = build_quality_report(dataset)
    managerial_analysis = build_managerial_analysis(dataset)
    dashboard = build_dashboard(dataset)
    charts = _build_report_charts(dataset, profile)
    insights = _build_insights(dataset, profile, quality, charts)
    recommendations = quality["recommendations"][:]

    return ReportContext(
        file_name=dataset.file_name,
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
        profile=profile,
        quality=quality,
        managerial_analysis=managerial_analysis,
        insights=insights,
        recommendations=recommendations,
        charts=charts,
        dashboard_kpis=dashboard.get("kpis", []),
    )


def _managerial_summary_items(context: ReportContext) -> list[str]:
    analysis = context.managerial_analysis or {}
    summary = [str(item) for item in analysis.get("summary", []) if item]
    return summary[:4] or ["Nao houve evidencia suficiente para gerar resumo executivo confiavel."]


def _managerial_variation_items(context: ReportContext) -> list[str]:
    analysis = context.managerial_analysis or {}
    variations = analysis.get("variations") or {}
    items = []
    latest = variations.get("latest")
    drop = variations.get("largest_drop")
    trend = variations.get("trend") or {}
    if latest:
        items.append(_movement_sentence("Movimento recente", latest))
    if drop:
        items.append(_movement_sentence("Maior queda", drop))
    if trend:
        items.append(
            f"Tendencia geral dos ultimos periodos: {trend.get('direction', 'indefinida')}."
        )
    return items or ["Nao ha variacao temporal suficiente para diagnostico gerencial."]


def _managerial_comparative_items(context: ReportContext) -> list[str]:
    analysis = context.managerial_analysis or {}
    comparative = analysis.get("comparative_summary") or {}
    cards = comparative.get("cards") or []
    readings = [str(item) for item in comparative.get("readings", []) if item]
    items = []
    for card in cards[:5]:
        label = card.get("label") or "Comparativo"
        value = card.get("value") or "n/d"
        detail = card.get("detail") or ""
        items.append(f"{label}: {value}. {detail}")
    items.extend(readings[:4])
    return items[:8] or ["Sem comparativos gerenciais suficientes para exportacao."]


def _managerial_root_cause_items(context: ReportContext) -> list[str]:
    analysis = context.managerial_analysis or {}
    root_cause = analysis.get("root_cause_analysis") or {}
    if not root_cause:
        return ["Sem causa raiz suficiente para exportacao nesta base."]

    items = [str(item) for item in (root_cause.get("summary") or [])[:3] if item]
    movement = root_cause.get("movement") or {}
    responsible = root_cause.get("responsible_month") or {}
    primary_contributor = root_cause.get("primary_contributor") or {}
    impact_ranking = root_cause.get("dimension_impact_ranking") or []
    concentration_alerts = root_cause.get("concentration_alerts") or []

    if movement:
        items.append(
            f"O principal movimento ocorreu em {_period_label(root_cause.get('period'))}."
        )
    if primary_contributor:
        items.append(
            f"O primeiro ponto para validar e {primary_contributor.get('name')}."
        )
    for item in impact_ranking[:3]:
        items.append(
            f"Tambem merece atencao: {item.get('name')} em {item.get('label')}."
        )
    for alert in concentration_alerts[:2]:
        items.append(f"Concentracao relevante: {alert}")

    confidence = root_cause.get("confidence")
    recommendation = root_cause.get("recommendation")
    if recommendation:
        items.append(f"Acao recomendada: {recommendation}.")
    return items[:10] or ["Sem causa raiz suficiente para exportacao nesta base."]


def _technical_detail_items(context: ReportContext) -> list[str]:
    profile = context.profile
    quality = context.quality
    analysis = context.managerial_analysis or {}
    context_payload = analysis.get("context") or {}
    metric_map = context_payload.get("metric_map") or {}
    time_payload = context_payload.get("time") or {}
    items = [
        f"Arquivo: {context.file_name}.",
        f"Estrutura: {profile['rows']} linhas e {profile['columns']} colunas.",
        f"Qualidade: pontuacao {quality.get('score')}/100, {quality.get('missing_total')} nulos e {quality.get('duplicate_rows')} duplicatas.",
    ]
    if metric_map.get("primary_metric"):
        items.append(f"Indicador principal usado pelo motor: {metric_map.get('primary_metric')}.")
    if time_payload.get("label"):
        items.append(f"Periodo usado pelo motor: {time_payload.get('label')}.")
    if metric_map.get("support_metrics"):
        support = ", ".join(str(value) for value in metric_map["support_metrics"].values())
        items.append(f"Fatores de apoio: {support}.")
    return items


def _managerial_dimension_items(context: ReportContext) -> list[str]:
    analysis = context.managerial_analysis or {}
    narratives = analysis.get("dimension_narratives") or ((analysis.get("root_cause_analysis") or {}).get("dimension_narratives")) or []
    items = []
    for item in narratives[:4]:
        text = f"{item.get('label')}: {item.get('narrative')}"
        impact = item.get("managerial_impact")
        recommendation = item.get("recommendation")
        if impact:
            text += f" Impacto: {impact}"
        if recommendation:
            text += f" Recomendacao: {recommendation}"
        items.append(text)
    return items or ["Sem leituras por dimensao suficientes para exportacao."]


def _managerial_monthly_items(context: ReportContext) -> list[str]:
    analysis = context.managerial_analysis or {}
    comparisons = analysis.get("monthly_comparisons") or []
    items = []
    for item in comparisons[-8:]:
        driver = item.get("main_driver") or {}
        driver_text = f" Fator de apoio observado: {driver.get('column')}." if driver else ""
        items.append(
            f"{_period_label(item.get('period'))}: {item.get('status', 'sem status')}; "
            f"valor {_format_number(item.get('value'))}; "
            f"variacao {_format_signed_number(item.get('variation'))} ({_format_pct(item.get('variation_pct'))})."
            f"{driver_text}"
        )
    return items or ["Sem comparativo mensal disponivel para exportacao."]


def _managerial_insight_items(context: ReportContext) -> list[str]:
    analysis = context.managerial_analysis or {}
    insights = analysis.get("insights") or []
    items = []
    for insight in insights[:4]:
        title = insight.get("title") or "Insight gerencial"
        how_much = insight.get("how_much") or ""
        where = insight.get("where") or ""
        impact = insight.get("managerial_impact") or ""
        recommendation = insight.get("recommendation") or ""
        confidence = insight.get("confidence") or "n/d"
        sentence = f"{title}: {how_much}"
        if where:
            sentence += f" Onde mudou: {where}"
        if impact:
            sentence += f" Impacto: {impact}"
        if recommendation:
            sentence += f" Recomendacao: {recommendation}"
        sentence += f" Confianca: {confidence}."
        items.append(sentence)
    return items or ["Sem insights gerenciais suficientes para exportacao."]


def _managerial_alert_items(context: ReportContext) -> list[str]:
    analysis = context.managerial_analysis or {}
    return [f"Validar: {item}" for item in (analysis.get("alerts") or [])[:5]] or ["Nenhum alerta gerencial adicional foi identificado."]


def _managerial_recommendation_items(context: ReportContext) -> list[str]:
    analysis = context.managerial_analysis or {}
    recommendations = [f"Acao: {item}" for item in (analysis.get("recommendations") or [])[:4]]
    questions = [f"Pergunta sugerida: {item}" for item in (analysis.get("suggested_questions") or [])[:3]]
    return recommendations + questions or ["Nenhuma recomendacao gerencial adicional foi identificada."]


def _movement_sentence(label: str, movement: dict) -> str:
    period = _period_label(movement.get("period"))
    variation = _report_float(movement.get("variation")) or 0
    direction = "subiu" if variation > 0 else "caiu" if variation < 0 else "ficou estavel"
    return (
        f"{label}: em {period}, o indicador {direction}. Os valores detalhados ficam em Detalhes tecnicos."
    )


def _summary_items(context: ReportContext) -> list[str]:
    profile = context.profile
    items = [
        f"{profile['rows']} linhas e {profile['columns']} colunas analisadas.",
        f"{len(profile['numeric_columns'])} colunas numericas, {len(profile['categorical_columns'])} categoricas e {len(profile['datetime_columns'])} de data.",
        "Formato aceito e processado com perfil automatico, auditoria de qualidade e sugestoes de graficos.",
    ]
    ingest_report = profile.get("ingest_report", {})
    if ingest_report.get("header_row_number"):
        items.append(
            f"Cabecalho detectado na linha {ingest_report['header_row_number']}; "
            f"{ingest_report.get('metadata_rows_skipped', 0)} linha(s) antes dele foram tratadas como metadado."
        )
    for warning in ingest_report.get("warnings", [])[:2]:
        items.append(f"Sanidade de ingestao: {warning}")
    return items


def _date_suggestion_items(context: ReportContext) -> list[str]:
    suggestions = context.profile.get("date_conversion_suggestions", [])
    return [suggestion["message"] for suggestion in suggestions[:5]]


def _quality_items(context: ReportContext) -> list[str]:
    quality = context.quality
    empty_columns = quality["empty_columns"]
    outliers = quality.get("numeric_outliers", {})
    items = [
        f"Pontuacao de qualidade: {quality['score']}/100.",
        f"Valores ausentes: {quality['missing_total']}.",
        f"Linhas duplicadas: {quality['duplicate_rows']}.",
        f"Colunas vazias: {len(empty_columns)}.",
        f"Colunas com outliers numericos: {len(outliers)}.",
    ]
    for item in quality.get("score_breakdown", []):
        items.append(
            f"{item['label']}: peso {item['weight']} pontos, perda {item['lost_points']} ponto(s). {item['detail']}"
        )
    for item in quality.get("numeric_outlier_details", [])[:4]:
        items.append(
            f"Outlier nomeado: {item['column']} linha {item['row_index']} com valor {_format_number(item['value'])}, "
            f"{item['deviation_ratio']}x distante da media."
        )
    return items


def _build_insights(dataset: DatasetSession, profile: dict, quality: dict, charts: list[ReportChart]) -> list[str]:
    insights: list[str] = []

    business_charts = [chart for chart in charts if chart.title != "Valores ausentes por coluna"] or charts
    for chart in business_charts:
        if chart.values:
            best_index = max(range(len(chart.values)), key=lambda index: chart.values[index])
            insights.append(
                f"No grafico '{chart.title}', o maior valor aparece em {chart.labels[best_index]}: {_format_number(chart.values[best_index])}."
            )
            break

    if profile["numeric_columns"]:
        first_numeric = profile["numeric_columns"][0]
        total = pd.to_numeric(dataset.dataframe[first_numeric], errors="coerce").sum()
        insights.append(f"A coluna numerica {first_numeric} soma {_format_number(float(total))}.")

    insights.append(_quality_score_sentence(quality["score"]))

    missing_by_column = quality.get("missing_by_column", {})
    if missing_by_column:
        top_missing = max(missing_by_column.items(), key=lambda item: item[1])
        if top_missing[1] > 0:
            insights.append(f"A coluna com mais valores ausentes e {top_missing[0]}, com {top_missing[1]} ocorrencias.")
        else:
            insights.append("Nao foram encontrados valores ausentes nas colunas avaliadas.")

    if quality["duplicate_rows"]:
        insights.append(f"Foram encontradas {quality['duplicate_rows']} linhas duplicadas que merecem validacao.")
    else:
        insights.append("Nao foram encontradas linhas duplicadas.")

    return insights[:6]


def _quality_score_sentence(score: int) -> str:
    if score >= 90:
        return "A qualidade geral esta alta, com poucos pontos de atencao."
    if score >= 70:
        return "A qualidade geral esta boa, mas ha ajustes importantes antes de decisoes finais."
    return "A qualidade geral exige revisao antes de usar o arquivo para decisoes."


def _build_report_charts(dataset: DatasetSession, profile: dict) -> list[ReportChart]:
    charts: list[ReportChart] = []

    for chart_payload in build_dashboard(dataset).get("charts", []):
        if chart_payload.get("id") in {"nulos_por_coluna", "score_qualidade"}:
            continue
        chart = _chart_from_dashboard_payload(chart_payload)
        if chart:
            charts.append(chart)
        if len(charts) >= 3:
            break

    if len(charts) >= 3:
        return charts

    for suggestion in suggest_charts(dataset):
        chart = _chart_from_suggestion(dataset, suggestion)
        if chart:
            charts.append(chart)
        if len(charts) >= 3:
            break

    return charts


def _chart_from_dashboard_payload(payload: dict) -> ReportChart | None:
    x_column = payload.get("x")
    y_column = payload.get("y")
    data = payload.get("data", [])
    if not x_column or not y_column or not data:
        return None

    labels: list[str] = []
    values: list[float] = []
    chart_type = "line" if payload.get("type") in {"line", "area"} else "bar"
    limited_data = data[:24] if chart_type == "line" else data[:10]
    for row in limited_data:
        if x_column not in row or y_column not in row:
            continue
        labels.append(str(row[x_column]))
        values.append(float(row[y_column] or 0))

    if not labels:
        return None

    return ReportChart(
        title=_truncate(str(payload.get("title") or "Grafico automatico"), 72),
        chart_type=chart_type,
        labels=labels,
        values=values,
        note=str(payload.get("insight") or payload.get("subtitle") or "Grafico gerado automaticamente pelo DataSense."),
    )


def _chart_from_suggestion(dataset: DatasetSession, suggestion: dict) -> ReportChart | None:
    df = dataset.dataframe.copy()
    x_column = suggestion["x"]
    y_column = suggestion["y"]

    if x_column not in df.columns or y_column not in df.columns:
        return None

    if suggestion["type"] == "line":
        dates = parse_common_dates(df[x_column])
        if looks_like_month_without_year(x_column, dates):
            return None
        values = pd.to_numeric(df[y_column], errors="coerce")
        result = (
            pd.DataFrame({"periodo": dates.dt.to_period("M").astype(str), "valor": values})
            .dropna()
            .query("periodo != 'NaT'")
            .groupby("periodo", as_index=False)["valor"]
            .sum()
            .sort_values("periodo")
        )
        if result.empty:
            return None
        return ReportChart(
            title=_truncate(str(suggestion["title"]), 72),
            chart_type="line",
            labels=result["periodo"].astype(str).tolist()[:24],
            values=[float(value) for value in result["valor"].tolist()[:24]],
            note=str(suggestion["reason"]),
        )

    if suggestion["type"] == "bar":
        values = pd.to_numeric(df[y_column], errors="coerce")
        result = (
            pd.DataFrame({"grupo": df[x_column].astype(str), "valor": values})
            .dropna()
            .groupby("grupo", as_index=False)["valor"]
            .sum()
            .sort_values("valor", ascending=False)
            .head(10)
        )
        if result.empty:
            return None
        return ReportChart(
            title=_truncate(str(suggestion["title"]), 72),
            chart_type="bar",
            labels=result["grupo"].astype(str).tolist(),
            values=[float(value) for value in result["valor"].tolist()],
            note=str(suggestion["reason"]),
        )

    return None


def _pdf_header(pdf: canvas.Canvas, context: ReportContext, margin: float, y: float, width: float) -> float:
    pdf.setFillColor(colors.HexColor("#0f766e"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, y, "DataSense")
    pdf.setFillColor(colors.HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(margin, y - 26, "Relatorio Analitico")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#475569"))
    pdf.drawString(margin, y - 46, f"Arquivo: {_truncate(context.file_name, 76)}")
    pdf.drawRightString(width - margin, y - 46, f"Gerado em: {context.generated_at}")
    pdf.setStrokeColor(colors.HexColor("#dbe5ef"))
    pdf.line(margin, y - 62, width - margin, y - 62)
    return y - 88


def _pdf_kpi_cards(pdf: canvas.Canvas, context: ReportContext, margin: float, y: float, width: float) -> float:
    cards = _report_kpi_cards(context)
    gap = 8
    card_width = (width - 2 * margin - 3 * gap) / 4
    for index, (label, value) in enumerate(cards):
        x = margin + index * (card_width + gap)
        pdf.setFillColor(colors.HexColor("#f8fafc"))
        pdf.roundRect(x, y - 56, card_width, 56, 7, fill=1, stroke=0)
        pdf.setStrokeColor(colors.HexColor("#dbe5ef"))
        pdf.roundRect(x, y - 56, card_width, 56, 7, fill=0, stroke=1)
        pdf.setFillColor(colors.HexColor("#64748b"))
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(x + 10, y - 19, label)
        pdf.setFillColor(colors.HexColor("#0f172a"))
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(x + 10, y - 40, value)
    return y - 82


def _pdf_section(pdf: canvas.Canvas, title: str, items: list[str], margin: float, y: float, width: float, height: float) -> float:
    needed = 20 + sum(ceil(len(item) / 90) * 12 for item in items)
    if y - needed < margin:
        _pdf_footer(pdf, width)
        pdf.showPage()
        y = height - margin

    pdf.setFillColor(colors.HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(margin, y, title)
    y -= 17
    pdf.setFont("Helvetica", 9.5)
    pdf.setFillColor(colors.HexColor("#334155"))
    for item in items:
        lines = wrap(item, 105)
        pdf.drawString(margin + 8, y, "-")
        for index, line in enumerate(lines):
            pdf.drawString(margin + 18, y - index * 11, line)
        y -= max(1, len(lines)) * 11 + 4
    return y - 8


def _pdf_chart(pdf: canvas.Canvas, chart: ReportChart, margin: float, y: float, width: float) -> float:
    chart_w = width - 2 * margin
    chart_h = 48 * mm
    box_h = chart_h + 28 * mm

    pdf.setFillColor(colors.HexColor("#ffffff"))
    pdf.setStrokeColor(colors.HexColor("#dbe5ef"))
    pdf.roundRect(margin, y - box_h, chart_w, box_h, 7, fill=1, stroke=1)

    pdf.setFillColor(colors.HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(margin + 10, y - 16, _truncate(chart.title, 86))
    pdf.setFont("Helvetica", 8.5)
    pdf.setFillColor(colors.HexColor("#64748b"))
    pdf.drawString(margin + 10, y - 29, _truncate(chart.note, 104))

    chart_x = margin + 16
    chart_y = y - box_h + 20
    inner_w = chart_w - 32
    _pdf_draw_axes(pdf, chart_x, chart_y, inner_w, chart_h)

    if chart.chart_type == "line":
        _pdf_line_chart(pdf, chart, chart_x, chart_y, inner_w, chart_h)
    else:
        _pdf_bar_chart(pdf, chart, chart_x, chart_y, inner_w, chart_h)
    return y - box_h - 14


def _pdf_draw_axes(pdf: canvas.Canvas, x: float, y: float, width: float, height: float) -> None:
    pdf.setStrokeColor(colors.HexColor("#cbd5e1"))
    pdf.line(x, y, x + width, y)
    pdf.line(x, y, x, y + height)


def _pdf_bar_chart(pdf: canvas.Canvas, chart: ReportChart, x: float, y: float, width: float, height: float) -> None:
    values = _safe_chart_values(chart.values)
    if not values or max(abs(value) for value in values) == 0:
        _pdf_empty_chart_message(pdf, x, y, width, height)
        return

    min_value = min(min(values), 0)
    max_value = max(max(values), 0)
    span = max(max_value - min_value, 1)
    baseline = y + ((0 - min_value) / span) * (height - 22)
    gap = 7
    bar_width = (width - gap * (len(values) + 1)) / max(len(values), 1)
    pdf.setFillColor(colors.HexColor("#0f766e"))
    for index, value in enumerate(values):
        value_y = y + ((value - min_value) / span) * (height - 22)
        bar_bottom = min(baseline, value_y)
        bar_height = max(abs(value_y - baseline), 1.5)
        bx = x + gap + index * (bar_width + gap)
        pdf.rect(bx, bar_bottom, bar_width, bar_height, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor("#334155"))
        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(bx + bar_width / 2, y - 10, _truncate(chart.labels[index], 12))
        pdf.drawCentredString(bx + bar_width / 2, max(baseline, value_y) + 4, _format_number(value))
        pdf.setFillColor(colors.HexColor("#0f766e"))


def _pdf_line_chart(pdf: canvas.Canvas, chart: ReportChart, x: float, y: float, width: float, height: float) -> None:
    values = _safe_chart_values(chart.values)
    if not values or max(abs(value) for value in values) == 0:
        _pdf_empty_chart_message(pdf, x, y, width, height)
        return

    max_value = max(values)
    min_value = min(values)
    span = max(max_value - min_value, 1)
    points = []
    for index, value in enumerate(values):
        px = x + (index / max(len(values) - 1, 1)) * width
        py = y + ((value - min_value) / span) * (height - 18) + 6
        points.append((px, py))

    pdf.setStrokeColor(colors.HexColor("#0f766e"))
    pdf.setLineWidth(2)
    for start, end in zip(points, points[1:]):
        pdf.line(start[0], start[1], end[0], end[1])
    pdf.setFillColor(colors.HexColor("#0f766e"))
    label_step = _label_step(len(points), 8)
    for index, (px, py) in enumerate(points):
        pdf.circle(px, py, 2.5, fill=1, stroke=0)
        if index == 0 or index == len(points) - 1 or index % label_step == 0:
            pdf.setFillColor(colors.HexColor("#334155"))
            pdf.setFont("Helvetica", 7)
            pdf.drawCentredString(px, y - 10, _truncate(chart.labels[index], 10))
            pdf.setFillColor(colors.HexColor("#0f766e"))


def _pdf_empty_chart_message(pdf: canvas.Canvas, x: float, y: float, width: float, height: float) -> None:
    pdf.setFillColor(colors.HexColor("#64748b"))
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(x + width / 2, y + height / 2, "Sem valores suficientes para desenhar este grafico.")


def _pdf_footer(pdf: canvas.Canvas, width: float) -> None:
    pdf.setFillColor(colors.HexColor("#94a3b8"))
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(width / 2, 12 * mm, "Gerado automaticamente pelo DataSense")


def _png_kpi_cards(draw: ImageDraw.ImageDraw, context: ReportContext, fonts: dict, x: int, y: int) -> None:
    cards = _report_kpi_cards(context)
    width = 292
    for index, (label, value) in enumerate(cards):
        left = x + index * (width + 30)
        draw.rounded_rectangle((left, y, left + width, y + 108), radius=10, fill="#ffffff", outline="#dbe5ef")
        draw.text((left + 22, y + 20), label, fill="#64748b", font=fonts["small"])
        draw.text((left + 22, y + 50), value, fill="#0f172a", font=fonts["subtitle"])


def _report_kpi_cards(context: ReportContext) -> list[tuple[str, str]]:
    technical_labels = {"Registros", "Pontuacao de qualidade", "Valores nulos", "Duplicatas"}
    dashboard_cards = [
        (str(kpi.get("label", "")), str(kpi.get("value", "")))
        for kpi in context.dashboard_kpis
        if kpi.get("label") and kpi.get("value")
    ]
    business = [card for card in dashboard_cards if card[0] not in technical_labels]
    technical = [card for card in dashboard_cards if card[0] in technical_labels]
    cards = (business + technical)[:4]
    if len(cards) >= 4:
        return cards

    fallback = [
        ("Linhas", str(context.profile["rows"])),
        ("Colunas", str(context.profile["columns"])),
        ("Qualidade", f"{context.quality['score']}/100"),
        ("Nulos", str(context.quality["missing_total"])),
    ]
    return (cards + fallback)[:4]


def _png_section(draw: ImageDraw.ImageDraw, title: str, items: list[str], fonts: dict, x: int, y: int, max_width: int) -> int:
    wrapped_items = [_wrap_for_pixels(item, fonts["body"], 1120) for item in items]
    section_height = 62 + sum(max(1, len(lines)) * 28 + 8 for lines in wrapped_items)
    draw.rounded_rectangle((x, y, x + max_width, y + section_height), radius=10, fill="#ffffff", outline="#dbe5ef")
    draw.text((x + 24, y + 18), title, fill="#0f172a", font=fonts["section"])
    y += 56
    for lines in wrapped_items:
        draw.text((x + 30, y), "-", fill="#0f766e", font=fonts["body_bold"])
        for line in lines:
            draw.text((x + 54, y), line, fill="#334155", font=fonts["body"])
            y += 28
        y += 6
    return y + 28


def _png_chart(draw: ImageDraw.ImageDraw, chart: ReportChart, fonts: dict, x: int, y: int, max_width: int) -> int:
    height = 330
    draw.rounded_rectangle((x, y, x + max_width, y + height), radius=10, fill="#ffffff", outline="#dbe5ef")
    draw.text((x + 24, y + 18), _truncate(chart.title, 72), fill="#0f172a", font=fonts["section"])
    draw.text((x + 24, y + 50), _truncate(chart.note, 110), fill="#64748b", font=fonts["small"])
    chart_box = (x + 60, y + 104, x + max_width - 50, y + height - 54)
    _png_axes(draw, chart_box)
    if chart.chart_type == "line":
        _png_line_chart(draw, chart, chart_box, fonts)
    else:
        _png_bar_chart(draw, chart, chart_box, fonts)
    return y + height + 28


def _png_axes(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    draw.line((left, bottom, right, bottom), fill="#cbd5e1", width=2)
    draw.line((left, top, left, bottom), fill="#cbd5e1", width=2)


def _png_bar_chart(draw: ImageDraw.ImageDraw, chart: ReportChart, box: tuple[int, int, int, int], fonts: dict) -> None:
    left, top, right, bottom = box
    values = _safe_chart_values(chart.values)
    if not values or max(abs(value) for value in values) == 0:
        draw.text((left + 24, top + 54), "Sem valores suficientes para desenhar este grafico.", fill="#64748b", font=fonts["body"])
        return

    min_value = min(min(values), 0)
    max_value = max(max(values), 0)
    span = max(max_value - min_value, 1)
    baseline = int(bottom - ((0 - min_value) / span) * (bottom - top - 30))
    gap = 22
    bar_width = max(24, (right - left - gap * (len(values) + 1)) // max(len(values), 1))
    for index, value in enumerate(values):
        value_y = int(bottom - ((value - min_value) / span) * (bottom - top - 30))
        bar_top = min(baseline, value_y)
        bar_bottom = max(baseline, value_y)
        bx = left + gap + index * (bar_width + gap)
        draw.rounded_rectangle((bx, bar_top, bx + bar_width, max(bar_bottom, bar_top + 2)), radius=5, fill="#0f766e")
        label = _truncate(chart.labels[index], 16)
        draw.text((bx, bottom + 10), label, fill="#334155", font=fonts["tiny"])
        draw.text((bx, bar_top - 22), _format_number(value), fill="#0f172a", font=fonts["tiny"])


def _png_line_chart(draw: ImageDraw.ImageDraw, chart: ReportChart, box: tuple[int, int, int, int], fonts: dict) -> None:
    left, top, right, bottom = box
    values = _safe_chart_values(chart.values)
    if not values or max(abs(value) for value in values) == 0:
        draw.text((left + 24, top + 54), "Sem valores suficientes para desenhar este grafico.", fill="#64748b", font=fonts["body"])
        return

    max_value = max(values)
    min_value = min(values)
    span = max(max_value - min_value, 1)
    points = []
    for index, value in enumerate(values):
        px = int(left + (index / max(len(values) - 1, 1)) * (right - left))
        py = int(bottom - ((value - min_value) / span) * (bottom - top - 28) - 10)
        points.append((px, py))
    if len(points) > 1:
        draw.line(points, fill="#0f766e", width=5)
    label_step = _label_step(len(points), 8)
    for index, point in enumerate(points):
        draw.ellipse((point[0] - 6, point[1] - 6, point[0] + 6, point[1] + 6), fill="#0f766e")
        if index == 0 or index == len(points) - 1 or index % label_step == 0:
            draw.text((point[0] - 24, bottom + 10), _truncate(chart.labels[index], 10), fill="#334155", font=fonts["tiny"])


def _load_fonts() -> dict:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]

    regular = next((path for path in candidates if path.exists() and "bd" not in path.name.lower() and "Bold" not in path.name), None)
    bold = next((path for path in candidates if path.exists() and ("bd" in path.name.lower() or "Bold" in path.name)), regular)

    def font(size: int, bold_font: bool = False):
        path = bold if bold_font else regular
        if path:
            return ImageFont.truetype(str(path), size)
        return ImageFont.load_default()

    return {
        "title": font(50, True),
        "subtitle": font(30, True),
        "section": font(24, True),
        "body": font(20),
        "body_bold": font(20, True),
        "label": font(20, True),
        "small": font(17),
        "tiny": font(14),
    }


def _wrap_for_pixels(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        bbox = font.getbbox(candidate)
        if bbox[2] - bbox[0] <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [text]


def _safe_chart_values(values: list[float]) -> list[float]:
    return [float(value) for value in values if pd.notna(value)]


def _label_step(length: int, target: int) -> int:
    return max(1, ceil(length / max(target, 1)))


def _format_signed_number(value: object) -> str:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return "n/d"
    sign = "+" if parsed >= 0 else "-"
    return f"{sign}{_format_number(abs(parsed))}"


def _report_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if pd.notna(parsed) else None


def _format_pct(value: object) -> str:
    try:
        if pd.isna(value):
            return "n/d"
    except (TypeError, ValueError):
        pass
    try:
        return f"{float(value):.1%}".replace(".", ",")
    except (TypeError, ValueError):
        return "n/d"


def _period_label(value: object) -> str:
    text = _clean_display_text(str(value or ""))
    try:
        period = pd.Period(text, freq="M")
    except (TypeError, ValueError):
        return text
    return f"{period.month:02d} {MONTH_NAMES_PT.get(period.month, text)}/{period.year}"


def _truncate(value: str, limit: int) -> str:
    text = _clean_display_text(str(value))
    return text if len(text) <= limit else f"{text[: limit - 1]}..."


def _clean_display_text(value: str) -> str:
    text = "".join(character for character in str(value) if character.isprintable())
    text = " ".join(text.split())
    return text
