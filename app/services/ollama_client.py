import json
import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)

# Cache für Warmup-Status pro Modell
_warmed_up_models = set()


def is_model_loaded(model_name: str) -> bool:
    """
    Prüft ob das Modell bereits im Speicher geladen ist.
    Verwendet den /api/ps Endpoint von Ollama.
    """
    try:
        resp = requests.get(f"{settings.OLLAMA_BASE_URL}/api/ps", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        loaded_models = [m.get("name", "") for m in data.get("models", [])]
        return any(model_name in name for name in loaded_models)
    except Exception as e:
        logger.warning(f"Konnte Modellstatus nicht prüfen: {e}")
        return False


def warmup_model(model_name: str) -> None:
    """
    Führt ein Warmup für das Modell durch, indem eine minimale Anfrage gesendet wird.
    Dies lädt das Modell in den Speicher.
    """
    if model_name in _warmed_up_models:
        logger.debug(f"Modell {model_name} wurde bereits aufgewärmt")
        return

    if is_model_loaded(model_name):
        logger.info(f"Modell {model_name} ist bereits im Speicher geladen")
        _warmed_up_models.add(model_name)
        return

    logger.info(f"Starte Warmup für Modell {model_name}...")
    try:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Hi"},
            ],
            "stream": False,
            "options": {
                "num_predict": 1,
            },
        }

        resp = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        _warmed_up_models.add(model_name)
        logger.info(f"Warmup für Modell {model_name} abgeschlossen")
    except Exception as e:
        logger.error(f"Warmup für Modell {model_name} fehlgeschlagen: {e}")
        # Trotzdem zur Liste hinzufügen, um nicht bei jeder Anfrage erneut zu versuchen
        _warmed_up_models.add(model_name)


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
) -> str:
    """
    Chat-Completion-Anfrage an Ollama senden.
    Nutzt Streaming um lange Antworten und Timeouts zu handhaben.
    Führt automatisch ein Warmup durch, falls das Modell nicht geladen ist.
    """
    # Warmup durchführen, falls Modell nicht im Speicher
    warmup_model(settings.OLLAMA_MODEL)

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": 16384,  # Explizit hoher Wert für längere Antworten
            "num_ctx": 32768,      # Größeres Context-Fenster für längere Antworten
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
