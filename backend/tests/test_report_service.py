import pandas as pd

from app.models import DatasetSession
from app.services.report_service import (
    _executive_section_plan,
    _managerial_comparative_items,
    _managerial_dimension_items,
    _managerial_monthly_items,
    _managerial_root_cause_items,
    _period_label,
    _technical_detail_items,
    build_report_context,
)


def _inventory_dataset() -> DatasetSession:
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
    return DatasetSession(dataset_id="relatorio", file_name="dashboard.xlsx", dataframe=dataframe)


def test_period_label_formats_month_with_order() -> None:
    assert _period_label("2025-03").endswith("/2025")
    assert _period_label("Produto A") == "Produto A"


def test_report_managerial_items_keep_executive_reading_and_technical_details() -> None:
    context = build_report_context(_inventory_dataset())

    root_items = _managerial_root_cause_items(context)
    monthly_items = _managerial_monthly_items(context)
    comparative_items = _managerial_comparative_items(context)
    dimension_items = _managerial_dimension_items(context)
    technical_items = _technical_detail_items(context)

    assert any("Ultimos 3 meses" in item for item in comparative_items)
    assert any("2025" in item for item in root_items)
    assert any("ponto para validar" in item and "Cafe A" in item for item in root_items)
    assert any("Concentracao relevante: Cafe A" in item for item in root_items)
    assert any("Movimento critico" in item for item in monthly_items)
    assert any("Produto:" in item or "Categoria:" in item for item in dimension_items)
    assert any("linhas" in item and "colunas" in item for item in technical_items)


def test_report_section_plan_uses_executive_order() -> None:
    context = build_report_context(_inventory_dataset())

    titles = [title for title, _items in _executive_section_plan(context)]

    assert titles == [
        "Resumo executivo",
        "Principais mudancas",
        "Comparativos gerenciais",
        "Causa raiz",
        "Alertas",
        "Recomendacoes",
        "Leituras por dimensao",
    ]
