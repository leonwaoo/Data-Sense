import pandas as pd

from app.models import DatasetSession
from app.services.managerial_analysis_service import _build_time_context, _detect_analysis_domain, _map_metrics
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
