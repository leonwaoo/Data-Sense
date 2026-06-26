import re
from functools import partial
from typing import Any

import pandas as pd

from app.services.column_heuristics import (
    looks_like_identifier,
    normalize_text as _normalize_text,
    strip_accents as _strip_accents,
)
from app.services.date_utils import MONTH_ALIASES, parse_common_dates

_looks_like_identifier = partial(looks_like_identifier, terms=("id", "codigo", "cod", "sku", "nf"))

DOMAIN_RULES = [
    {
        "type": "estoque_operacao",
        "label": "Estoque e operacao",
        "terms": ["estoque", "inventario", "volume", "industrializado", "producao", "fabrica", "ton", "sku", "produto", "custo"],
        "primary_metrics": ["estoque_total", "estoque", "saldo_estoque", "inventario", "stock"],
        "support_groups": {
            "estoque_fabrica": ["estoque_fabrica", "fabrica", "warehouse", "factory_stock"],
            "volume_operacional": ["volume", "industrializado", "producao", "quantidade", "qtd"],
            "custo": ["custo", "cost", "preco", "price"],
        },
        "dimensions": ["produto", "sku", "categoria", "fy_gaap", "gaap", "fabrica", "local", "familia"],
    },
    {
        "type": "vendas",
        "label": "Vendas e receita",
        "terms": ["venda", "receita", "faturamento", "cliente", "produto", "canal", "valor_total"],
        "primary_metrics": ["valor_total", "receita", "faturamento", "valor_venda", "venda", "sales", "revenue"],
        "support_groups": {
            "quantidade": ["quantidade", "qtd", "volume", "unidade"],
            "volume_vendido": ["volume_vendido", "volume", "vendido", "ton", "kg"],
            "qtd_pedidos": ["qtd_pedidos", "pedidos", "pedido"],
            "desconto": ["desconto", "abatimento"],
            "devolucoes": ["devolucao", "devolucoes", "retorno", "cancelamento"],
            "oee": ["oee", "eficiencia"],
            "taxa_aprovacao": ["taxa_aprovacao", "aprovacao", "aprovado"],
            "margem_ebitda": ["margem_ebitda", "ebitda", "margem"],
            "custo": ["custo", "cost"],
        },
        "dimensions": ["produto", "cliente", "categoria", "canal", "regiao", "vendedor"],
    },
    {
        "type": "compras",
        "label": "Compras e fornecedores",
        "terms": ["compra", "fornecedor", "custo", "despesa", "pedido", "prazo"],
        "primary_metrics": ["valor_compra", "compra", "custo", "despesa", "gasto", "valor_total"],
        "support_groups": {
            "quantidade": ["quantidade", "qtd", "volume", "unidade"],
            "prazo": ["prazo", "lead_time", "dias"],
        },
        "dimensions": ["fornecedor", "item", "produto", "categoria", "comprador", "status"],
    },
    {
        "type": "financeiro",
        "label": "Financeiro",
        "terms": ["receita", "despesa", "custo", "lucro", "margem", "saldo", "valor"],
        "primary_metrics": ["receita", "despesa", "custo", "lucro", "saldo", "valor_total", "valor"],
        "support_groups": {
            "margem": ["margem", "margin"],
            "quantidade": ["quantidade", "qtd", "volume"],
        },
        "dimensions": ["categoria", "centro_custo", "conta", "cliente", "fornecedor"],
    },
]

YEAR_TERMS = ["ano", "year", "exercicio", "fiscal", "fy", "gaap"]
MONTH_TERMS = ["mes", "month", "competencia"]


def detect_analysis_domain(column_names: list[str]) -> dict:
    normalized = [_normalize_text(column) for column in column_names]
    scores = []
    for rule in DOMAIN_RULES:
        hits = sorted({term for term in rule["terms"] for column in normalized if term in column})
        metric_hits = sorted({term for term in rule["primary_metrics"] for column in normalized if term in column})
        score = len(hits) + len(metric_hits) * 2
        scores.append((score, rule, hits[:6], metric_hits[:4]))

    score, rule, hits, metric_hits = max(scores, key=lambda item: item[0])
    if score <= 1:
        return {
            "type": "generico",
            "label": "Analise gerencial generica",
            "confidence": 0.35,
            "reasons": ["Nao foram encontrados sinais suficientes para classificar um dominio especifico."],
        }

    confidence = min(0.96, 0.42 + score * 0.07)
    reasons = []
    if hits:
        reasons.append(f"Sinais de dominio: {', '.join(hits)}")
    if metric_hits:
        reasons.append(f"Metricas reconhecidas: {', '.join(metric_hits)}")
    return {
        "type": rule["type"],
        "label": rule["label"],
        "confidence": round(confidence, 2),
        "reasons": reasons,
    }


def map_metrics(df: pd.DataFrame, profile: dict, domain: dict) -> dict:
    numeric_columns = profile["numeric_columns"]
    rule = domain_rule(domain["type"])
    primary_metric = first_scored_column(numeric_columns, rule.get("primary_metrics", []), df)
    if not primary_metric and numeric_columns:
        primary_metric = first_business_numeric(numeric_columns, df)

    support_metrics: dict[str, str] = {}
    for group_name, terms in rule.get("support_groups", {}).items():
        column = first_scored_column(numeric_columns, terms, df, exclude={primary_metric})
        if column:
            support_metrics[group_name] = column

    return {
        "primary_metric": primary_metric,
        "support_metrics": support_metrics,
        "mapped_columns": {
            "primary_metric": primary_metric,
            **support_metrics,
        },
    }


