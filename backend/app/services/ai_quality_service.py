import json
import math
import os
import re
import unicodedata
import urllib.error
import urllib.request
from collections.abc import Iterable
from typing import Any

import pandas as pd

from app.models import DatasetSession
from app.services.dashboard_service import build_dashboard
from app.services.profile_service import build_profile
from app.services.quality_service import build_quality_report

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

METRIC_NOISE_TERMS = {
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
}
BUSINESS_VALUE_TERMS = {
    "valor",
    "valor_total",
    "total",
    "receita",
    "faturamento",
    "venda",
    "vendas",
    "compra",
    "compras",
    "custo",
    "despesa",
    "gasto",
    "preco",
    "lucro",
    "margem",
}
NEGATIVE_ALLOWED_TERMS = {"desconto", "devolucao", "estorno", "cancelamento", "saldo", "lucro", "margem"}
DATE_DOMAIN_TYPES = {"vendas", "compras", "clientes", "financeiro"}
SEVERITY_PENALTIES = {"critical": 18, "warning": 9, "info": 3}


def build_quality_audit(dataset: DatasetSession) -> dict:
    profile = build_profile(dataset)
    quality = build_quality_report(dataset)
    dashboard = build_dashboard(dataset)
    evidence = _build_evidence(dataset, profile, quality, dashboard)
    rule_audit = _build_rule_audit(evidence)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    if not api_key:
        return {
            **rule_audit,
            "ai_enabled": False,
            "ai_status": "not_configured",
            "model": None,
        }

    if _ai_audit_disabled():
        return {
            **rule_audit,
            "ai_enabled": True,
            "ai_status": "disabled",
            "model": model,
        }

    try:
        ai_payload = _request_ai_audit(evidence, rule_audit, api_key, model)
        return _merge_ai_audit(rule_audit, ai_payload, model)
    except Exception as exc:
        return {
            **rule_audit,
            "ai_enabled": True,
            "ai_status": "failed",
            "ai_error": _safe_error_message(exc),
            "model": model,
        }


def _build_evidence(dataset: DatasetSession, profile: dict, quality: dict, dashboard: dict) -> dict:
    df = dataset.dataframe
    total_cells = max(df.shape[0] * df.shape[1], 1)
    duplicate_rate = quality["duplicate_rows"] / max(df.shape[0], 1)
    missing_rate = quality["missing_total"] / total_cells
    dashboard_metrics = _extract_dashboard_metrics(dashboard)
    generic_columns = [column for column in profile["column_names"] if _is_generic_column(column)]
    numeric_stats = _numeric_stats(df, profile["numeric_columns"])
    dashboard_domain = dashboard.get("domain", {})

    return {
        "dataset": {
            "id": dataset.dataset_id,
            "file_name": dataset.file_name,
            "rows": profile["rows"],
            "columns": profile["columns"],
            "ingest_report": profile.get("ingest_report", {}),
        },
        "profile": {
            "column_names": profile["column_names"],
            "column_types": profile.get("column_types", {}),
            "numeric_columns": profile["numeric_columns"],
            "categorical_columns": profile["categorical_columns"],
            "datetime_columns": profile["datetime_columns"],
            "date_conversion_suggestions": profile.get("date_conversion_suggestions", []),
        },
        "quality": {
            "score": quality["score"],
            "missing_total": quality["missing_total"],
            "missing_rate": round(missing_rate, 4),
            "missing_by_column": quality["missing_by_column"],
            "duplicate_rows": quality["duplicate_rows"],
            "duplicate_rate": round(duplicate_rate, 4),
            "empty_columns": quality["empty_columns"],
            "numeric_outliers": quality.get("numeric_outliers", {}),
            "numeric_outlier_details": quality.get("numeric_outlier_details", []),
            "score_breakdown": quality.get("score_breakdown", []),
        },
        "dashboard": {
            "domain": dashboard_domain,
            "subtitle": dashboard.get("subtitle"),
            "metrics_used": dashboard_metrics,
            "charts": _dashboard_chart_evidence(dashboard),
        },
        "checks": {
            "generic_columns": generic_columns,
            "generic_column_rate": round(len(generic_columns) / max(profile["columns"], 1), 4),
            "possible_header_row": _possible_header_row(df, generic_columns),
            "business_value_candidates": _business_value_candidates(profile["numeric_columns"]),
            "metric_stats": {metric: numeric_stats.get(metric) for metric in dashboard_metrics if metric in numeric_stats},
            "numeric_stats": numeric_stats,
            "id_like_numeric_columns": [column for column in profile["numeric_columns"] if _looks_like_identifier(column)],
            "sample_values": _sample_values_by_column(df),
            "sample_rows": _safe_records(df.head(8)),
            "ingest_warnings": profile.get("ingest_report", {}).get("warnings", []),
        },
    }


