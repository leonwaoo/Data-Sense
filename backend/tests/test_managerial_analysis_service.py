import pandas as pd

from app.models import DatasetSession
from app.services.managerial_analysis_service import (
    _build_time_context,
    _detect_analysis_domain,
    _map_metrics,
    build_managerial_analysis,
)
from app.services.dashboard_service import build_dashboard
from app.services.profile_service import build_profile


def _inventory_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Ano": [2024, 2024, 2024, 2024],
            "Month": ["JAN", "FEV", "MAR", "ABR"],
            "Produto": ["Cafe Arabica", "Cafe Arabica", "Cafe Arabica", "Cafe Arabica"],
            "FY GAAP": ["FY24", "FY24", "FY24", "FY24"],
            "Estoque Total (TON)": [1000, 1100, 950, 760],
            "Estoque Fabrica (TON)": [700, 720, 690, 650],
            "Volume Industrializado (TON)": [120, 130, 180, 210],
            "Custo (R$/TON)": [450, 455, 470, 480],
        }
    )
    return DatasetSession(dataset_id="teste", file_name="estoque.xlsx", dataframe=dataframe)


def _multi_dimension_inventory_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Ano": [2025, 2025, 2025, 2025, 2025, 2025],
            "Month": ["JAN", "JAN", "FEV", "FEV", "MAR", "MAR"],
            "Produto": ["Cafe A", "Cafe B", "Cafe A", "Cafe B", "Cafe A", "Cafe B"],
            "Categoria": ["Arabica", "Conilon", "Arabica", "Conilon", "Arabica", "Conilon"],
            "FY GAAP": ["FY25", "FY25", "FY25", "FY25", "FY25", "FY25"],
            "Estoque Total (TON)": [1000, 500, 900, 520, 100, 530],
            "Estoque Fabrica (TON)": [700, 300, 650, 310, 180, 320],
            "Volume Industrializado (TON)": [120, 80, 130, 90, 460, 95],
            "Custo (R$/TON)": [450, 440, 455, 442, 470, 445],
        }
    )
    return DatasetSession(dataset_id="teste-multi", file_name="estoque_multi.xlsx", dataframe=dataframe)


def _year_over_year_inventory_dataset() -> DatasetSession:
    rows = []
    for year, values in {
        2024: [800, 850, 900, 920],
        2025: [1000, 1100, 950, 760],
    }.items():
        for month, value in zip(["JAN", "FEV", "MAR", "ABR"], values, strict=True):
            rows.append(
                {
                    "Ano": year,
                    "Month": month,
                    "Produto": "Cafe Arabica",
                    "FY GAAP": f"FY{str(year)[-2:]}",
                    "Estoque Total (TON)": value,
                    "Estoque Fabrica (TON)": value * 0.7,
                    "Volume Industrializado (TON)": value * 0.2,
                    "Custo (R$/TON)": 450 + (year - 2024) * 15,
                }
            )
    return DatasetSession(dataset_id="teste-yoy", file_name="estoque_yoy.xlsx", dataframe=pd.DataFrame(rows))


def _cost_up_volume_down_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Ano": [2025, 2025, 2025],
            "Month": ["JAN", "FEV", "MAR"],
            "Produto": ["Cafe Arabica", "Cafe Arabica", "Cafe Arabica"],
            "FY GAAP": ["FY25", "FY25", "FY25"],
            "Estoque Total (TON)": [1000, 980, 400],
            "Estoque Fabrica (TON)": [700, 690, 280],
            "Volume Industrializado (TON)": [200, 180, 120],
            "Custo (R$/TON)": [450, 460, 490],
        }
    )
    return DatasetSession(dataset_id="teste-custo-volume", file_name="estoque_alerta.xlsx", dataframe=dataframe)