def build_time_context(df: pd.DataFrame, profile: dict) -> dict:
    year_column = first_matching(profile["column_names"], YEAR_TERMS)
    month_column = first_matching([column for column in profile["column_names"] if column != year_column], MONTH_TERMS)
    if month_column and not year_column:
        year_column = infer_year_column(df, profile["column_names"], exclude={month_column})
    if year_column and month_column:
        parsed = parse_year_month(df[year_column], df[month_column])
        if parsed.notna().mean() >= 0.6:
            return {
                "available": True,
                "label": f"{year_column} + {month_column}",
                "columns": [year_column, month_column],
                "series": parsed,
            }

    for column in profile["datetime_columns"]:
        parsed = parse_common_dates(df[column])
        if parsed.notna().mean() >= 0.6 and not looks_like_month_without_year(column, parsed):
            return {"available": True, "label": column, "columns": [column], "series": parsed}

    for candidate in profile.get("date_candidates", []):
        column = candidate.get("column")
        if column in df.columns:
            parsed = parse_common_dates(df[column])
            if parsed.notna().mean() >= 0.6 and not looks_like_month_without_year(column, parsed):
                return {"available": True, "label": column, "columns": [column], "series": parsed}

    return {"available": False, "label": None, "columns": [], "series": pd.Series(pd.NaT, index=df.index)}


def parse_year_month(year_series: pd.Series, month_series: pd.Series) -> pd.Series:
    years = year_series.map(year_number)
    months = month_series.map(month_number)
    return pd.to_datetime(
        pd.DataFrame({"year": years, "month": months, "day": 1}),
        errors="coerce",
    )


def infer_year_column(df: pd.DataFrame, columns: list[str], exclude: set[str] | None = None) -> str | None:
    exclude = exclude or set()
    scored: list[tuple[float, int, str]] = []
    for column in columns:
        if column in exclude or column not in df.columns:
            continue
        years = df[column].map(year_number)
        ratio = float(years.notna().mean()) if len(years) else 0.0
        if ratio < 0.6:
            continue
        name_bonus = 1 if any(term in _normalize_text(column) for term in YEAR_TERMS) else 0
        scored.append((ratio, name_bonus, column))

    scored.sort(reverse=True)
    return scored[0][2] if scored else None


def year_number(value: Any) -> float | None:
    if pd.isna(value):
        return None

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 1900 <= int(value) <= 2200:
            return int(value)

    text = _strip_accents(str(value)).lower().strip()
    match = re.search(r"(19|20|21|22)\d{2}", text)
    if match:
        return int(match.group(0))

    fiscal_match = re.search(r"(?:fy|exercicio|ano)?\s*'?(\d{2})\b", text)
    if fiscal_match and any(term in text for term in ["fy", "fiscal", "gaap"]):
        year = int(fiscal_match.group(1))
        return 2000 + year if year < 70 else 1900 + year

    return None


def looks_like_month_without_year(column: str, parsed: pd.Series) -> bool:
    normalized = _normalize_text(column)
    if not any(term in normalized for term in MONTH_TERMS):
        return False

    years = parsed.dropna().dt.year
    return not years.empty and years.nunique() == 1 and int(years.iloc[0]) == 2000


def month_number(value: Any) -> float | None:
    if pd.isna(value):
        return None

    text = _strip_accents(str(value)).lower().strip()
    numeric_match = re.search(r"\d{1,2}", text)
    if numeric_match:
        number = int(numeric_match.group(0))
        if 1 <= number <= 12:
            return number

    text_match = re.search(r"[a-z]{3,}", text)
    if text_match:
        return MONTH_ALIASES.get(text_match.group(0)[:3])
    return None


def select_dimensions(profile: dict, domain: dict) -> list[dict]:
    rule = domain_rule(domain["type"])
    column_names = profile["column_names"]
    metric_like_columns = set(profile.get("numeric_columns", [])) | set(profile.get("datetime_columns", []))
    dimensions = []
    used = set()
    for term in rule.get("dimensions", []):
        column = first_matching(column_names, [term])
        if column and column not in used and column not in metric_like_columns:
            dimensions.append({"label": column, "column": column})
            used.add(column)
    return dimensions[:4]


def domain_rule(domain_type: str) -> dict:
    for rule in DOMAIN_RULES:
        if rule["type"] == domain_type:
            return rule
    return {
        "type": "generico",
        "label": "Generico",
        "terms": [],
        "primary_metrics": ["valor_total", "valor", "total", "quantidade", "qtd", "volume"],
        "support_groups": {},
        "dimensions": ["produto", "categoria", "cliente", "fornecedor", "status"],
    }


def first_scored_column(
    columns: list[str],
    terms: list[str],
    df: pd.DataFrame,
    exclude: set[str | None] | None = None,
) -> str | None:
    exclude = exclude or set()
    scored = []
    for column in columns:
        if column in exclude:
            continue
        normalized = _normalize_text(column)
        score = sum(100 - index * 4 for index, term in enumerate(terms) if term in normalized)
        if _looks_like_identifier(column):
            score -= 500
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            score -= 200
        if score > 0:
            scored.append((score, column))
    scored.sort(reverse=True)
    return scored[0][1] if scored else None


def first_business_numeric(columns: list[str], df: pd.DataFrame) -> str | None:
    candidates = [column for column in columns if not _looks_like_identifier(column)]
    candidates = candidates or columns
    if not candidates:
        return None
    return max(candidates, key=lambda column: pd.to_numeric(df[column], errors="coerce").abs().sum(skipna=True))


def first_matching(columns: list[str], terms: list[str]) -> str | None:
    for term in terms:
        for column in columns:
            if term in _normalize_text(column):
                return column
    return None