def _build_rule_audit(evidence: dict) -> dict:
    findings: list[dict] = []
    _check_generic_columns(evidence, findings)
    _check_date_detection(evidence, findings)
    _check_dashboard_metrics(evidence, findings)
    _check_missing_values(evidence, findings)
    _check_duplicates(evidence, findings)
    _check_outliers(evidence, findings)
    _check_numeric_identifiers(evidence, findings)
    _check_ingest_warnings(evidence, findings)

    if not findings:
        findings.append(
            _finding(
                "dataset_consistente",
                "info",
                "confiabilidade",
                "Auditoria inicial sem bloqueios",
                "As regras locais nao encontraram sinais fortes de cabecalho errado, metrica suspeita, nulos, duplicatas ou datas mal reconhecidas.",
                "Seguir com a analise e validar os principais resultados com amostras do arquivo original.",
                ["Score de qualidade sem penalidades relevantes."],
            )
        )

    score = _analysis_score(evidence["quality"]["score"], findings)
    return {
        "mode": "rules",
        "analysis_score": score,
        "summary": _audit_summary(score, findings),
        "findings": findings[:8],
        "recommendations": _recommendations_from_findings(findings),
        "checks": {
            "quality_score": evidence["quality"]["score"],
            "missing_rate": evidence["quality"]["missing_rate"],
            "duplicate_rate": evidence["quality"]["duplicate_rate"],
            "generic_columns": evidence["checks"]["generic_columns"],
            "metrics_used": evidence["dashboard"]["metrics_used"],
            "date_conversion_suggestions": len(evidence["profile"]["date_conversion_suggestions"]),
        },
    }


def _check_generic_columns(evidence: dict, findings: list[dict]) -> None:
    generic_columns = evidence["checks"]["generic_columns"]
    if not generic_columns:
        return

    possible_header = evidence["checks"]["possible_header_row"]
    severity = "critical" if evidence["checks"]["generic_column_rate"] >= 0.2 or possible_header else "warning"
    detail = f"{len(generic_columns)} coluna(s) ainda parecem nomes genericos, como coluna_N ou Unnamed."
    if possible_header:
        detail += " A primeira linha dos dados tambem parece conter nomes reais de colunas."

    evidence_lines = [f"Colunas genericas: {', '.join(generic_columns[:8])}"]
    if possible_header:
        evidence_lines.append(f"Possivel cabecalho na primeira linha: {', '.join(possible_header[:8])}")

    findings.append(
        _finding(
            "cabecalho_generico",
            severity,
            "cabecalho",
            "Cabecalho pode ter sido lido de forma incorreta",
            detail,
            "Reprocessar a planilha usando a linha real de cabecalho antes de confiar nos rankings e somas.",
            evidence_lines,
        )
    )


