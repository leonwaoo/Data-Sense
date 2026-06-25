import math
import re
import unicodedata
from typing import Any, Iterable

import pandas as pd

DEFAULT_IDENTIFIER_TERMS = ("id", "codigo", "cod", "sku", "cpf", "cnpj", "cep", "telefone", "phone", "nf")
DEFAULT_ADJUSTMENT_METRIC_TERMS = ("desconto", "devolucao", "estorno", "cancelamento", "ajuste", "abatimento")
DEFAULT_NEGATIVE_ALLOWED_TERMS = ("lucro", "margem", "saldo")


def normalize_text(value: Any, separator: str = "_") -> str:
    text = strip_accents(str(value))
    replacement = " " if separator == " " else "_"
    text = re.sub(r"[^a-zA-Z0-9_]+", replacement, text.lower())
    collapsed = re.sub(r"\s+", " ", text) if replacement == " " else re.sub(r"_+", "_", text)
    return collapsed.strip(replacement)


def normalize_text_for_search(value: Any) -> str:
    return normalize_text(value, separator=" ")


def strip_accents(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(character for character in text if not unicodedata.combining(character))


def looks_like_identifier(column: str, terms: Iterable[str] = DEFAULT_IDENTIFIER_TERMS) -> bool:
    normalized = normalize_text(column)
    return any(_matches_term(normalized, term) for term in terms)


def is_metric_noise(column: str, terms: Iterable[str]) -> bool:
    normalized = normalize_text(column)
    return any(_matches_term(normalized, term) for term in terms)


def is_adjustment_metric(column: str, terms: Iterable[str] = DEFAULT_ADJUSTMENT_METRIC_TERMS) -> bool:
    normalized = normalize_text(column)
    return any(term in normalized for term in terms)


def metric_score(
    df: pd.DataFrame,
    column: str,
    domain: str,
    domain_candidates: Iterable[str],
    value_candidates: Iterable[str],
    metric_noise_terms: Iterable[str],
    negative_allowed_terms: Iterable[str] = DEFAULT_NEGATIVE_ALLOWED_TERMS,
    domain_base: int = 120,
    value_base: int = 80,
    zero_sum_penalty: bool = False,
) -> float:
    normalized = normalize_text(column)
    if looks_like_identifier(column) or is_metric_noise(column, metric_noise_terms):
        return -1000

    score = 0.0
    for index, candidate in enumerate(domain_candidates):
        if candidate in normalized:
            score += max(18, domain_base - index * 5)
    for index, candidate in enumerate(value_candidates):
        if candidate in normalized:
            score += max(10, value_base - index * 3)

    if is_adjustment_metric(column):
        score -= 220
    if domain == "vendas" and any(term in normalized for term in ["compra", "custo", "despesa", "gasto"]):
        score -= 70
    if domain == "compras" and any(term in normalized for term in ["receita", "faturamento", "venda"]):
        score -= 50

    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return -1000

    negative_ratio = float((series < 0).sum() / len(series))
    if negative_ratio > 0 and not any(term in normalized for term in negative_allowed_terms):
        score -= 160 * negative_ratio
    if negative_ratio >= 0.35 and not any(term in normalized for term in negative_allowed_terms):
        score -= 120
    if zero_sum_penalty and float(series.abs().sum()) == 0:
        score -= 40

    return score


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize_text(value)).strip("_")


def format_number(value: Any, none_text: str | None = None, compact_large: bool = False) -> str:
    try:
        if value is None:
            return none_text or str(value)
        parsed = float(value)
    except (TypeError, ValueError):
        return none_text or str(value)

    if not math.isfinite(parsed):
        return none_text or str(value)
    if compact_large and abs(parsed) >= 1000:
        return f"{parsed:,.0f}".replace(",", ".")
    if parsed.is_integer():
        return f"{int(parsed):,}".replace(",", ".")
    return f"{parsed:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _matches_term(normalized: str, term: str) -> bool:
    return term == normalized or normalized.startswith(f"{term}_") or normalized.endswith(f"_{term}")
