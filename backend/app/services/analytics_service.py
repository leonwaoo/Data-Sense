import re
import unicodedata

import duckdb
import pandas as pd

from app.models import DatasetSession
from app.services.date_utils import parse_common_dates

SALES_CANDIDATES = [
    "valor_total",
    "total_venda",
    "valor_liquido",
    "valor_bruto",
    "faturamento",
    "receita",
    "receita_bruta",
    "receita_liquida",
    "venda",
    "vendas",
    "valor_venda",
    "sales",
    "revenue",
]
PURCHASE_CANDIDATES = ["compra", "compras", "valor_compra", "custo", "custos", "despesa", "gasto", "purchase", "cost"]
QUANTITY_CANDIDATES = ["quantidade", "qtd", "volume", "unidade", "unidades", "units"]
VALUE_CANDIDATES = SALES_CANDIDATES + PURCHASE_CANDIDATES + [
    "valor",
    "total",
    "preco",
    "preco_unitario",
    "amount",
    "price",
    "lucro",
    "margem",
]
METRIC_NOISE_TERMS = [
    "id",
    "codigo",
    "cod",
    "nf",
    "nota_fiscal",
    "numero",
    "prazo",
    "dias",
    "avaliacao",
    "rating",
    "mes",
    "ano",
    "trim",
    "trimestre",
    "percentual",
    "taxa",
]
NEGATIVE_METRIC_TERMS = ["desconto", "devolucao", "estorno", "cancelamento", "ajuste", "abatimento"]
NEGATIVE_ALLOWED_TERMS = ["lucro", "margem", "saldo"]
DATE_CANDIDATES = ["data", "date", "mes", "month", "dia", "periodo", "competencia"]
GROUP_CANDIDATES = [
    ("produto", ["produto", "item", "sku", "servico", "produto_servico"]),
    ("fornecedor", ["fornecedor", "supplier", "vendor"]),
    ("cliente", ["cliente", "customer", "comprador"]),
    ("categoria", ["categoria", "segmento", "tipo", "classe", "familia"]),
    ("regiao", ["regiao", "estado", "cidade", "uf", "pais", "local"]),
    ("canal", ["canal", "origem", "midia", "loja", "vendedor"]),
    ("status", ["status", "situacao", "etapa"]),
]


def answer_question(dataset: DatasetSession, question: str) -> dict:
    normalized = _normalize_text(question)
    df = dataset.dataframe

    if any(term in normalized for term in ["linhas", "linha", "colunas", "coluna", "tamanho"]):
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

    if "ausente" in normalized or "nulo" in normalized or "vazio" in normalized:
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

    metric_column = _select_metric_column(df, normalized)
    date_column = _find_column(df.columns, DATE_CANDIDATES)
    group_column, group_label = _select_group_column(df, normalized)
    ascending = any(term in normalized for term in ["menor", "piores", "baixo", "menores"])

    if metric_column and date_column and _asks_for_time(normalized):
        return _monthly_response(dataset, date_column=date_column, value_column=metric_column)

    if metric_column and group_column and _asks_for_breakdown(normalized):
        return _ranking_response(
            dataset,
            group_column=group_column,
            value_column=metric_column,
            label=group_label,
            ascending=ascending,
        )

    if metric_column and any(term in normalized for term in ["media", "medio", "average"]):
        return _single_metric_response(dataset, value_column=metric_column, operation="media")

    if metric_column and any(term in normalized for term in ["total", "soma", "somar", "quanto"]):
        return _single_metric_response(dataset, value_column=metric_column, operation="total")

    if group_column:
        return _count_by_group_response(dataset, group_column=group_column, label=group_label, ascending=ascending)

    return {
        "answer": "Ainda nao tenho uma regra para essa pergunta. Tente perguntar sobre linhas, colunas, duplicatas, valores ausentes, total de vendas/compras, top produtos, fornecedores, clientes, categorias, regioes ou evolucao por mes.",
        "calculation": None,
        "table": [],
        "chart": None,
    }


