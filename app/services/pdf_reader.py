import logging
from dataclasses import dataclass
from pathlib import Path

import pypdf
import pytesseract
from pdf2image import convert_from_path

from app.config import settings

logger = logging.getLogger(__name__)

MIN_CHARS_PER_PAGE = 50


@dataclass
class ExtractionInfo:
    text: str
    method: str
    page_count: int
    char_count: int
    is_ocr_fallback: bool


def extract_text_from_pdf(file_path: Path) -> ExtractionInfo:
    """
    Text aus PDF extrahieren.
    Falls der Text zu duenn ist (gescanntes Dokument), wird OCR verwendet.
    """
    reader = pypdf.PdfReader(str(file_path))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    full_text = "\n\n".join(pages_text)
    avg_chars = len(full_text.strip()) / max(len(reader.pages), 1)

    if avg_chars < MIN_CHARS_PER_PAGE:
        logger.info(
            f"{file_path.name}: Wenig Text gefunden ({avg_chars:.0f} Zeichen/Seite), "
            f"starte OCR..."
        )
        full_text = _ocr_pdf(file_path)
        return ExtractionInfo(
            text=full_text,
            method="ocr",
            page_count=len(reader.pages),
            char_count=len(full_text),
            is_ocr_fallback=True,
        )

    logger.info(
        f"{file_path.name}: Text extrahiert ({len(full_text)} Zeichen, "
        f"{len(reader.pages)} Seiten)"
    )
    return ExtractionInfo(
        text=full_text,
        method="text_extraction",
        page_count=len(reader.pages),
        char_count=len(full_text),
        is_ocr_fallback=False,
    )


def _ocr_pdf(file_path: Path) -> str:
    """PDF-Seiten in Bilder konvertieren und per OCR verarbeiten."""
    images = convert_from_path(str(file_path), dpi=300)
    texts = []
    for i, img in enumerate(images):
        text = pytesseract.image_to_string(img, lang=settings.OCR_LANGUAGE)
        texts.append(f"--- Seite {i + 1} ---\n{text}")
        logger.info(f"OCR Seite {i + 1}/{len(images)}: {len(text)} Zeichen")
    return "\n\n".join(texts)


def extract_from_multiple(file_paths: list[Path]) -> str:
    """Text aus mehreren hochgeladenen PDFs extrahieren und zusammenfuegen."""
    all_texts = []
    for fp in file_paths:
        try:
            info = extract_text_from_pdf(fp)
            all_texts.append(
                f"=== Dokument: {fp.name} (Methode: {info.method}) ===\n{info.text}"
            )
        except Exception as e:
            logger.error(f"Fehler bei {fp.name}: {e}")
            all_texts.append(f"=== Dokument: {fp.name} (FEHLER: {e}) ===")
    return "\n\n".join(all_texts)
