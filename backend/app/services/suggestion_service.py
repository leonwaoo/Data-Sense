"""Gera perguntas sugeridas especificas para cada dataset.

As sugestoes reaproveitam a mesma deteccao de coluna usada pelo motor de
respostas (`analytics_service`), garantindo que toda pergunta sugerida mapeia
para uma analise que o sistema realmente sabe responder.
"""

from app.models import DatasetSession
from app.services.analytics_service import (
    DATE_CANDIDATES,
    GROUP_CANDIDATES,
    _find_column,
    _select_metric_column,
)
from app.services.column_heuristics import normalize_text_for_search

MAX_SUGGESTIONS = 8
MAX_RANKINGS = 3


def build_suggested_questions(dataset: DatasetSession) -> list[dict]:
    df = dataset.dataframe
    suggestions: list[dict] = []
    seen: set[str] = set()

    def add(question: str, category: str) -> None:
        key = normalize_text_for_search(question)
        if not question or key in seen or len(suggestions) >= MAX_SUGGESTIONS:
            return
        seen.add(key)
        suggestions.append({"question": question, "category": category})

    metric_column = _select_metric_column(df, "")
    date_column = _find_column(df.columns, DATE_CANDIDATES)

    # 1. Estrutura basica sempre util como primeiro passo.
    add("Quantas linhas e colunas existem?", "estrutura")

    # 2. Metrica principal (maior valor analitico).
    if metric_column:
        add(f"Qual o total de {metric_column}?", "metrica")
        if date_column:
            add(f"Mostre {metric_column} por mes.", "tempo")

    # 3. Rankings pelas dimensoes de negocio detectadas.
    rankings = 0
    for _label, candidates in GROUP_CANDIDATES:
        if rankings >= MAX_RANKINGS:
            break
        group_column = _find_column(df.columns, candidates)
        if not group_column:
            continue
        if metric_column:
            add(f"Top 5 {group_column} por {metric_column}.", "ranking")
        else:
            add(f"Mostre a contagem por {group_column}.", "ranking")
        rankings += 1

    # 4. Media da metrica como aprofundamento.
    if metric_column:
        add(f"Qual a media de {metric_column}?", "metrica")

    # 5. Qualidade de dados, quando ha algo a investigar.
    if int(df.isna().sum().sum()) > 0:
        add("Qual coluna tem mais valores ausentes?", "qualidade")
    if int(df.duplicated().sum()) > 0:
        add("Existem linhas duplicadas?", "qualidade")

    return suggestions