def _ranking_response(dataset: DatasetSession, group_column: str, value_column: str, label: str, ascending: bool = False) -> dict:
    df = dataset.dataframe
    direction = "ASC" if ascending else "DESC"
    query = f"""
        SELECT CAST({_quote_identifier(group_column)} AS VARCHAR) AS grupo, SUM({_quote_identifier(value_column)}) AS total
        FROM df
        WHERE {_quote_identifier(group_column)} IS NOT NULL
          AND {_quote_identifier(value_column)} IS NOT NULL
        GROUP BY 1
        ORDER BY total {direction}
        LIMIT 5
    """
    result = duckdb.sql(query).df().round(2)
    if result.empty:
        return _empty_answer(f"Nao encontrei dados suficientes para cruzar {label} com {value_column}.")

    top = result.iloc[0]
    data = result.to_dict(orient="records")
    direction_label = "menor" if ascending else "principal"
    return {
        "answer": f"O {direction_label} {label} foi {top['grupo']}, com total de {top['total']}.",
        "calculation": f"sum({value_column}) grouped by {group_column}",
        "table": data,
        "chart": {"type": "bar", "x": "grupo", "y": "total", "data": data},
    }


def _monthly_response(dataset: DatasetSession, date_column: str, value_column: str) -> dict:
    df = dataset.dataframe.copy()
    parsed_dates = parse_common_dates(df[date_column])
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


def _single_metric_response(dataset: DatasetSession, value_column: str, operation: str) -> dict:
    series = pd.to_numeric(dataset.dataframe[value_column], errors="coerce").dropna()
    if series.empty:
        return _empty_answer(f"Nao encontrei valores numericos na coluna {value_column}.")

    if operation == "media":
        value = round(float(series.mean()), 2)
        return {
            "answer": f"A media de {value_column} e {value}.",
            "calculation": f"mean({value_column})",
            "table": [{"metrica": value_column, "media": value}],
            "chart": None,
        }

    value = round(float(series.sum()), 2)
    return {
        "answer": f"O total de {value_column} e {value}.",
        "calculation": f"sum({value_column})",
        "table": [{"metrica": value_column, "total": value}],
        "chart": None,
    }


def _count_by_group_response(dataset: DatasetSession, group_column: str, label: str, ascending: bool = False) -> dict:
    df = dataset.dataframe
    direction = "ASC" if ascending else "DESC"
    query = f"""
        SELECT CAST({_quote_identifier(group_column)} AS VARCHAR) AS grupo, COUNT(*) AS registros
        FROM df
        WHERE {_quote_identifier(group_column)} IS NOT NULL
        GROUP BY 1
        ORDER BY registros {direction}
        LIMIT 5
    """
    result = duckdb.sql(query).df()
    if result.empty:
        return _empty_answer(f"Nao encontrei registros agrupaveis por {label}.")

    top = result.iloc[0]
    data = result.to_dict(orient="records")
    direction_label = "menos" if ascending else "mais"
    return {
        "answer": f"O {label} com {direction_label} registros foi {top['grupo']}, com {int(top['registros'])} linhas.",
        "calculation": f"count(*) grouped by {group_column}",
        "table": data,
        "chart": {"type": "bar", "x": "grupo", "y": "registros", "data": data},
    }


def _select_metric_column(df: pd.DataFrame, normalized_question: str) -> str | None:
    numeric_columns = [str(column) for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]
    if not numeric_columns:
        return None

    for column in numeric_columns:
        normalized_column = _normalize_text(column)
        if normalized_column and normalized_column in normalized_question:
            return column

    if any(term in normalized_question for term in ["compra", "compras", "fornecedor", "custo", "despesa", "gasto"]):
        return _best_metric_column(df, numeric_columns, PURCHASE_CANDIDATES, domain="compras")

    if any(term in normalized_question for term in ["venda", "vendas", "receita", "faturamento", "cliente"]):
        return _best_metric_column(df, numeric_columns, SALES_CANDIDATES, domain="vendas")

    if any(term in normalized_question for term in ["quantidade", "qtd", "volume", "unidade"]):
        return _best_metric_column(df, numeric_columns, QUANTITY_CANDIDATES, domain="quantidade")

    return _best_metric_column(df, numeric_columns, VALUE_CANDIDATES, domain="generico")


