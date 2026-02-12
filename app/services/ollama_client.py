import json
import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
) -> str:
    """
    Chat-Completion-Anfrage an Ollama senden.
    Nutzt Streaming um lange Antworten und Timeouts zu handhaben.
    """
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": 4096,
        },
    }

    full_response = ""
    with requests.post(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        json=payload,
        stream=True,
        timeout=settings.OLLAMA_TIMEOUT,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "message" in chunk and "content" in chunk["message"]:
                full_response += chunk["message"]["content"]
            if chunk.get("done", False):
                break

    logger.info(f"Ollama-Antwort: {len(full_response)} Zeichen")
    return full_response.strip()


def check_health() -> bool:
    """Pruefen ob Ollama erreichbar ist und das Modell verfuegbar ist."""
    try:
        resp = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=10)
        data = resp.json()
        model_names = [m["name"] for m in data.get("models", [])]
        return any(settings.OLLAMA_MODEL in name for name in model_names)
    except Exception:
        return False
