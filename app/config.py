import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "300"))
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "/app/output"))
    FORM_TEMPLATE_DIR: Path = Path(os.getenv("FORM_TEMPLATE_DIR", "/app/data"))
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    MAX_UPLOAD_FILES: int = int(os.getenv("MAX_UPLOAD_FILES", "10"))
    OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "deu")
    OCR_DPI: int = int(os.getenv("OCR_DPI", "300"))
    MAX_OLLAMA_PASSES: int = int(os.getenv("MAX_OLLAMA_PASSES", "3"))
    # Context-Fenstergröße Standard: für kurze Anfragen (ICD-10-Validierung, Warmup)
    OLLAMA_NUM_CTX: int = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
    # Context-Fenstergröße für Pässe mit vollem Quelltext (Pass 1-4): passt noch vollständig in VRAM
    # Benchmark: 8192→10.1 GB VRAM (100%), 16384≈11.2 GB VRAM (100%), 32768→17.2 GB (64%, CPU-Overflow)
    OLLAMA_NUM_CTX_LARGE: int = int(os.getenv("OLLAMA_NUM_CTX_LARGE", "12288"))


settings = Settings()
