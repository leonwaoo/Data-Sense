from app.models import DatasetSession
from app.services.profile_service import build_profile


def suggest_charts(dataset: DatasetSession) -> list[dict]:
    profile = build_profile(dataset)
    numeric_columns = profile["numeric_columns"]
    categorical_columns = profile["categorical_columns"]
    datetime_columns = profile["datetime_columns"]
    suggestions: list[dict] = []

    value_column = _first_matching(
        numeric_columns,
        [
            "faturamento",
            "receita",
            "venda",
            "compra",
            "custo",
            "despesa",
            "valor",
            "total",
            "quantidade",
            "qtd",
            "amount",
        ],
    ) or (numeric_columns[0] if numeric_columns else None)
    category_column = _first_matching(
        categorical_columns,
        ["produto", "item", "categoria", "fornecedor", "cliente", "regiao", "estado", "cidade", "canal", "status"],
    ) or (categorical_columns[0] if categorical_columns else None)

    if category_column and value_column:
        suggestions.append(
            {
                "title": f"Total de {value_column} por {category_column}",
                "type": "bar",
                "x": category_column,
                "y": value_column,
                "reason": "Boa primeira visualizacao para comparar grupos do dataset.",
            }
        )

    if datetime_columns and value_column:
        suggestions.append(
            {
                "title": f"Evolucao de {value_column} ao longo do tempo",
                "type": "line",
                "x": datetime_columns[0],
                "y": value_column,
                "reason": "Ajuda a observar tendencia, sazonalidade e picos.",
            }
        )

    if len(numeric_columns) >= 2:
        suggestions.append(
            {
                "title": f"Relacao entre {numeric_columns[0]} e {numeric_columns[1]}",
                "type": "scatter",
                "x": numeric_columns[0],
                "y": numeric_columns[1],
                "reason": "Ajuda a detectar correlacao e possiveis outliers.",
            }
        )

    return suggestions


def _first_matching(columns: list[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        for column in columns:
            if candidate in column.lower():
                return column
    return None
