import duckdb
import pandas as pd

from app.models import DatasetSession


def answer_question(dataset: DatasetSession, question: str) -> dict:
    normalized = question.lower()
    df = dataset.dataframe

    if "linhas" in normalized or "colunas" in normalized:
        return {
            "answer": f"O dataset possui {df.shape[0]} linhas e {df.shape[1]} colunas.",
            "calculation": "shape(dataframe)",
            "table": [{"linhas": int(df.shape[0]), "colunas": int(df.shape[1])}],
            "chart": None,
        }

    if "duplic" in normalized:
        duplicate_rows = int(df.duplicated().sum())
        return {
            "answer": f"Foram encontradas {duplicate_rows} linhas duplicadas.",
            "calculation": "dataframe.duplicated().sum()",
            "table": [{"linhas_duplicadas": duplicate_rows}],
            "chart": None,
        }

    if "ausente" in normalized or "nulo" in normalized:
        missing = df.isna().sum().astype(int).sort_values(ascending=False)
        top = missing.head(5).reset_index()
        top.columns = ["coluna", "valores_ausentes"]
        column = str(top.iloc[0]["coluna"])
        value = int(top.iloc[0]["valores_ausentes"])
        data = top.to_dict(orient="records")
        return {
            "answer": f"A coluna com mais valores ausentes e {column}, com {value} ocorrencias.",
            "calculation": "dataframe.isna().sum().sort_values(desc)",
            "table": data,
            "chart": {"type": "bar", "x": "coluna", "y": "valores_ausentes", "data": data},
        }

    revenue_column = _find_column(df.columns, ["faturamento", "receita", "valor", "vendas"])
    product_column = _find_column(df.columns, ["produto", "item"])
    category_column = _find_column(df.columns, ["categoria", "segmento"])
    date_column = _find_column(df.columns, ["data", "date", "mes"])
    region_column = _find_column(df.columns, ["regiao", "estado", "cidade"])

    if revenue_column and date_column and ("mes" in normalized or "evolu" in normalized or "tempo" in normalized):
        return _monthly_response(dataset, date_column=date_column, value_column=revenue_column)

    if revenue_column and product_column and ("produto" in normalized or "top" in normalized):
        return _ranking_response(dataset, group_column=product_column, value_column=revenue_column, label="produto")

    if revenue_column and category_column and "categoria" in normalized:
        return _ranking_response(dataset, group_column=category_column, value_column=revenue_column, label="categoria")

    if revenue_column and region_column and ("regiao" in normalized or "estado" in normalized or "cidade" in normalized):
        return _ranking_response(dataset, group_column=region_column, value_column=revenue_column, label="regiao")

    return {
        "answer": "Ainda nao tenho uma regra para essa pergunta. Tente perguntar sobre linhas, colunas, duplicatas, valores ausentes, top produtos, categoria, regiao ou vendas por mes.",
        "calculation": None,
        "table": [],
        "chart": None,
    }


def _ranking_response(dataset: DatasetSession, group_column: str, value_column: str, label: str) -> dict:
    df = dataset.dataframe
    query = f"""
        SELECT "{group_column}" AS grupo, SUM("{value_column}") AS total
        FROM df
        GROUP BY 1
        ORDER BY total DESC
        LIMIT 5
    """
    result = duckdb.sql(query).df().round(2)
    top = result.iloc[0]
    data = result.to_dict(orient="records")
    return {
        "answer": f"O principal {label} foi {top['grupo']}, com total de {top['total']}.",
        "calculation": f"sum({value_column}) grouped by {group_column}",
        "table": data,
        "chart": {"type": "bar", "x": "grupo", "y": "total", "data": data},
    }


def _monthly_response(dataset: DatasetSession, date_column: str, value_column: str) -> dict:
    df = dataset.dataframe.copy()
    parsed_dates = pd.to_datetime(df[date_column], errors="coerce")
    df = df.assign(_mes=parsed_dates.dt.to_period("M").astype(str))
    df = df[df["_mes"].ne("NaT")]

    if df.empty:
        return {
            "answer": f"Nao consegui interpretar a coluna {date_column} como data.",
            "calculation": None,
            "table": [],
            "chart": None,
        }

    result = (
        df.groupby("_mes", as_index=False)[value_column]
        .sum()
        .rename(columns={"_mes": "mes", value_column: "total"})
        .round(2)
        .sort_values("mes")
    )
    best = result.sort_values("total", ascending=False).iloc[0]
    data = result.to_dict(orient="records")

    return {
        "answer": f"O mes com maior total foi {best['mes']}, com {best['total']}.",
        "calculation": f"sum({value_column}) grouped by month({date_column})",
        "table": data,
        "chart": {"type": "line", "x": "mes", "y": "total", "data": data},
    }


def _find_column(columns, candidates: list[str]) -> str | None:
    normalized_columns = {str(column).lower(): column for column in columns}
    for candidate in candidates:
        for normalized, original in normalized_columns.items():
            if candidate in normalized:
                return str(original)
    return None