def _check_date_detection(evidence: dict, findings: list[dict]) -> None:
    datetime_columns = evidence["profile"]["datetime_columns"]
    suggestions = evidence["profile"]["date_conversion_suggestions"]
    domain = evidence["dashboard"]["domain"].get("type")

    if suggestions:
        suggested_columns = [suggestion["column"] for suggestion in suggestions[:6]]
        severity = "warning" if not datetime_columns else "info"
        findings.append(
            _finding(
                "datas_como_texto",
                severity,
                "datas",
                "Colunas de periodo podem estar como texto",
                f"Foram encontradas {len(suggestions)} coluna(s) com formato de mes, trimestre ou competencia que ainda nao entraram como data real.",
                "Oferecer conversao para periodo mensal/trimestral e recalcular tendencias com essas colunas quando fizer sentido.",
                [f"Sugestoes: {', '.join(suggested_columns)}"],
            )
        )

    if not datetime_columns and domain in DATE_DOMAIN_TYPES:
        findings.append(
            _finding(
                "sem_data_detectada",
                "warning",
                "datas",
                "Nenhuma coluna de data foi usada na analise temporal",
                "O dominio detectado normalmente precisa de periodo para evolucao, sazonalidade ou comparacao mensal.",
                "Pedir ao usuario para confirmar qual coluna representa data, mes, trimestre ou competencia.",
                [f"Dominio detectado: {evidence['dashboard']['domain'].get('label', 'nao informado')}"],
            )
        )


def _check_dashboard_metrics(evidence: dict, findings: list[dict]) -> None:
    metrics = evidence["dashboard"]["metrics_used"]
    candidates = evidence["checks"]["business_value_candidates"]
    domain = evidence["dashboard"]["domain"].get("type")

    if not metrics and evidence["profile"]["numeric_columns"]:
        findings.append(
            _finding(
                "sem_metrica_principal",
                "warning",
                "metricas",
                "Dashboard sem metrica principal clara",
                "Existem colunas numericas, mas nenhuma metrica principal apareceu nos graficos de negocio.",
                "Confirmar qual coluna representa valor, receita, compra, custo ou quantidade antes de montar conclusoes.",
                [f"Numericas disponiveis: {', '.join(evidence['profile']['numeric_columns'][:8])}"],
            )
        )
        return

    suspicious_metrics = [metric for metric in metrics if _is_metric_noise(metric)]
    if suspicious_metrics:
        findings.append(
            _finding(
                "metrica_ruido",
                "critical",
                "metricas",
                "Metrica principal parece ser coluna de controle",
                "Uma coluna usada nos graficos tem nome tipico de NF, prazo, avaliacao, identificador ou percentual, o que pode distorcer os totais.",
                "Trocar a metrica do dashboard para uma coluna de valor de negocio antes de exportar relatorios.",
                [f"Metricas suspeitas: {', '.join(suspicious_metrics)}"],
            )
        )

    if metrics and candidates and not any(metric in candidates for metric in metrics):
        findings.append(
            _finding(
                "metrica_nao_priorizada",
                "warning",
                "metricas",
                "Existe coluna de valor melhor que a metrica usada",
                "O dataset possui colunas com nome de receita, venda, compra, custo ou valor total que deveriam ser priorizadas.",
                "Revisar a escolha da metrica principal e preferir a coluna de valor mais aderente ao dominio do dataset.",
                [
                    f"Metricas usadas: {', '.join(metrics)}",
                    f"Candidatas de negocio: {', '.join(candidates[:8])}",
                ],
            )
        )

    for metric, stats in evidence["checks"]["metric_stats"].items():
        if not stats:
            continue

        normalized = _normalize_text(metric)
        negative_allowed = any(term in normalized for term in NEGATIVE_ALLOWED_TERMS)
        if stats["sum"] < 0 and not negative_allowed:
            findings.append(
                _finding(
                    f"total_negativo_{_slug(metric)}",
                    "critical" if domain in {"vendas", "compras", "clientes"} else "warning",
                    "metricas",
                    "Total negativo em metrica principal",
                    f"A soma de {metric} ficou negativa, o que costuma ser estranho para vendas, compras ou receita bruta.",
                    "Verificar se a coluna correta foi escolhida, se descontos/devolucoes foram misturados ou se houve erro de parsing numerico.",
                    [f"Soma: {_format_number(stats['sum'])}", f"Valores negativos: {stats['negative_rate']:.1%}"],
                )
            )
        elif stats["negative_rate"] > 0.05 and not negative_allowed:
            findings.append(
                _finding(
                    f"negativos_{_slug(metric)}",
                    "warning",
                    "metricas",
                    "Metrica principal possui valores negativos",
                    f"{stats['negative_rate']:.1%} dos valores de {metric} sao negativos.",
                    "Separar descontos, devolucoes ou ajustes em colunas proprias antes de somar a metrica principal.",
                    [f"Minimo: {_format_number(stats['min'])}", f"Maximo: {_format_number(stats['max'])}"],
                )
            )


