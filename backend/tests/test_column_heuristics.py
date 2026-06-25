import pandas as pd

from app.services.column_heuristics import (
    format_number,
    is_adjustment_metric,
    is_metric_noise,
    looks_like_identifier,
    metric_score,
    normalize_text,
)


def test_normalize_text_uses_stable_column_slug() -> None:
    assert normalize_text("Nº NF / Código") == "no_nf_codigo"
    assert normalize_text("Mês da Venda", separator=" ") == "mes da venda"


def test_identifier_and_metric_noise_detection() -> None:
    assert looks_like_identifier("Codigo Cliente")
    assert looks_like_identifier("Nº_NF")
    assert is_metric_noise("Prazo Entrega Dias", {"prazo", "dias"})
    assert not is_metric_noise("Valor Total", {"prazo", "dias"})
    assert is_adjustment_metric("Desconto Total")
    assert not is_adjustment_metric("Receita Total")


def test_format_number_pt_br() -> None:
    assert format_number(1234) == "1.234"
    assert format_number(1234.56) == "1.234,56"
    assert format_number(None, none_text="n/d") == "n/d"
    assert format_number(1234.56, none_text="n/d", compact_large=True) == "1.235"


def test_metric_score_prioritizes_business_metrics() -> None:
    df = pd.DataFrame(
        {
            "Nº_NF": [1001, 1002, 1003],
            "Receita Total": [1200, 1500, 1800],
            "Desconto": [-100, -120, -90],
        }
    )
    metric_noise_terms = {"nf", "numero"}
    value_candidates = ["receita", "valor", "desconto"]

    identifier_score = metric_score(df, "Nº_NF", "vendas", value_candidates, value_candidates, metric_noise_terms)
    revenue_score = metric_score(df, "Receita Total", "vendas", value_candidates, value_candidates, metric_noise_terms)
    discount_score = metric_score(df, "Desconto", "vendas", value_candidates, value_candidates, metric_noise_terms)

    assert identifier_score == -1000
    assert revenue_score > 0
    assert revenue_score > discount_score
