import json
import os
from typing import Any

from app.models import DatasetSession
from app.services.ai_provider_service import (
    has_real_api_key as _has_real_api_key,
    request_openrouter_json,
    resolve_ai_credentials,
    safe_ai_error_message as _safe_error_message,
)
from app.services.managerial_analysis_service import build_managerial_analysis


def build_managerial_ai_review(dataset: DatasetSession, requested_model: str | None = None) -> dict:
    analysis = build_managerial_analysis(dataset)
    evidence = _managerial_evidence_package(dataset, analysis)
    local_review = _local_managerial_review(evidence)

    credentials = resolve_ai_credentials(requested_model)
    api_key = credentials["api_key"]
    model = credentials["model"]
    provider = credentials["provider"]
    if not _has_real_api_key(api_key):
        return {
            **local_review,
            "ai_enabled": False,
            "ai_status": "not_configured",
            "model": None,
            "evidence_package": evidence,
        }

    if _managerial_ai_disabled():
        return {
            **local_review,
            "ai_enabled": True,
            "ai_status": "disabled",
            "model": model,
            "provider": provider,
            "evidence_package": evidence,
        }

    try:
        ai_payload = _request_ai_managerial_review(evidence, local_review, api_key, model)
        return _merge_ai_managerial_review(local_review, ai_payload, model, evidence, provider)
    except Exception as exc:
        return {
            **local_review,
            "ai_enabled": True,
            "ai_status": "failed",
            "ai_error": _safe_error_message(exc),
            "model": model,
            "provider": provider,
            "evidence_package": evidence,
        }


def _managerial_evidence_package(dataset: DatasetSession, analysis: dict) -> dict:
    context = analysis.get("context", {})
    root_cause = analysis.get("root_cause_analysis") or {}
    variations = analysis.get("variations") or {}

    return {
        "dataset": {
            "id": dataset.dataset_id,
            "file_name": dataset.file_name,
            "rows": int(dataset.dataframe.shape[0]),
            "columns": int(dataset.dataframe.shape[1]),
        },
        "context": {
            "domain": context.get("domain"),
            "metric_map": context.get("metric_map"),
            "time": context.get("time"),
            "dimensions": context.get("dimensions"),
        },
        "summary": analysis.get("summary", [])[:6],
        "kpis": analysis.get("kpis", [])[:8],
        "largest_movements": {
            "latest": variations.get("latest"),
            "largest_increase": variations.get("largest_increase"),
            "largest_drop": variations.get("largest_drop"),
        },
        "monthly_comparisons": analysis.get("monthly_comparisons", [])[-12:],
        "root_cause": {
            "title": root_cause.get("title"),
            "metric": root_cause.get("metric"),
            "period": root_cause.get("period"),
            "previous_period": root_cause.get("previous_period"),
            "movement": root_cause.get("movement"),
            "responsible_month": root_cause.get("responsible_month"),
            "primary_contributor": root_cause.get("primary_contributor"),
            "dimension_impact_ranking": root_cause.get("dimension_impact_ranking", [])[:8],
            "dimension_narratives": analysis.get("dimension_narratives", [])[:4],
            "concentration_alerts": root_cause.get("concentration_alerts", [])[:5],
            "supporting_metrics": root_cause.get("supporting_metrics", [])[:5],
            "confidence": root_cause.get("confidence"),
            "recommendation": root_cause.get("recommendation"),
        },
        "driver_evidence": analysis.get("driver_evidence", [])[:8],
        "alerts": analysis.get("alerts", [])[:8],
        "recommendations": analysis.get("recommendations", [])[:8],
        "limitations": (analysis.get("ai_evidence_package") or {}).get("limitations", []),
    }


def _local_managerial_review(evidence: dict) -> dict:
    root = evidence.get("root_cause") or {}
    movement = root.get("movement") or {}
    primary = root.get("primary_contributor") or {}
    domain = ((evidence.get("context") or {}).get("domain") or {}).get("label") or "Analise gerencial"
    metric = root.get("metric") or (((evidence.get("context") or {}).get("metric_map") or {}).get("primary_metric"))
    period = root.get("period") or "periodo analisado"
    direction = movement.get("direction") or "variacao"

    contributor_name = primary.get("name") or "recorte principal nao identificado"
    contributor_variation = primary.get("variation")
    confidence = root.get("confidence") or "media"

    executive_summary = (
        f"{domain}: {metric or 'a metrica principal'} teve {direction} em {period}. "
        f"O principal sinal calculado aponta para {contributor_name} como recorte de maior impacto."
    )
    likely_causes = []
    if primary:
        likely_causes.append(
            {
                "title": f"Variação concentrada em {contributor_name}",
                "detail": (
                    f"{contributor_name} respondeu pela maior parte da mudança calculada"
                    f"{f' ({contributor_variation})' if contributor_variation is not None else ''}."
                ),
                "confidence": confidence,
                "evidence": [primary.get("name"), root.get("period")],
            }
        )
    for driver in root.get("supporting_metrics", [])[:2]:
        likely_causes.append(
            {
                "title": f"Driver associado: {driver.get('column')}",
                "detail": driver.get("interpretation") or "Driver de apoio teve movimento relevante no periodo.",
                "confidence": driver.get("relationship") or confidence,
                "evidence": [str(driver.get("variation")), str(driver.get("variation_pct"))],
            }
        )

    return {
        "mode": "local_managerial_review",
        "executive_summary": executive_summary,
        "what_changed": root.get("title") or executive_summary,
        "likely_causes": likely_causes[:4],
        "managerial_impact": _managerial_impact_text(evidence),
        "recommendations": _deduplicate_strings(
            [
                root.get("recommendation"),
                *evidence.get("recommendations", []),
            ]
        )[:6],
        "investigation_questions": _investigation_questions(evidence),
        "confidence": confidence,
    }