def _check_missing_values(evidence: dict, findings: list[dict]) -> None:
    missing_rate = evidence["quality"]["missing_rate"]
    if missing_rate <= 0:
        return

    missing_by_column = evidence["quality"]["missing_by_column"]
    rows = max(evidence["dataset"]["rows"], 1)
    worst_columns = [
        (column, count / rows)
        for column, count in missing_by_column.items()
        if count > 0
    ]
    worst_columns.sort(key=lambda item: item[1], reverse=True)

    if missing_rate >= 0.25:
        severity = "critical"
    elif missing_rate >= 0.08 or any(rate >= 0.35 for _, rate in worst_columns):
        severity = "warning"
    else:
        severity = "info"

    findings.append(
        _finding(
            "valores_ausentes",
            severity,
            "qualidade",
            "Valores ausentes podem afetar conclusoes",
            f"O dataset possui {evidence['quality']['missing_total']} valor(es) ausente(s), equivalentes a {missing_rate:.1%} das celulas.",
            "Priorizar tratamento das colunas mais vazias antes de comparar totais, medias ou rankings.",
            [f"{column}: {rate:.1%} vazio" for column, rate in worst_columns[:5]],
        )
    )


def _check_duplicates(evidence: dict, findings: list[dict]) -> None:
    duplicate_rows = evidence["quality"]["duplicate_rows"]
    duplicate_rate = evidence["quality"]["duplicate_rate"]
    if not duplicate_rows:
        return

    severity = "critical" if duplicate_rate >= 0.1 else "warning"
    findings.append(
        _finding(
            "linhas_duplicadas",
            severity,
            "qualidade",
            "Linhas duplicadas podem inflar totais",
            f"Foram encontradas {duplicate_rows} linha(s) duplicada(s), equivalentes a {duplicate_rate:.1%} dos registros.",
            "Remover ou justificar duplicatas antes de calcular vendas, compras, receita ou contagens.",
            [f"Duplicatas: {duplicate_rows}"],
        )
    )


def _check_outliers(evidence: dict, findings: list[dict]) -> None:
    outliers = evidence["quality"].get("numeric_outliers", {})
    if not outliers:
        return

    details = evidence["quality"].get("numeric_outlier_details", [])
    rows = max(evidence["dataset"]["rows"], 1)
    worst = sorted(outliers.items(), key=lambda item: item[1], reverse=True)
    worst_rate = worst[0][1] / rows
    severity = "warning" if worst_rate >= 0.08 else "info"
    evidence_lines = [
        f"{column}: {count} outlier(s)"
        for column, count in worst[:5]
    ]
    if details:
        evidence_lines = [
            f"{item['column']} linha {item['row_index']}: valor {item['value']} ({item['deviation_ratio']}x da media)"
            for item in details[:4]
        ]
    findings.append(
        _finding(
            "outliers_numericos",
            severity,
            "qualidade",
            "Outliers numericos podem distorcer medias",
            f"{len(outliers)} coluna(s) numerica(s) possuem valores fora do padrao pelo criterio de intervalo interquartil.",
            "Validar se os maiores valores sao reais antes de usar medias, totais e graficos de tendencia.",
            evidence_lines,
        )
    )