def _best_metric_column(df: pd.DataFrame, numeric_columns: list[str], candidates: list[str], domain: str) -> str | None:
    scored_columns = [(_metric_score(df, column, candidates, domain), column) for column in numeric_columns]
    scored_columns.sort(reverse=True)
    if scored_columns and scored_columns[0][0] > 0:
        return scored_columns[0][1]

    filtered = [
        column
        for column in numeric_columns
        if not _looks_like_identifier(column) and not _is_metric_noise(column) and not _is_adjustment_metric(column)
    ]
    return (filtered or numeric_columns)[0] if numeric_columns else None


def _metric_score(df: pd.DataFrame, column: str, candidates: list[str], domain: str) -> float:
    normalized = _normalize_text(column).replace(" ", "_")
    if _looks_like_identifier(column) or _is_metric_noise(column):
        return -1000

    score = 0.0
    for index, candidate in enumerate(candidates):
        if candidate in normalized:
            score += max(18, 110 - index * 5)
    for index, candidate in enumerate(VALUE_CANDIDATES):
        if candidate in normalized:
            score += max(10, 70 - index * 3)

    if _is_adjustment_metric(column):
        score -= 220
    if domain == "vendas" and any(term in normalized for term in ["compra", "custo", "despesa", "gasto"]):
        score -= 70
    if domain == "compras" and any(term in normalized for term in ["receita", "faturamento", "venda"]):
        score -= 50

    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return -1000
    negative_ratio = float((series < 0).sum() / len(series))
    if negative_ratio > 0 and not any(term in normalized for term in NEGATIVE_ALLOWED_TERMS):
        score -= 160 * negative_ratio
    if negative_ratio >= 0.35 and not any(term in normalized for term in NEGATIVE_ALLOWED_TERMS):
        score -= 120

    return score


def _select_group_column(df: pd.DataFrame, normalized_question: str) -> tuple[str | None, str]:
    columns = [str(column) for column in df.columns]

    for label, candidates in GROUP_CANDIDATES:
        if any(candidate in normalized_question for candidate in candidates + [label]):
            column = _find_column(columns, candidates)
            if column:
                return column, label

    if _asks_for_breakdown(normalized_question):
        for label, candidates in GROUP_CANDIDATES:
            column = _find_column(columns, candidates)
            if column:
                return column, label

    return None, "grupo"


def _asks_for_time(normalized_question: str) -> bool:
    return any(term in normalized_question for term in ["mes", "meses", "tempo", "evolu", "data", "periodo", "tendencia"])


def _asks_for_breakdown(normalized_question: str) -> bool:
    return any(term in normalized_question for term in ["top", "ranking", "maior", "menor", "por", "grupo", "categoria", "regiao", "produto", "cliente", "fornecedor", "canal", "status"])


def _find_column(columns, candidates: list[str]) -> str | None:
    normalized_columns = {_normalize_text(str(column)): column for column in columns}
    for candidate in candidates:
        for normalized, original in normalized_columns.items():
            if candidate in normalized:
                return str(original)
    return None


def _looks_like_identifier(column: str) -> bool:
    normalized = _normalize_text(column).replace(" ", "_")
    identifier_terms = ("id", "codigo", "cod", "sku", "cpf", "cnpj", "cep", "telefone", "phone")
    return any(term == normalized or normalized.startswith(f"{term}_") or normalized.endswith(f"_{term}") for term in identifier_terms)


def _is_metric_noise(column: str) -> bool:
    normalized = _normalize_text(column).replace(" ", "_")
    return any(term == normalized or normalized.startswith(f"{term}_") or normalized.endswith(f"_{term}") for term in METRIC_NOISE_TERMS)


def _is_adjustment_metric(column: str) -> bool:
    normalized = _normalize_text(column).replace(" ", "_")
    return any(term in normalized for term in NEGATIVE_METRIC_TERMS)


def _quote_identifier(column: str) -> str:
    return f'"{column.replace(chr(34), chr(34) + chr(34))}"'


def _empty_answer(message: str) -> dict:
    return {"answer": message, "calculation": None, "table": [], "chart": None}


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-zA-Z0-9_]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()
