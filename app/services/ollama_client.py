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


def get_gpu_layer_ratio() -> str:
    """
    Gibt das VRAM-zu-Gesamt-Verhältnis des geladenen Modells zurück (Diagnosezwecke).
    Zeigt an, wie viel des Modells auf GPU vs. CPU liegt.
    """
    try:
        resp = requests.get(f"{settings.OLLAMA_BASE_URL}/api/ps", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("models", [])
        for m in models:
            if settings.OLLAMA_MODEL in m.get("name", ""):
                size_total = m.get("size", 0)
                size_vram = m.get("size_vram", 0)
                if size_total > 0:
                    pct = size_vram / size_total * 100
                    total_gb = size_total / 1024**3
                    vram_gb = size_vram / 1024**3
                    cpu_gb = (size_total - size_vram) / 1024**3
                    return (
                        f"{pct:.0f}% auf GPU ({vram_gb:.1f} GB VRAM, "
                        f"{cpu_gb:.1f} GB CPU) von {total_gb:.1f} GB gesamt"
                    )
        return "Modell nicht geladen"
    except Exception as e:
        return f"Unbekannt ({e})"


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    num_ctx: int | None = None,
) -> str:
    """
    Chat-Completion-Anfrage an Ollama senden.
    Nutzt Streaming um lange Antworten und Timeouts zu handhaben.
    Führt automatisch ein Warmup durch, falls das Modell nicht geladen ist.

    num_ctx: Context-Fenstergröße (None = settings.OLLAMA_NUM_CTX).
             Für Pässe mit vollem Quelltext settings.OLLAMA_NUM_CTX_LARGE übergeben.
    """
    # Warmup durchführen, falls Modell nicht im Speicher
    warmup_model(settings.OLLAMA_MODEL)

    effective_ctx = num_ctx if num_ctx is not None else settings.OLLAMA_NUM_CTX

    # GPU-Nutzung loggen
    gpu_info = get_gpu_layer_ratio()
    if "CPU" in gpu_info and "0.0 GB CPU" not in gpu_info:
        logger.warning(
            f"Modell läuft teilweise auf CPU! {gpu_info} – "
            f"num_ctx={effective_ctx} (ggf. OLLAMA_NUM_CTX_LARGE reduzieren)"
        )
    else:
        logger.debug(f"GPU-Nutzung: {gpu_info}, num_ctx={effective_ctx}")

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": 4096,   # Strukturierte JSON-Antworten brauchen selten mehr
            "num_ctx": effective_ctx,
            "num_gpu": -1,         # Alle Layer auf GPU erzwingen (kein CPU-Offloading)
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