def _check_numeric_identifiers(evidence: dict, findings: list[dict]) -> None:
    id_like = evidence["checks"]["id_like_numeric_columns"]
    metrics = evidence["dashboard"]["metrics_used"]
    if not id_like:
        return

    used_ids = [column for column in id_like if column in metrics]
    if used_ids:
        findings.append(
            _finding(
                "identificador_como_metrica",
                "critical",
                "metricas",
                "Identificador numerico usado como metrica",
                "Uma coluna com cara de ID/codigo entrou nos graficos como se fosse valor de negocio.",
                "Remover identificadores da lista de metricas e usar apenas como chave ou dimensao.",
                [f"Colunas: {', '.join(used_ids)}"],
            )
        )
    else:
        findings.append(
            _finding(
                "identificadores_numericos",
                "info",
                "tipagem",
                "Identificadores numericos detectados",
                "Algumas colunas numericas parecem IDs ou codigos e devem ser tratadas como dimensoes ou chaves.",
                "Evitar somar ou calcular media dessas colunas no chat analitico.",
                [f"Colunas: {', '.join(id_like[:8])}"],
            )
        )


def _check_ingest_warnings(evidence: dict, findings: list[dict]) -> None:
    warnings = evidence["checks"].get("ingest_warnings", [])
    if not warnings:
        return

    findings.append(
        _finding(
            "avisos_ingestao",
            "warning",
            "ingestao",
            "Ingestao gerou avisos de sanidade",
            "O parser precisou ajustar cabecalho, pular metadados ou reconciliar contagens antes da analise.",
            "Comparar o preview do DataSense com as primeiras linhas do arquivo original antes de confiar nos totais.",
            [str(warning) for warning in warnings[:4]],
        )
    )
def _request_ai_audit(evidence: dict, rule_audit: dict, api_key: str, model: str) -> dict:
    url = os.getenv("OPENAI_RESPONSES_URL", OPENAI_RESPONSES_URL).strip() or OPENAI_RESPONSES_URL
    body = {
        "model": model,
        "instructions": (
            "Voce e um auditor de qualidade de dados do DataSense. "
            "Revise se a analise automatica e confiavel antes de o usuario tomar decisoes. "
            "Use apenas as evidencias fornecidas. Foque em cabecalho, tipos, datas, metricas, totais negativos, "
            "nulos, duplicatas, outliers e graficos possivelmente montados com coluna errada. "
            "Responda em portugues do Brasil, com recomendacoes curtas e acionaveis."
        ),
        "input": json.dumps(
            {
                "evidence": evidence,
                "rule_audit": {
                    "analysis_score": rule_audit["analysis_score"],
                    "findings": rule_audit["findings"],
                },
            },
            ensure_ascii=False,
        ),
        "text": {"format": _ai_response_schema(), "verbosity": "low"},
        "max_output_tokens": 1800,
        "store": False,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "12"))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")[:500]
        raise RuntimeError(f"OpenAI retornou HTTP {exc.code}: {details}") from exc

    output_text = _extract_output_text(payload)
    if not output_text:
        raise RuntimeError("Resposta da IA sem texto estruturado.")

    return json.loads(output_text)


def _merge_ai_audit(rule_audit: dict, ai_payload: dict, model: str) -> dict:
    ai_findings = [
        _normalize_ai_finding(finding, index)
        for index, finding in enumerate(ai_payload.get("findings", []), start=1)
        if isinstance(finding, dict)
    ]
    findings = _deduplicate_findings([*rule_audit["findings"], *ai_findings])[:8]
    ai_score = _clamp_int(ai_payload.get("analysis_score"), 0, 100, rule_audit["analysis_score"])
    analysis_score = min(rule_audit["analysis_score"], ai_score)
    recommendations = _deduplicate_strings(
        [
            *[str(item) for item in ai_payload.get("recommendations", []) if str(item).strip()],
            *rule_audit["recommendations"],
        ]
    )[:6]

    return {
        **rule_audit,
        "mode": "ai",
        "ai_enabled": True,
        "ai_status": "completed",
        "model": model,
        "analysis_score": analysis_score,
        "summary": str(ai_payload.get("summary") or rule_audit["summary"]).strip(),
        "findings": findings,
        "recommendations": recommendations or _recommendations_from_findings(findings),
    }


