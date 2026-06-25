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
        package.writestr("leituras_dimensao.csv", _csv_bytes(pd.DataFrame(_dimension_narrative_rows(analysis))))
        package.writestr("insights_gerenciais.csv", _csv_bytes(pd.DataFrame(_insight_rows(analysis))))
        package.writestr("graficos_sugeridos.csv", _csv_bytes(pd.DataFrame(_chart_rows(dashboard))))
        package.writestr("indicadores_powerbi.csv", _csv_bytes(pd.DataFrame(_indicator_rows(analysis, quality))))
        package.writestr("layout_sugerido.csv", _csv_bytes(pd.DataFrame(_layout_rows(analysis, dashboard))))
        package.writestr("modelo_paginas.json", _json_bytes(_page_model(analysis, dashboard)))
        package.writestr("medidas_dax.txt", _dax_measures_text(analysis))
        package.writestr("metadados.json", _json_bytes(_metadata(dataset, analysis, dashboard, quality)))
        package.writestr("README.txt", _readme_text(dataset, analysis))

    return output.getvalue()


def _monthly_rows(analysis: dict) -> list[dict]:
    rows = []
    running_year_totals: dict[int, float] = {}
    values: list[float] = []
    for item in analysis.get("monthly_comparisons", []):
        main_driver = item.get("main_driver") or {}
        period = str(item.get("period") or "")
        year = _period_year(period)
        value = _safe_float(item.get("value"))
        if value is not None:
            values.append(value)
        moving_average_3m = sum(values[-3:]) / len(values[-3:]) if values else None
        if year is not None and value is not None:
            running_year_totals[year] = running_year_totals.get(year, 0) + value
        rows.append(
            {
                "periodo": period,
                "ano": year,
                "mes": _period_month(period),
                "valor": item.get("value"),
                "valor_anterior": item.get("previous_value"),
                "variacao": item.get("variation"),
                "variacao_pct": item.get("variation_pct"),
                "media_movel_3m": _round_or_none(moving_average_3m),
                "acumulado_ano": _round_or_none(running_year_totals.get(year)) if year is not None else None,
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


def _indicator_rows(analysis: dict, quality: dict) -> list[dict]:
    context = analysis.get("context") or {}
    metric = ((context.get("metric_map") or {}).get("primary_metric")) or "metrica principal"
    comparative = analysis.get("comparative_summary") or {}
    variations = analysis.get("variations") or {}
    root_cause = analysis.get("root_cause_analysis") or {}
    rows = [
        {
            "indicador": "Metrica principal",
            "valor": metric,
            "detalhe": "Coluna inferida como principal para analise gerencial.",
            "pagina_sugerida": "Resumo executivo",
        },
        {
            "indicador": "Score de qualidade",
            "valor": quality.get("score"),
            "detalhe": "Usar como card de confiabilidade dos dados.",
            "pagina_sugerida": "Resumo executivo",
        },
    ]
    for key, label in [("latest", "Ultimo periodo"), ("largest_increase", "Maior alta"), ("largest_drop", "Maior queda")]:
        movement = variations.get(key) or {}
        if movement:
            rows.append(
                {
                    "indicador": label,
                    "valor": movement.get("period"),
                    "detalhe": f"Valor {movement.get('value')} | variacao {movement.get('variation')}",
                    "pagina_sugerida": "Comparativo mensal",
                }
            )
    for card in comparative.get("cards", [])[:5]:
        rows.append(
            {
                "indicador": card.get("label"),
                "valor": card.get("value"),
                "detalhe": card.get("detail"),
                "pagina_sugerida": "Comparativos gerenciais",
            }
        )
    for item in (analysis.get("dimension_narratives") or [])[:3]:
        rows.append(
            {
                "indicador": f"Leitura por {item.get('label')}",
                "valor": (item.get("top_movers") or [{}])[0].get("name"),
                "detalhe": item.get("managerial_impact"),
                "pagina_sugerida": "Leituras por dimensao",
            }
        )
    contributor = root_cause.get("primary_contributor") or {}
    if contributor:
        rows.append(
            {
                "indicador": "Principal contribuinte",
                "valor": contributor.get("name"),
                "detalhe": f"Variacao {contributor.get('variation')} | participacao {contributor.get('share_of_abs_change')}",
                "pagina_sugerida": "Causa raiz",
            }
        )
    return rows


def _layout_rows(analysis: dict, dashboard: dict) -> list[dict]:
    rows = [
        {
            "pagina": "Resumo executivo",
            "ordem": 1,
            "visual": "Cards KPI",
            "campos": "indicador, valor",
            "objetivo": "Mostrar metrica principal, score de qualidade, ultimo periodo, maior alta e maior queda.",
        },
        {
            "pagina": "Comparativo mensal",
            "ordem": 1,
            "visual": "Grafico de linhas",
            "campos": "comparativo_mensal[periodo], comparativo_mensal[valor]",
            "objetivo": "Acompanhar evolucao mensal da metrica principal.",
        },
        {
            "pagina": "Principais mudancas",
            "ordem": 2,
            "visual": "Colunas agrupadas",
            "campos": "comparativo_mensal[periodo], comparativo_mensal[variacao]",
            "objetivo": "Comparar mes contra mes.",
        },
        {
            "pagina": "Comparativos gerenciais",
            "ordem": 1,
            "visual": "Tabela executiva",
            "campos": "comparativo_mensal[periodo], comparativo_mensal[valor], comparativo_mensal[variacao_pct]",
            "objetivo": "Ler MoM, media movel, acumulado e meses fora do padrao.",
        },
        {
            "pagina": "Causa raiz",
            "ordem": 1,
            "visual": "Waterfall",
            "campos": "causa_raiz[entidade], causa_raiz[variacao]",
            "objetivo": "Mostrar os passos que explicam a alta ou queda.",
        },
        {
            "pagina": "Causa raiz",
            "ordem": 2,
            "visual": "Barras horizontais",
            "campos": "causa_raiz[entidade], causa_raiz[participacao_mudanca_abs]",
            "objetivo": "Mostrar quem concentrou a variacao.",
        },
        {
            "pagina": "Leituras por dimensao",
            "ordem": 1,
            "visual": "Tabela ou cards de texto",
            "campos": "leituras_dimensao[dimensao], leituras_dimensao[narrativa], leituras_dimensao[impacto_gerencial]",
            "objetivo": "Transformar causa raiz em leitura contextualizada por dimensao.",
        },
        {
            "pagina": "Alertas",
            "ordem": 1,
            "visual": "Cards de texto",
            "campos": "indicadores_powerbi[indicador], indicadores_powerbi[detalhe]",
            "objetivo": "Destacar alertas e concentracoes que exigem acao.",
        },
        {
            "pagina": "Recomendacoes",
            "ordem": 1,
            "visual": "Tabela ou cards de texto",
            "campos": "insights_gerenciais[recomendacao], insights_gerenciais[confianca]",
            "objetivo": "Abrir pela decisao gerencial antes da auditoria tecnica.",
        },
    ]
    for chart in _chart_rows(dashboard):
        rows.append(
            {
                "pagina": "Graficos sugeridos",
                "ordem": chart.get("ordem_sugerida"),
                "visual": chart.get("visual_power_bi_sugerido"),
                "campos": f"{chart.get('eixo')} x {chart.get('valor')}",
                "objetivo": chart.get("explicacao"),
            }
        )
    return rows


def _page_model(analysis: dict, dashboard: dict) -> dict:
    context = analysis.get("context") or {}
    return {
        "nome_modelo": "DataSense Power BI Starter",
        "dominio": context.get("domain"),
        "metrica_principal": ((context.get("metric_map") or {}).get("primary_metric")),
        "tabelas": [
            {"nome": "dados_tratados", "uso": "base principal"},
            {"nome": "comparativo_mensal", "uso": "serie temporal, MoM, media movel e acumulado"},
            {"nome": "causa_raiz", "uso": "waterfall e ranking de contribuicao"},
            {"nome": "leituras_dimensao", "uso": "narrativas executivas por dimensao"},
            {"nome": "insights_gerenciais", "uso": "narrativa executiva"},
            {"nome": "indicadores_powerbi", "uso": "cards executivos"},
        ],
        "paginas": [
            {"nome": "Resumo executivo", "visuais": ["Cards KPI", "Resumo gerencial", "Score de confiabilidade"]},
            {"nome": "Principais mudancas", "visuais": ["Linha mensal", "Variacao MoM", "Tabela de movimentos"]},
            {"nome": "Comparativos gerenciais", "visuais": ["MoM", "Media movel", "Acumulado YTD", "Melhor e pior mes"]},
            {"nome": "Causa raiz", "visuais": ["Waterfall", "Ranking de contribuicao", "Alertas de concentracao"]},
            {"nome": "Leituras por dimensao", "visuais": ["Narrativas executivas", "Peso relativo", "Historico por dimensao"]},
            {"nome": "Alertas", "visuais": ["Cards de alerta", "Concentracoes relevantes"]},
            {"nome": "Recomendacoes", "visuais": ["Acoes sugeridas", "Perguntas sugeridas"]},
            {"nome": "Qualidade dos dados", "visuais": ["Score", "Nulos", "Duplicatas", "Outliers"]},
        ],
        "graficos_datasense": dashboard.get("charts", []),
    }


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
                    "variacao_pct_vs_anterior": contributor.get("variation_pct_vs_previous"),
                    "participacao_mudanca_abs": contributor.get("share_of_abs_change"),
                    "participacao_mudanca_total": contributor.get("share_of_total_change"),
                    "media_historica_entidade": contributor.get("historical_mean"),
                    "delta_media_historica_entidade": contributor.get("historical_delta"),
                    "concentracao": contributor.get("concentration_level"),
                    "recorrencia": contributor.get("recurrence_flag"),
                    "leitura": next(
                        (
                            item.get("reading")
                            for item in (root_cause.get("dimension_impact_ranking") or [])
                            if item.get("dimension") == dimension_name and item.get("name") == contributor.get("name")
                        ),
                        None,
                    ),
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


def _dimension_narrative_rows(analysis: dict) -> list[dict]:
    rows = []
    for item in analysis.get("dimension_narratives") or []:
        top_movers = item.get("top_movers") or []
        top_names = " | ".join(str(mover.get("name")) for mover in top_movers[:3] if mover.get("name"))
        rows.append(
            {
                "dimensao": item.get("dimension"),
                "rotulo": item.get("label"),
                "principais_movimentos": top_names,
                "concentracao_top_1": (item.get("share_concentration") or {}).get("top_1"),
                "concentracao_top_3": (item.get("share_concentration") or {}).get("top_3"),
                "nivel_concentracao": (item.get("share_concentration") or {}).get("level"),
                "media_historica": (item.get("historical_comparison") or {}).get("historical_mean"),
                "delta_historico": (item.get("historical_comparison") or {}).get("historical_delta"),
                "narrativa": item.get("narrative"),
                "impacto_gerencial": item.get("managerial_impact"),
                "possiveis_causas": " | ".join(item.get("possible_causes") or []),
                "recomendacao": item.get("recommendation"),
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


def _dax_measures_text(analysis: dict) -> str:
    metric = ((analysis.get("context") or {}).get("metric_map") or {}).get("primary_metric") or "valor"
    safe_metric = str(metric).replace("]", "]]")
    return "\n".join(
        [
            "Medidas DAX sugeridas - DataSense",
            "",
            "-- Ajuste o nome da tabela/coluna caso voce renomeie os campos no Power BI.",
            f"Total Metrica = SUM('dados_tratados'[{safe_metric}])",
            "",
            f"Media Metrica = AVERAGE('dados_tratados'[{safe_metric}])",
            "",
            "Valor Mes Anterior =",
            "CALCULATE(",
            "    [Total Metrica],",
            "    DATEADD('Calendario'[Data], -1, MONTH)",
            ")",
            "",
            "Variacao MoM = [Total Metrica] - [Valor Mes Anterior]",
            "",
            "Variacao MoM % = DIVIDE([Variacao MoM], [Valor Mes Anterior])",
            "",
            "Acumulado Ano = TOTALYTD([Total Metrica], 'Calendario'[Data])",
            "",
            "Media Movel 3M =",
            "AVERAGEX(",
            "    DATESINPERIOD('Calendario'[Data], MAX('Calendario'[Data]), -3, MONTH),",
            "    [Total Metrica]",
            ")",
            "",
            "Participacao Contribuicao =",
            "DIVIDE(",
            "    SUM('causa_raiz'[participacao_mudanca_abs]),",
            "    CALCULATE(SUM('causa_raiz'[participacao_mudanca_abs]), ALL('causa_raiz'[entidade]))",
            ")",
            "",
            "Mes Fora do Padrao =",
            "IF(MAX('comparativo_mensal'[severidade]) IN {\"danger\", \"warning\"}, 1, 0)",
            "",
            "Score Qualidade =",
            "MAXX(",
            "    FILTER('indicadores_powerbi', 'indicadores_powerbi'[indicador] = \"Score de qualidade\"),",
            "    VALUE('indicadores_powerbi'[valor])",
            ")",
        ]
    )


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
            "5. Importe leituras_dimensao.csv para criar a leitura executiva por dimensao.",
            "6. Importe insights_gerenciais.csv para apoiar alertas, perguntas e recomendacoes.",
            "7. Use graficos_sugeridos.csv como roteiro para montar visuais equivalentes.",
            "8. Abra medidas_dax.txt e copie as medidas sugeridas para o modelo.",
            "9. Use modelo_paginas.json e layout_sugerido.csv como guia de paginas e posicionamento.",
            "",
            "Arquivos de apoio:",
            "- medidas_dax.txt: medidas DAX iniciais para total, MoM, acumulado, media movel e participacao.",
            "- modelo_paginas.json: estrutura sugerida de paginas, tabelas e visuais.",
            "- layout_sugerido.csv: roteiro visual com pagina, ordem, campos e objetivo.",
            "- indicadores_powerbi.csv: KPIs prontos para cards executivos.",
            "- leituras_dimensao.csv: narrativas gerenciais por dimensao relevante.",
            "",
            "Graficos recomendados:",
            f"- Linha: periodo x {primary_metric}.",
            "- Colunas: periodo x variacao.",
            "- Waterfall: causa_raiz.csv filtrado em tipo_linha = waterfall.",
            "- Barras horizontais: causa_raiz.csv filtrado em tipo_linha = contribuinte, entidade x variacao.",
            "- Tabela: periodo, valor, variacao_pct, status, leitura_gerencial.",
            "- Cards/texto: leituras_dimensao.csv com narrativa, impacto e recomendacao.",
            "- Cartoes: ultimo periodo, maior alta, maior queda, score de qualidade.",
            "",
            "Ordem executiva sugerida: Resumo executivo, Principais mudancas, Comparativos gerenciais, Causa raiz, Leituras por dimensao, Alertas, Recomendacoes e Qualidade dos dados.",
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


def _period_year(period: str) -> int | None:
    try:
        return int(str(period)[:4])
    except (TypeError, ValueError):
        return None


def _period_month(period: str) -> int | None:
    try:
        return int(str(period)[5:7])
    except (TypeError, ValueError):
        return None


def _safe_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if pd.notna(parsed) else None


def _round_or_none(value: object) -> float | None:
    parsed = _safe_float(value)
    return round(parsed, 4) if parsed is not None else None


def _csv_bytes(dataframe: pd.DataFrame) -> bytes:
    buffer = StringIO()
    dataframe.to_csv(buffer, index=False)
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
