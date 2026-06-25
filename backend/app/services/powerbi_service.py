from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from app.models import DatasetSession
from app.services.dashboard_service import build_dashboard
from app.services.managerial_analysis_service import build_managerial_analysis
from app.services.quality_service import build_quality_report


def build_powerbi_export(dataset: DatasetSession) -> bytes:
    analysis = build_managerial_analysis(dataset)
    dashboard = build_dashboard(dataset)
    quality = build_quality_report(dataset)

    output = BytesIO()
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as package:
        package.writestr("dados_tratados.csv", _csv_bytes(dataset.dataframe))
        package.writestr("comparativo_mensal.csv", _csv_bytes(pd.DataFrame(_monthly_rows(analysis))))
        package.writestr("causa_raiz.csv", _csv_bytes(pd.DataFrame(_root_cause_rows(analysis))))
        package.writestr("insights_gerenciais.csv", _csv_bytes(pd.DataFrame(_insight_rows(analysis))))
        package.writestr("graficos_sugeridos.csv", _csv_bytes(pd.DataFrame(_chart_rows(dashboard))))
        package.writestr("metadados.json", _json_bytes(_metadata(dataset, analysis, dashboard, quality)))
        package.writestr("README.txt", _readme_text(dataset, analysis))

    return output.getvalue()


def _monthly_rows(analysis: dict) -> list[dict]:
    rows = []
    for item in analysis.get("monthly_comparisons", []):
        main_driver = item.get("main_driver") or {}
        rows.append(
            {
                "periodo": item.get("period"),
                "valor": item.get("value"),
                "valor_anterior": item.get("previous_value"),
                "variacao": item.get("variation"),
                "variacao_pct": item.get("variation_pct"),
                "media_historica": item.get("historical_mean"),
                "z_score": item.get("z_score"),
                "status": item.get("status"),
                "severidade": item.get("severity"),
                "leitura_gerencial": item.get("managerial_reading"),
                "driver_principal": main_driver.get("column"),
                "driver_variacao": main_driver.get("variation"),
                "driver_variacao_pct": main_driver.get("variation_pct"),
            }
        )
    return rows


def _insight_rows(analysis: dict) -> list[dict]:
    rows = []
    for insight in analysis.get("insights", []):
        rows.append(
            {
                "titulo": insight.get("title"),
                "severidade": insight.get("severity"),
                "metrica": insight.get("metric"),
                "periodo": insight.get("period"),
                "mudanca": insight.get("what_changed"),
                "quanto_mudou": insight.get("how_much"),
                "onde_mudou": insight.get("where"),
                "possiveis_causas": " | ".join(insight.get("possible_causes") or []),
                "impacto_gerencial": insight.get("managerial_impact"),
                "recomendacao": insight.get("recommendation"),
                "confianca": insight.get("confidence"),
                "evidencias": " | ".join(insight.get("evidence") or []),
            }
        )
    return rows


def _root_cause_rows(analysis: dict) -> list[dict]:
    root_cause = analysis.get("root_cause_analysis") or {}
    if not root_cause:
        return []

    rows = []
    movement = root_cause.get("movement") or {}
    responsible = root_cause.get("responsible_month") or {}
    waterfall_steps = root_cause.get("waterfall", {}).get("steps") or []

    for dimension in root_cause.get("dimension_drivers") or []:
        dimension_name = dimension.get("dimension")
        for contributor in dimension.get("contributors") or []:
            rows.append(
                {
                    "tipo_linha": "contribuinte",
                    "periodo": root_cause.get("period"),
                    "periodo_anterior": root_cause.get("previous_period"),
                    "metrica": root_cause.get("metric"),
                    "direcao": movement.get("direction"),
                    "dimensao": dimension_name,
                    "entidade": contributor.get("name"),
                    "valor_atual": contributor.get("current_value"),
                    "valor_anterior": contributor.get("previous_value"),
                    "variacao": contributor.get("variation"),
                    "participacao_mudanca_abs": contributor.get("share_of_abs_change"),
                    "participacao_mudanca_total": contributor.get("share_of_total_change"),
                    "media_historica_periodo": responsible.get("historical_mean"),
                    "distancia_media_historica": responsible.get("historical_delta"),
                    "z_score": responsible.get("z_score"),
                    "confianca": root_cause.get("confidence"),
                    "recomendacao": root_cause.get("recommendation"),
                }
            )

    for index, step in enumerate(waterfall_steps, start=1):
        rows.append(
            {
                "tipo_linha": "waterfall",
                "periodo": root_cause.get("period"),
                "periodo_anterior": root_cause.get("previous_period"),
                "metrica": root_cause.get("metric"),
                "direcao": movement.get("direction"),
                "dimensao": (root_cause.get("waterfall") or {}).get("dimension"),
                "entidade": step.get("label"),
                "valor_atual": step.get("value"),
                "valor_anterior": None,
                "variacao": step.get("delta"),
                "participacao_mudanca_abs": None,
                "participacao_mudanca_total": None,
                "media_historica_periodo": responsible.get("historical_mean"),
                "distancia_media_historica": responsible.get("historical_delta"),
                "z_score": responsible.get("z_score"),
                "confianca": root_cause.get("confidence"),
                "recomendacao": f"Passo {index} do waterfall: {step.get('kind')}",
            }
        )

    return rows