def _ai_response_schema() -> dict:
    return {
        "type": "json_schema",
        "name": "datasense_quality_audit",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"type": "string"},
                "analysis_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "findings": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "string"},
                            "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                            "category": {"type": "string"},
                            "title": {"type": "string"},
                            "detail": {"type": "string"},
                            "recommendation": {"type": "string"},
                            "evidence": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
                        },
                        "required": ["id", "severity", "category", "title", "detail", "recommendation", "evidence"],
                    },
                },
                "recommendations": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            },
            "required": ["summary", "analysis_score", "findings", "recommendations"],
        },
    }


def _extract_dashboard_metrics(dashboard: dict) -> list[str]:
    metrics: list[str] = []
    for kpi in dashboard.get("kpis", []):
        label = str(kpi.get("label", ""))
        if label.startswith("Total de "):
            metrics.append(label.replace("Total de ", "", 1).strip())

    for chart in dashboard.get("charts", []):
        subtitle = str(chart.get("subtitle", ""))
        match = re.search(r"Soma de (.+?) por ", subtitle)
        if match:
            metrics.append(match.group(1).strip())

    return _deduplicate_strings(metrics)


def _dashboard_chart_evidence(dashboard: dict) -> list[dict]:
    charts = []
    for chart in dashboard.get("charts", [])[:6]:
        data = chart.get("data", [])
        charts.append(
            {
                "id": chart.get("id"),
                "title": chart.get("title"),
                "subtitle": chart.get("subtitle"),
                "type": chart.get("type"),
                "rows": len(data) if isinstance(data, list) else 0,
                "sample": _safe_records(data[:3]) if isinstance(data, list) else [],
                "insight": chart.get("insight"),
            }
        )
    return charts


def _numeric_stats(df: pd.DataFrame, numeric_columns: list[str]) -> dict[str, dict]:
    stats: dict[str, dict] = {}
    for column in numeric_columns[:30]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            continue

        stats[column] = {
            "count": int(series.shape[0]),
            "sum": round(float(series.sum()), 4),
            "mean": round(float(series.mean()), 4),
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
            "negative_rate": round(float((series < 0).sum() / len(series)), 4),
            "zero_rate": round(float((series == 0).sum() / len(series)), 4),
        }
    return stats


def _business_value_candidates(numeric_columns: list[str]) -> list[str]:
    candidates = []
    for column in numeric_columns:
        normalized = _normalize_text(column)
        if any(term == normalized or term in normalized for term in BUSINESS_VALUE_TERMS) and not _is_metric_noise(column):
            candidates.append(column)
    return candidates


