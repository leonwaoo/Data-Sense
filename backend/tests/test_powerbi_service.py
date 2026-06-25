from io import BytesIO
from zipfile import ZipFile

import pandas as pd

from app.models import DatasetSession
from app.services.powerbi_service import build_powerbi_export


def _inventory_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Ano": [2025, 2025, 2025, 2025, 2025, 2025],
            "Month": ["JAN", "JAN", "FEV", "FEV", "MAR", "MAR"],
            "Produto": ["Cafe A", "Cafe B", "Cafe A", "Cafe B", "Cafe A", "Cafe B"],
            "FY GAAP": ["FY25", "FY25", "FY25", "FY25", "FY25", "FY25"],
            "Estoque Total (TON)": [1000, 500, 900, 520, 100, 530],
            "Estoque Fabrica (TON)": [700, 300, 650, 310, 180, 320],
            "Volume Industrializado (TON)": [120, 80, 130, 90, 460, 95],
            "Custo (R$/TON)": [450, 440, 455, 442, 470, 445],
        }
    )
    return DatasetSession(dataset_id="powerbi", file_name="dashboard.xlsx", dataframe=dataframe)


def test_powerbi_export_includes_dax_layout_and_indicators() -> None:
    content = build_powerbi_export(_inventory_dataset())

    with ZipFile(BytesIO(content)) as package:
        names = set(package.namelist())
        dax = package.read("medidas_dax.txt").decode("utf-8")
        readme = package.read("README.txt").decode("utf-8")
        layout = package.read("layout_sugerido.csv").decode("utf-8-sig")
        indicators = package.read("indicadores_powerbi.csv").decode("utf-8-sig")
        monthly = package.read("comparativo_mensal.csv").decode("utf-8-sig")

    assert {
        "medidas_dax.txt",
        "modelo_paginas.json",
        "layout_sugerido.csv",
        "indicadores_powerbi.csv",
    }.issubset(names)
    assert "Total Metrica = SUM('dados_tratados'[Estoque Total (TON)])" in dax
    assert "Media Movel 3M" in dax
    assert "layout_sugerido.csv" in readme
    assert "Resumo executivo" in layout
    assert "Principal contribuinte" in indicators
    assert "media_movel_3m" in monthly
    assert "acumulado_ano" in monthly
