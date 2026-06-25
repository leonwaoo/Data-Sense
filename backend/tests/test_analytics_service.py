import pandas as pd

from app.models import DatasetSession
from app.services.analytics_service import answer_question


def _sales_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Data": ["2024-01-10", "2024-01-22", "2024-02-05", "2024-02-18"],
            "Produto": ["Cafe", "Cha", "Cafe", "Suco"],
            "Valor Total": [1200.0, 800.0, 1500.0, 600.0],
        }
    )
    return DatasetSession(dataset_id="vendas", file_name="vendas.csv", dataframe=dataframe)


def test_distinct_count_counts_unique_values() -> None:
    result = answer_question(_sales_dataset(), "Quantos produtos diferentes existem?")

    assert result["calculation"] == "nunique(Produto)"
    assert result["table"] == [{"coluna": "Produto", "valores_distintos": 3}]


def test_distinct_intent_has_priority_over_total_keyword() -> None:
    # "quantos" contem "quanto" (gatilho de total); a contagem distinta deve vencer.
    result = answer_question(_sales_dataset(), "Quantos clientes distintos temos por produto?")

    assert result["calculation"] == "nunique(Produto)"


def test_total_question_still_sums_metric() -> None:
    result = answer_question(_sales_dataset(), "Qual o total de Valor Total?")

    assert result["calculation"] == "sum(Valor Total)"
    assert result["table"] == [{"metrica": "Valor Total", "total": 4100.0}]
