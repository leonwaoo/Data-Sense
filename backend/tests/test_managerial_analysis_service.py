import pandas as pd

from app.models import DatasetSession
from app.services.managerial_analysis_service import (
    _build_time_context,
    _detect_analysis_domain,
    _map_metrics,
    build_managerial_analysis,
)
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


def test_managerial_analysis_ranks_dimension_contributors_and_concentration_alerts() -> None:
    dataset = _multi_dimension_inventory_dataset()

    analysis = build_managerial_analysis(dataset)

    root_cause = analysis["root_cause_analysis"]
    ranking = root_cause["dimension_impact_ranking"]
    alerts = root_cause["concentration_alerts"]
    driver_labels = {driver["label"] for driver in root_cause["dimension_drivers"]}

    assert "Produto" in driver_labels
    assert "Categoria" in driver_labels
    assert ranking[0]["name"] == "Cafe A"
    assert ranking[0]["share_of_abs_change"] >= 0.9
    assert any("Cafe A" in alert for alert in alerts)
    assert any("Cafe A" in alert for alert in analysis["alerts"])
