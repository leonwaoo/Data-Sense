import pandas as pd

from app.models import DatasetSession
from app.services.suggestion_service import MAX_SUGGESTIONS, build_suggested_questions


def _sales_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Data": ["2024-01-10", "2024-01-22", "2024-02-05", "2024-02-18", "2024-03-01"],
            "Produto": ["Cafe", "Cha", "Cafe", "Suco", "Cha"],
            "Fornecedor": ["Acme", "Beta", "Acme", "Gama", "Beta"],
            "Valor Total": [1200.0, 800.0, 1500.0, 600.0, 950.0],
        }
    )
    return DatasetSession(dataset_id="vendas", file_name="vendas.csv", dataframe=dataframe)


def _text_only_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Cidade": ["Sao Paulo", "Rio", "Sao Paulo", "Rio", None],
            "Bairro": ["Centro", "Sul", "Centro", "Sul", "Norte"],
        }
    )
    return DatasetSession(dataset_id="texto", file_name="locais.csv", dataframe=dataframe)


def test_sales_suggestions_use_real_columns_and_respect_cap() -> None:
    suggestions = build_suggested_questions(_sales_dataset())
    questions = [item["question"] for item in suggestions]

    assert len(suggestions) <= MAX_SUGGESTIONS
    assert all(set(item.keys()) == {"question", "category"} for item in suggestions)
    # A metrica detectada deve aparecer no total e a dimensao de negocio num ranking.
    assert "Qual o total de Valor Total?" in questions
    assert any("Top 5 Produto por Valor Total." == question for question in questions)
    assert "Mostre Valor Total por mes." in questions


def test_sales_suggestions_have_no_duplicates() -> None:
    suggestions = build_suggested_questions(_sales_dataset())
    questions = [item["question"] for item in suggestions]

    assert len(questions) == len(set(questions))


def test_text_only_dataset_keeps_structure_and_quality_questions() -> None:
    suggestions = build_suggested_questions(_text_only_dataset())
    questions = [item["question"] for item in suggestions]

    assert "Quantas linhas e colunas existem?" in questions
    # Sem metrica numerica, ainda assim oferece contagem por dimensao de texto.
    assert any(question.startswith("Mostre a contagem por") for question in questions)
    # Ha valores ausentes em Cidade, entao a pergunta de qualidade deve existir.
    assert "Qual coluna tem mais valores ausentes?" in questions