def _sales_client_channel_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Ano": [2025, 2025, 2025, 2025, 2025, 2025],
            "Month": ["JAN", "JAN", "FEV", "FEV", "MAR", "MAR"],
            "Cliente": ["Cliente A", "Cliente B", "Cliente A", "Cliente B", "Cliente A", "Cliente B"],
            "Canal": ["Online", "Loja", "Online", "Loja", "Online", "Loja"],
            "Produto": ["Produto X", "Produto Y", "Produto X", "Produto Y", "Produto X", "Produto Y"],
            "Receita": [1000, 600, 1250, 610, 400, 620],
            "Quantidade": [10, 6, 12, 6, 4, 6],
            "Desconto": [20, 15, 25, 15, 80, 15],
        }
    )
    return DatasetSession(dataset_id="teste-vendas", file_name="vendas.xlsx", dataframe=dataframe)


def _rich_sales_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Ano": [2024, 2024, 2024, 2024, 2024, 2024, 2024, 2024],
            "Month": ["SET", "SET", "OUT", "OUT", "NOV", "NOV", "DEZ", "DEZ"],
            "Cliente": [
                "Distribuidora Centro",
                "Cliente B",
                "Distribuidora Centro",
                "Cliente B",
                "Distribuidora Centro",
                "Cliente B",
                "Distribuidora Centro",
                "Cliente B",
            ],
            "Canal": ["E-commerce", "Loja", "E-commerce", "Loja", "E-commerce", "Loja", "E-commerce", "Loja"],
            "Produto": ["Cafe Robusta", "Cafe Organico", "Cafe Robusta", "Cafe Organico", "Cafe Robusta", "Cafe Organico", "Cafe Robusta", "Cafe Organico"],
            "Receita": [100, 80, 120, 90, 130, 95, 660, 100],
            "Qtd Pedidos": [5, 4, 6, 4, 7, 5, 28, 5],
            "Volume Vendido": [50, 20, 55, 22, 58, 25, 260, 24],
            "Desconto (%)": [0.05, 0.02, 0.05, 0.02, 0.06, 0.02, 0.08, 0.02],
            "Devolucoes": [0, 0, 1, 0, 1, 0, 3, 0],
            "OEE": [0.81, 0.79, 0.82, 0.8, 0.83, 0.8, 0.76, 0.81],
            "Taxa Aprovacao": [0.92, 0.93, 0.91, 0.94, 0.9, 0.94, 0.86, 0.95],
            "Margem EBITDA": [0.18, 0.38, 0.19, 0.39, 0.2, 0.4, 0.17, 0.42],
        }
    )
    return DatasetSession(dataset_id="teste-vendas-rico", file_name="vendas_rico.xlsx", dataframe=dataframe)


def _fiscal_year_sales_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "FY GAAP": ["FY24", "FY24", "FY24", "FY24", "FY25", "FY25"],
            "Month": ["OUT", "NOV", "DEZ", "DEZ", "JAN", "FEV"],
            "Cliente": ["A", "A", "A", "B", "A", "B"],
            "Canal": ["E-commerce", "E-commerce", "Loja", "Loja", "E-commerce", "Loja"],
            "Produto": ["Cafe", "Cafe", "Cafe", "Cafe Especial", "Cafe", "Cafe Especial"],
            "Receita Bruta (R$)": [100, 120, 200, 80, 180, 190],
            "Margem EBITDA": [0.2, 0.21, 0.24, 0.35, 0.22, 0.36],
        }
    )
    return DatasetSession(dataset_id="teste-vendas-fiscal", file_name="vendas_fiscal.xlsx", dataframe=dataframe)


def _month_only_sales_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Month": ["JAN", "FEV", "MAR"],
            "Produto": ["Cafe", "Cafe", "Cafe"],
            "Receita": [100, 120, 140],
        }
    )
    return DatasetSession(dataset_id="teste-vendas-mes", file_name="vendas_mes.xlsx", dataframe=dataframe)


def _purchase_supplier_item_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Ano": [2025, 2025, 2025, 2025, 2025, 2025],
            "Month": ["JAN", "JAN", "FEV", "FEV", "MAR", "MAR"],
            "Fornecedor": ["Fornecedor A", "Fornecedor B", "Fornecedor A", "Fornecedor B", "Fornecedor A", "Fornecedor B"],
            "Item": ["Insumo X", "Insumo Y", "Insumo X", "Insumo Y", "Insumo X", "Insumo Y"],
            "Comprador": ["Time 1", "Time 2", "Time 1", "Time 2", "Time 1", "Time 2"],
            "Valor Compra": [700, 500, 720, 520, 1500, 530],
            "Quantidade": [7, 5, 7, 5, 14, 5],
            "Prazo Dias": [12, 15, 13, 15, 25, 15],
        }
    )
    return DatasetSession(dataset_id="teste-compras", file_name="compras.xlsx", dataframe=dataframe)


