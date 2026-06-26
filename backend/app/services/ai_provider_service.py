import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
PLACEHOLDER_API_KEYS = {
    "sua_chave_openai",
    "sua_chave_openrouter",
    "your_openai_api_key",
    "your_openrouter_api_key",
    "cole_sua_chave_aqui",
}
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._~:/-]{2,160}$")


def has_real_api_key(api_key: str) -> bool:
    return bool(api_key and api_key.lower() not in PLACEHOLDER_API_KEYS)


def resolve_ai_credentials(requested_model: str | None = None) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    provider = "openrouter"
    if not has_real_api_key(api_key):
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        provider = "openai_compat"

    default_model = (
        os.getenv("OPENROUTER_MODEL", "").strip()
        or os.getenv("OPENAI_MODEL", "").strip()
        or DEFAULT_OPENROUTER_MODEL
    )
    model = normalize_model(requested_model, default_model)
    return {"api_key": api_key, "model": model, "provider": provider}


def normalize_model(requested_model: str | None, fallback: str = DEFAULT_OPENROUTER_MODEL) -> str:
    model = str(requested_model or "").strip() or fallback
    if not _MODEL_PATTERN.fullmatch(model):
        return fallback
    return model


def request_openrouter_json(
    *,
    system_prompt: str,
    payload: dict,
    api_key: str,
    model: str,
    max_tokens: int = 1800,
) -> dict:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Responda somente com JSON valido, sem markdown. "
                    "Use este pacote de evidencias:\n"
                    f"{json.dumps(payload, ensure_ascii=False)}"
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        os.getenv("OPENROUTER_CHAT_COMPLETIONS_URL", OPENROUTER_CHAT_COMPLETIONS_URL).strip()
        or OPENROUTER_CHAT_COMPLETIONS_URL,
        data=json.dumps(body).encode("utf-8"),
        headers=_openrouter_headers(api_key),
        method="POST",
    )

    timeout = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", os.getenv("OPENAI_TIMEOUT_SECONDS", "12")))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")[:500]
        raise RuntimeError(f"OpenRouter retornou HTTP {exc.code}: {details}") from exc

    content = extract_chat_content(response_payload)
    if not content:
        raise RuntimeError("Resposta da IA sem texto estruturado.")
    return parse_json_content(content)


def extract_chat_content(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                chunks.append(item["text"])
            elif isinstance(item, str):
                chunks.append(item)
        return "".join(chunks).strip()
    return ""


def parse_json_content(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def safe_ai_error_message(exc: Exception) -> str:
    message = str(exc)
    for env_key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        secret = os.getenv(env_key, "")
        if secret:
            message = message.replace(secret, "[redacted]")
    return message[:500] or "Falha ao chamar a IA."


def _openrouter_headers(api_key: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    referer = os.getenv("OPENROUTER_SITE_URL", "").strip()
    app_title = os.getenv("OPENROUTER_APP_TITLE", "DataSense").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if app_title:
        headers["X-OpenRouter-Title"] = app_title
    return headers