def _request_ai_managerial_review(evidence: dict, local_review: dict, api_key: str, model: str) -> dict:
    return request_openrouter_json(
        system_prompt=(
            "Voce e uma segunda leitura gerencial do DataSense para gestores. "
            "Use apenas as evidencias calculadas pelo backend; nao invente valores, causas nem nomes. "
            "Transforme variacoes, drivers, ranking de contribuicao, alertas e limitacoes em narrativa executiva. "
            "Sempre diferencie fato calculado de causa provavel. Responda em portugues do Brasil. "
            "O JSON deve conter: executive_summary, what_changed, likely_causes, managerial_impact, "
            "recommendations, investigation_questions e confidence."
        ),
        payload={
            "evidence": evidence,
            "local_review": {
                "executive_summary": local_review["executive_summary"],
                "likely_causes": local_review["likely_causes"],
                "recommendations": local_review["recommendations"],
                "confidence": local_review["confidence"],
            },
        },
        api_key=api_key,
        model=model,
        max_tokens=1800,
    )


def _merge_ai_managerial_review(local_review: dict, ai_payload: dict, model: str, evidence: dict, provider: str = "openrouter") -> dict:
    return {
        **local_review,
        "mode": "ai_managerial_review",
        "ai_enabled": True,
        "ai_status": "completed",
        "model": model,
        "provider": provider,
        "executive_summary": str(ai_payload.get("executive_summary") or local_review["executive_summary"])[:1200],
        "what_changed": str(ai_payload.get("what_changed") or local_review["what_changed"])[:900],
        "likely_causes": _normalize_causes(ai_payload.get("likely_causes"), local_review["likely_causes"]),
        "managerial_impact": str(ai_payload.get("managerial_impact") or local_review["managerial_impact"])[:900],
        "recommendations": _deduplicate_strings(
            [
                *[str(item) for item in ai_payload.get("recommendations", []) if str(item).strip()],
                *local_review["recommendations"],
            ]
        )[:6],
        "investigation_questions": _deduplicate_strings(
            [
                *[str(item) for item in ai_payload.get("investigation_questions", []) if str(item).strip()],
                *local_review["investigation_questions"],
            ]
        )[:6],
        "confidence": str(ai_payload.get("confidence") or local_review["confidence"])[:40],
        "evidence_package": evidence,
    }


def _managerial_ai_response_schema() -> dict:
    return {
        "type": "json_schema",
        "name": "datasense_managerial_review",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "executive_summary": {"type": "string"},
                "what_changed": {"type": "string"},
                "likely_causes": {
                    "type": "array",
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "title": {"type": "string"},
                            "detail": {"type": "string"},
                            "confidence": {"type": "string"},
                            "evidence": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
                        },
                        "required": ["title", "detail", "confidence", "evidence"],
                    },
                },
                "managerial_impact": {"type": "string"},
                "recommendations": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
                "investigation_questions": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
                "confidence": {"type": "string"},
            },
            "required": [
                "executive_summary",
                "what_changed",
                "likely_causes",
                "managerial_impact",
                "recommendations",
                "investigation_questions",
                "confidence",
            ],
        },
    }


def _normalize_causes(value: Any, fallback: list[dict]) -> list[dict]:
    if not isinstance(value, list):
        return fallback[:4]
    causes = []
    for index, item in enumerate(value[:4], start=1):
        if not isinstance(item, dict):
            continue
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = [str(evidence)]
        causes.append(
            {
                "title": str(item.get("title") or f"Causa provavel {index}")[:160],
                "detail": str(item.get("detail") or "")[:700],
                "confidence": str(item.get("confidence") or "media")[:40],
                "evidence": [str(entry)[:220] for entry in evidence[:4] if str(entry).strip()],
            }
        )
    return causes or fallback[:4]


def _managerial_impact_text(evidence: dict) -> str:
    alerts = evidence.get("alerts", [])
    root = evidence.get("root_cause") or {}
    metric = root.get("metric") or "metrica principal"
    if alerts:
        return f"Impacto gerencial: {alerts[0]} Validar antes de fechar decisao sobre {metric}."
    return f"Impacto gerencial: revisar o movimento de {metric} antes de decidir reposicao, venda, compra ou ajuste operacional."


def _investigation_questions(evidence: dict) -> list[str]:
    root = evidence.get("root_cause") or {}
    contributor = (root.get("primary_contributor") or {}).get("name") or "principal recorte"
    metric = root.get("metric") or "metrica principal"
    period = root.get("period") or "periodo analisado"
    return [
        f"O que aconteceu com {contributor} em {period}?",
        f"A variacao de {metric} veio de volume, transferencia, entrada, saida ou ajuste?",
        "Existe evento operacional, comercial ou financeiro que explique o movimento?",
        "O comportamento se repete nos meses seguintes ou foi pontual?",
    ]


def _deduplicate_strings(values: list[Any]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = str(value or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _managerial_ai_disabled() -> bool:
    value = os.getenv("DATASENSE_MANAGERIAL_AI_ENABLED", "true").strip().lower()
    return value in {"0", "false", "no", "off"}