def _possible_header_row(df: pd.DataFrame, generic_columns: list[str]) -> list[str]:
    if not generic_columns or df.empty:
        return []

    first_row = [str(value).strip() for value in df.iloc[0].tolist() if pd.notna(value) and str(value).strip()]
    if len(first_row) < 2:
        return []

    text_like = [value for value in first_row if re.search(r"[A-Za-zÀ-ÿ_]", value)]
    numeric_like = [value for value in first_row if pd.notna(pd.to_numeric(value, errors="coerce"))]
    known_terms = {"data", "mes", "trim", "produto", "cliente", "fornecedor", "valor", "receita", "venda", "compra"}
    known_hits = sum(any(term in _normalize_text(value) for term in known_terms) for value in text_like)

    if len(text_like) >= 2 and len(numeric_like) <= max(1, len(first_row) // 3) and known_hits >= 1:
        return text_like[:10]
    return []


def _sample_values_by_column(df: pd.DataFrame) -> dict[str, list[Any]]:
    samples = {}
    for column in list(df.columns)[:24]:
        values = df[column].dropna().head(6).tolist()
        samples[column] = [_safe_value(value) for value in values]
    return samples


def _safe_records(records: Any) -> list[dict]:
    if isinstance(records, pd.DataFrame):
        iterable = records.to_dict(orient="records")
    elif isinstance(records, list):
        iterable = records
    else:
        return []

    safe_rows: list[dict] = []
    for row in iterable:
        if not isinstance(row, dict):
            continue
        safe_rows.append({str(key): _safe_value(value) for key, value in row.items()})
    return safe_rows


def _safe_value(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        return _safe_value(value.item())
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, str):
        return value[:160]
    return str(value)[:160]


def _analysis_score(base_quality_score: int, findings: list[dict]) -> int:
    penalty = sum(SEVERITY_PENALTIES.get(finding.get("severity", "info"), 3) for finding in findings)
    return max(0, min(100, int(base_quality_score) - penalty))


def _audit_summary(score: int, findings: list[dict]) -> str:
    critical = sum(1 for finding in findings if finding.get("severity") == "critical")
    warnings = sum(1 for finding in findings if finding.get("severity") == "warning")
    if critical:
        return f"Analise exige revisao: {critical} ponto(s) critico(s) podem afetar metricas, datas ou cabecalho."
    if warnings:
        return f"Analise utilizavel com cautela: {warnings} alerta(s) merecem validacao antes de decisoes."
    if score >= 85:
        return "Analise com boa confiabilidade inicial para exploracao e dashboards."
    return "Analise sem bloqueios fortes, mas ainda recomenda validacao amostral."


def _recommendations_from_findings(findings: list[dict]) -> list[str]:
    recommendations = [finding["recommendation"] for finding in findings if finding.get("recommendation")]
    return _deduplicate_strings(recommendations)[:6]


def _finding(
    finding_id: str,
    severity: str,
    category: str,
    title: str,
    detail: str,
    recommendation: str,
    evidence: list[str],
) -> dict:
    return {
        "id": finding_id,
        "severity": severity,
        "category": category,
        "title": title,
        "detail": detail,
        "recommendation": recommendation,
        "evidence": evidence,
    }


def _normalize_ai_finding(finding: dict, index: int) -> dict:
    severity = str(finding.get("severity", "info")).lower()
    if severity not in SEVERITY_PENALTIES:
        severity = "info"

    evidence = finding.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = [str(evidence)]

    return _finding(
        str(finding.get("id") or f"ia_{index}")[:80],
        severity,
        str(finding.get("category") or "ia")[:80],
        str(finding.get("title") or "Achado da IA")[:140],
        str(finding.get("detail") or "")[:500],
        str(finding.get("recommendation") or "")[:300],
        [str(item)[:220] for item in evidence[:4]],
    )


def _deduplicate_findings(findings: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    for finding in findings:
        key = _normalize_text(f"{finding.get('category')} {finding.get('title')}")
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    unique.sort(key=lambda item: severity_order.get(item.get("severity", "info"), 2))
    return unique


def _deduplicate_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        key = _normalize_text(text)
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _extract_output_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "".join(chunks).strip()


def _ai_audit_disabled() -> bool:
    value = os.getenv("DATASENSE_AI_AUDIT_ENABLED", "true").strip().lower()
    return value in {"0", "false", "no", "off"}


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).replace(os.getenv("OPENAI_API_KEY", ""), "[redacted]")
    return message[:500] or "Falha ao chamar a IA."


def _clamp_int(value: Any, minimum: int, maximum: int, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = fallback
    return max(minimum, min(maximum, parsed))


def _is_generic_column(column: str) -> bool:
    normalized = _normalize_text(column)
    return bool(re.fullmatch(r"coluna_\d+", normalized) or normalized.startswith("unnamed"))


def _looks_like_identifier(column: str) -> bool:
    normalized = _normalize_text(column)
    identifier_terms = ("id", "codigo", "cod", "sku", "cpf", "cnpj", "cep", "telefone", "phone")
    return any(term == normalized or normalized.startswith(f"{term}_") or normalized.endswith(f"_{term}") for term in identifier_terms)


def _is_metric_noise(column: str) -> bool:
    normalized = _normalize_text(column)
    return any(term == normalized or normalized.startswith(f"{term}_") or normalized.endswith(f"_{term}") for term in METRIC_NOISE_TERMS)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _normalize_text(value)).strip("_")


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^a-zA-Z0-9_]+", "_", text.lower())
    return re.sub(r"_+", "_", text).strip("_")


def _format_number(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    if isinstance(value, float):
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(value)
