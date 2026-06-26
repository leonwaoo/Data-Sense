import pandas as pd

from app.models import DatasetSession
from app.services import ai_managerial_service
from app.services.ai_managerial_service import build_managerial_ai_review


def _inventory_dataset() -> DatasetSession:
    dataframe = pd.DataFrame(
        {
            "Ano": [2025, 2025, 2025, 2025, 2025, 2025],
            "Month": ["JAN", "JAN", "FEV", "FEV", "MAR", "MAR"],
            "Produto": ["Cafe A", "Cafe B", "Cafe A", "Cafe B", "Cafe A", "Cafe B"],
            "FY GAAP": ["FY25", "FY25", "FY25", "FY25", "FY25", "FY25"],
            "Estoque Total (TON)": [1000, 500, 900, 520, 100, 530],
            "Estoque Fabrica (TON)": [700, 300, 650, 310, 180, 320],
            "Volume Industrializado (TON)": [120, 80, 130, 90, 460, 95],
            "Custo (R$/TON)": [450, 440, 455, 442, 470, 445],
        }
    )
    return DatasetSession(dataset_id="estoque", file_name="dashboard.xlsx", dataframe=dataframe)


def test_managerial_ai_review_uses_local_review_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    review = build_managerial_ai_review(_inventory_dataset())

    assert review["ai_enabled"] is False
    assert review["ai_status"] == "not_configured"
    assert review["model"] is None
    assert "Cafe A" in review["executive_summary"]
    assert review["likely_causes"]
    assert review["evidence_package"]["root_cause"]["dimension_impact_ranking"][0]["name"] == "Cafe A"
    assert "sample_rows" not in review["evidence_package"]


def test_managerial_ai_review_merges_structured_ai_payload(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-chave-real-de-teste")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def fake_request(evidence: dict, local_review: dict, api_key: str, model: str) -> dict:
        assert evidence["root_cause"]["primary_contributor"]["name"] == "Cafe A"
        assert api_key == "sk-or-chave-real-de-teste"
        assert model == "anthropic/claude-3.5-sonnet"
        return {
            "executive_summary": "Cafe A explica a queda operacional de marco.",
            "what_changed": "Estoque caiu no mes analisado.",
            "likely_causes": [
                {
                    "title": "Consumo operacional elevado",
                    "detail": "O volume industrializado subiu enquanto o estoque caiu.",
                    "confidence": "media",
                    "evidence": ["Cafe A", "2025-03"],
                }
            ],
            "managerial_impact": "Risco de ruptura ou necessidade de validar transferencias.",
            "recommendations": ["Validar movimentos de estoque do Cafe A."],
            "investigation_questions": ["Houve transferencia de Cafe A em marco?"],
            "confidence": "media",
        }

    monkeypatch.setattr(ai_managerial_service, "_request_ai_managerial_review", fake_request)

    review = build_managerial_ai_review(_inventory_dataset(), requested_model="anthropic/claude-3.5-sonnet")

    assert review["ai_enabled"] is True
    assert review["ai_status"] == "completed"
    assert review["model"] == "anthropic/claude-3.5-sonnet"
    assert review["provider"] == "openrouter"
    assert review["mode"] == "ai_managerial_review"
    assert review["executive_summary"] == "Cafe A explica a queda operacional de marco."
    assert review["likely_causes"][0]["title"] == "Consumo operacional elevado"