def test_detect_analysis_domain_recognizes_inventory_operations() -> None:
    dataset = _inventory_dataset()
    profile = build_profile(dataset)

    domain = _detect_analysis_domain(profile["column_names"])

    assert domain["type"] == "estoque_operacao"
    assert domain["confidence"] >= 0.7


def test_map_metrics_prefers_inventory_total_over_support_drivers() -> None:
    dataset = _inventory_dataset()
    profile = build_profile(dataset)
    domain = _detect_analysis_domain(profile["column_names"])

    metric_map = _map_metrics(dataset.dataframe, profile, domain)

    assert metric_map["primary_metric"] == "Estoque Total (TON)"
    assert metric_map["support_metrics"]["estoque_fabrica"] == "Estoque Fabrica (TON)"
    assert metric_map["support_metrics"]["volume_operacional"] == "Volume Industrializado (TON)"
    assert metric_map["support_metrics"]["custo"] == "Custo (R$/TON)"


def test_build_time_context_uses_year_plus_month_fallback() -> None:
    dataset = _inventory_dataset()
    profile = build_profile(dataset)

    time_context = _build_time_context(dataset.dataframe, profile)

    assert time_context["available"] is True
    assert time_context["label"] == "Ano + Month"
    assert time_context["columns"] == ["Ano", "Month"]
    assert time_context["series"].dt.strftime("%Y-%m").tolist() == ["2024-01", "2024-02", "2024-03", "2024-04"]


def test_build_time_context_uses_fiscal_year_plus_month() -> None:
    dataset = _fiscal_year_sales_dataset()
    profile = build_profile(dataset)

    time_context = _build_time_context(dataset.dataframe, profile)

    assert time_context["available"] is True
    assert time_context["label"] == "FY GAAP + Month"
    assert time_context["columns"] == ["FY GAAP", "Month"]
    assert time_context["series"].dt.strftime("%Y-%m").tolist() == [
        "2024-10",
        "2024-11",
        "2024-12",
        "2024-12",
        "2025-01",
        "2025-02",
    ]


def test_managerial_analysis_ranks_dimension_contributors_and_concentration_alerts() -> None:
    dataset = _multi_dimension_inventory_dataset()

    analysis = build_managerial_analysis(dataset)

    root_cause = analysis["root_cause_analysis"]
    ranking = root_cause["dimension_impact_ranking"]
    dimension_narratives = analysis["dimension_narratives"]
    alerts = root_cause["concentration_alerts"]
    driver_labels = {driver["label"] for driver in root_cause["dimension_drivers"]}

    assert "Produto" in driver_labels
    assert "Categoria" in driver_labels
    assert ranking[0]["name"] == "Cafe A"
    assert ranking[0]["share_of_abs_change"] >= 0.9
    assert ranking[0]["concentration_level"] == "alta"
    assert ranking[0]["recurrence_flag"] in {"recorrente", "pontual"}
    assert "historical_mean" in ranking[0]
    assert dimension_narratives
    assert dimension_narratives[0]["label"] in {"Produto", "Categoria"}
    assert "managerial_impact" in dimension_narratives[0]
    assert any("Cafe A" in alert for alert in alerts)
    assert any("Cafe A" in alert for alert in analysis["alerts"])
    assert any("mais de 80%" in alert for alert in analysis["alerts"])


def test_managerial_analysis_builds_complete_comparative_summary() -> None:
    analysis = build_managerial_analysis(_year_over_year_inventory_dataset())

    comparative = analysis["comparative_summary"]
    labels = {card["label"] for card in comparative["cards"]}

    assert {"Ultimos 3 meses", "Acumulado do ano", "Media movel 3M", "Melhor mes", "Pior mes"}.issubset(labels)
    assert any("ultimos 3 meses" in reading.lower() for reading in comparative["readings"])
    assert any("2025" in reading for reading in comparative["readings"])


