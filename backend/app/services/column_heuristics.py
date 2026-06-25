import math
import re
import unicodedata
from typing import Any, Iterable

DEFAULT_IDENTIFIER_TERMS = ("id", "codigo", "cod", "sku", "cpf", "cnpj", "cep", "telefone", "phone", "nf")


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
