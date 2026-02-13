import logging
from pathlib import Path

import requests
from flask import Flask

from app.config import settings
from app.routers.forms import forms_bp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)
app.config["MAX_CONTENT_LENGTH"] = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

app.register_blueprint(forms_bp)

# Version aus VERSION-Datei laden
def get_version():
    version_file = Path(__file__).parent.parent / "VERSION"
    try:
        if version_file.exists():
            return version_file.read_text(encoding='utf-8').strip()
        else:
            logger.warning(f"VERSION-Datei nicht gefunden: {version_file}")
            return "0.1"
    except Exception as e:
        logger.error(f"Fehler beim Laden der VERSION-Datei: {e}")
        return "0.1"

@app.context_processor
def inject_version():
    return {"version": get_version()}

# Startup-Pruefungen
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    resp = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=10)
    resp.raise_for_status()
    models = [m["name"] for m in resp.json().get("models", [])]
    if any(settings.OLLAMA_MODEL in m for m in models):
        logger.info(f"Ollama erreichbar, Modell '{settings.OLLAMA_MODEL}' verfuegbar")
    else:
        logger.warning(
            f"Ollama erreichbar, aber Modell '{settings.OLLAMA_MODEL}' "
            f"nicht gefunden. Verfuegbare Modelle: {models}"
        )
except Exception as e:
    logger.warning(f"Ollama beim Start nicht erreichbar: {e}")