def _chart_rows(dashboard: dict) -> list[dict]:
    rows = []
    for chart in dashboard.get("charts", []):
        chart_type = chart.get("type")
        rows.append(
            {
                "grafico": chart.get("title"),
                "tipo_datasense": chart_type,
                "visual_power_bi_sugerido": _powerbi_visual(chart_type),
                "eixo": chart.get("x"),
                "valor": chart.get("y"),
                "explicacao": chart.get("insight") or chart.get("subtitle"),
                "ordem_sugerida": len(rows) + 1,
            }
        )
    return rows


def _metadata(dataset: DatasetSession, analysis: dict, dashboard: dict, quality: dict) -> dict:
    context = analysis.get("context") or {}
    return {
        "arquivo_origem": dataset.file_name,
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "linhas": int(dataset.dataframe.shape[0]),
        "colunas": int(dataset.dataframe.shape[1]),
        "dominio": context.get("domain"),
        "metricas": context.get("metric_map"),
        "tempo": context.get("time"),
        "dimensoes": context.get("dimensions"),
        "score_qualidade": quality.get("score"),
        "titulo_dashboard": dashboard.get("title"),
        "subtitulo_dashboard": dashboard.get("subtitle"),
    }


def _readme_text(dataset: DatasetSession, analysis: dict) -> str:
    primary_metric = ((analysis.get("context") or {}).get("metric_map") or {}).get("primary_metric") or "metrica principal"
    return "\n".join(
        [
            "Pacote Power BI - DataSense",
            "",
            f"Arquivo de origem: {dataset.file_name}",
            "",
            "Como usar no Power BI:",
            "1. Extraia este ZIP em uma pasta.",
            "2. No Power BI Desktop, use Obter dados > Texto/CSV para importar dados_tratados.csv.",
            "3. Importe comparativo_mensal.csv para criar graficos de evolucao mes a mes.",
            "4. Importe causa_raiz.csv para criar waterfall, ranking de contribuicao e leitura de quem puxou a mudanca.",
            "5. Importe insights_gerenciais.csv para criar uma pagina de narrativa executiva.",
            "6. Use graficos_sugeridos.csv como roteiro para montar visuais equivalentes.",
            "",
            "Graficos recomendados:",
            f"- Linha: periodo x {primary_metric}.",
            "- Colunas: periodo x variacao.",
            "- Waterfall: causa_raiz.csv filtrado em tipo_linha = waterfall.",
            "- Barras horizontais: causa_raiz.csv filtrado em tipo_linha = contribuinte, entidade x variacao.",
            "- Tabela: periodo, valor, variacao_pct, status, leitura_gerencial.",
            "- Cartoes: ultimo periodo, maior alta, maior queda, score de qualidade.",
            "",
            "Observacao: o pacote nao gera um arquivo PBIX automaticamente; ele entrega os dados e o roteiro dos visuais prontos para importacao.",
        ]
    )


def _powerbi_visual(chart_type: str | None) -> str:
    if chart_type in {"line", "area"}:
        return "Grafico de linhas"
    if chart_type == "bar":
        return "Grafico de colunas agrupadas"
    if chart_type == "pie":
        return "Grafico de rosca"
    return "Tabela ou grafico automatico"


def _csv_bytes(dataframe: pd.DataFrame) -> bytes:
    buffer = StringIO()
    dataframe.to_csv(buffer, index=False)
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