def test_managerial_analysis_emits_critical_drop_and_cost_vs_volume_alerts() -> None:
    analysis = build_managerial_analysis(_cost_up_volume_down_dataset())

    alerts = analysis["alerts"]

    assert any("Queda superior a 50%" in alert for alert in alerts)
    assert any("Custo subiu enquanto volume caiu" in alert for alert in alerts)


def test_managerial_analysis_uses_client_and_channel_for_sales() -> None:
    analysis = build_managerial_analysis(_sales_client_channel_dataset())

    assert analysis["context"]["domain"]["type"] == "vendas"
    labels = {item["label"] for item in analysis["root_cause_analysis"]["dimension_drivers"]}
    ranking_labels = {item["label"] for item in analysis["root_cause_analysis"]["dimension_impact_ranking"]}

    assert "Cliente" in labels
    assert "Canal" in labels
    assert "Cliente" in ranking_labels
    assert analysis["dimension_narratives"]


def test_managerial_analysis_uses_rich_sales_support_metrics_and_cross_context() -> None:
    analysis = build_managerial_analysis(_rich_sales_dataset())

    support_columns = set(analysis["context"]["metric_map"]["support_metrics"].values())
    ranking = analysis["root_cause_analysis"]["dimension_impact_ranking"]
    centro = next(item for item in ranking if item["name"] == "Distribuidora Centro")
    alerts = analysis["alerts"]

    assert {"Qtd Pedidos", "Volume Vendido", "Desconto (%)", "Devolucoes", "OEE", "Taxa Aprovacao", "Margem EBITDA"}.issubset(support_columns)
    assert any(item["dimension"] == "Canal" and item["name"] == "E-commerce" for item in centro["context"])
    assert any(item["dimension"] == "Produto" and item["name"] == "Cafe Robusta" for item in centro["context"])
    assert any("2024-12" in alert for alert in alerts)


def test_dashboard_uses_year_month_context_and_margin_ranking() -> None:
    dashboard = build_dashboard(_rich_sales_dataset())
    monthly = next(chart for chart in dashboard["charts"] if chart["id"] == "evolucao_mensal")
    margin = next(chart for chart in dashboard["charts"] if chart["id"].startswith("ranking_margem_"))

    periods = [row["periodo"] for row in monthly["data"]]
    assert periods == ["2024-09", "2024-10", "2024-11", "2024-12"]
    assert not any(str(period).startswith("2000-") for period in periods)
    assert margin["data"][0]["grupo"] == "Cafe Organico"


def test_dashboard_uses_fiscal_year_and_hides_null_chart() -> None:
    dashboard = build_dashboard(_fiscal_year_sales_dataset())
    monthly = next(chart for chart in dashboard["charts"] if chart["id"] == "evolucao_mensal")

    periods = [row["periodo"] for row in monthly["data"]]
    chart_ids = {chart["id"] for chart in dashboard["charts"]}
    kpi_labels = {kpi["label"] for kpi in dashboard["kpis"]}

    assert periods == ["2024-10", "2024-11", "2024-12", "2025-01", "2025-02"]
    assert not any(str(period).startswith("2000-") for period in periods)
    assert "nulos_por_coluna" not in chart_ids
    assert "Valores nulos" not in kpi_labels


def test_dashboard_does_not_publish_synthetic_2000_for_month_only_column() -> None:
    dashboard = build_dashboard(_month_only_sales_dataset())

    assert "2000-" not in str(dashboard["charts"])
    assert "2000-" not in str(dashboard["insights"])


def test_managerial_analysis_uses_supplier_and_item_for_purchases() -> None:
    analysis = build_managerial_analysis(_purchase_supplier_item_dataset())

    assert analysis["context"]["domain"]["type"] == "compras"
    labels = {item["label"] for item in analysis["root_cause_analysis"]["dimension_drivers"]}
    ranking_labels = {item["label"] for item in analysis["root_cause_analysis"]["dimension_impact_ranking"]}

    assert "Fornecedor" in labels
    assert "Item" in labels
    assert "Fornecedor" in ranking_labels
    assert analysis["dimension_narratives"]
