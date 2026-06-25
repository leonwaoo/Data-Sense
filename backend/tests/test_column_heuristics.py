from app.services.column_heuristics import format_number, is_metric_noise, looks_like_identifier, normalize_text


def test_normalize_text_uses_stable_column_slug() -> None:
    assert normalize_text("Nº NF / Código") == "no_nf_codigo"
    assert normalize_text("Mês da Venda", separator=" ") == "mes da venda"


def test_identifier_and_metric_noise_detection() -> None:
    assert looks_like_identifier("Codigo Cliente")
    assert looks_like_identifier("Nº_NF")
    assert is_metric_noise("Prazo Entrega Dias", {"prazo", "dias"})
    assert not is_metric_noise("Valor Total", {"prazo", "dias"})


def test_format_number_pt_br() -> None:
    assert format_number(1234) == "1.234"
    assert format_number(1234.56) == "1.234,56"
    assert format_number(None, none_text="n/d") == "n/d"
    assert format_number(1234.56, none_text="n/d", compact_large=True) == "1.235"
