"""DeepSeek LLM client."""

from __future__ import annotations

from typing import Any

try:
    import requests
except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime env
    raise RuntimeError("Missing dependency `requests`. Install requirements first.") from exc

try:
    from src.config import get_settings
    from src.schemas import LLMAnswer
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from config import get_settings
    from schemas import LLMAnswer


REQUEST_TIMEOUT_SECONDS = 60


def _extract_message_content(payload: dict[str, Any]) -> str:
    """Extract assistant text from a chat completion payload."""

    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("DeepSeek response does not contain `choices`.")

    message = choices[0].get("message") or {}
    content = message.get("content", "")

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [item.get("text", "") for item in content if isinstance(item, dict)]
        return "".join(parts).strip()
    return str(content).strip()


def generate_answer(prompt: str) -> LLMAnswer:
    """Send a prompt to the configured LLM backend and normalize the response."""

    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise ValueError("Prompt cannot be empty.")

    settings = get_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("Missing `DEEPSEEK_API_KEY`. Create a `.env` file or export it.")

    endpoint = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.deepseek_model,
        "temperature": settings.temperature,
        "messages": [
            {
                "role": "system",
                "content": "You are a factual assistant that answers only from supplied context.",
            },
            {"role": "user", "content": normalized_prompt},
        ],
    }

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"DeepSeek request failed: {exc}") from exc

    data = response.json()
    answer_text = _extract_message_content(data)
    if not answer_text:
        raise RuntimeError("DeepSeek returned an empty answer.")

    return LLMAnswer(answer_text=answer_text, raw_response=data)
