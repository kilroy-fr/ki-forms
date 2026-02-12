import json
import logging
import re

from app.models.form_schema import FormField, FieldType, ExtractionResult
from app.services.ollama_client import chat_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Du bist ein medizinischer Dokumentationsassistent. Deine Aufgabe ist es, aus \
medizinischen Quelldokumenten (Arztbriefe, Befundberichte, Entlassungsbriefe etc.) \
die relevanten Informationen zu extrahieren und den Feldern eines Formulars der \
Deutschen Rentenversicherung (Befundbericht S0051) zuzuordnen.

WICHTIGE REGELN:
1. Extrahiere NUR Informationen, die TATSAECHLICH im Quelltext vorhanden sind.
2. Erfinde NIEMALS Informationen. Wenn eine Information nicht im Text steht, lasse das Feld weg.
3. Fuer Datumsfelder verwende das Format TT.MM.JJJJ.
4. Fuer Checkboxen antworte mit "ja" oder "nein".
5. Fuer ICD-10-Codes gib den exakten Code an (z.B. M54.5).
6. Antworte AUSSCHLIESSLICH im vorgegebenen JSON-Format.
7. Bei Unsicherheit setze confidence auf "low" statt zu raten."""


def _build_text_fields_prompt(
    fields: list[FormField],
    source_text: str,
) -> str:
    """Prompt fuer Textfeld-Extraktion bauen."""
    field_descriptions = []
    for f in fields:
        if f.field_type == FieldType.TEXT:
            field_descriptions.append(f'  "{f.field_name}": "{f.description}"')

    fields_block = ",\n".join(field_descriptions)

    return f"""Hier ist der Quelltext aus den hochgeladenen medizinischen Dokumenten:

--- QUELLTEXT BEGINN ---
{source_text}
--- QUELLTEXT ENDE ---

Extrahiere die folgenden Informationen aus dem Quelltext und ordne sie den Formularfeldern zu.
Fuer jedes Feld, fuer das du eine Information findest, gib den Wert und deine Konfidenz an.

FELDER:
{{
{fields_block}
}}

Antworte im folgenden JSON-Format (NUR das JSON, kein anderer Text):
{{
  "fields": [
    {{
      "field_name": "FELDNAME",
      "value": "extrahierter Wert",
      "confidence": "high|medium|low"
    }}
  ]
}}

Lasse Felder, fuer die keine Information im Quelltext gefunden wurde, komplett weg."""


def _build_checkbox_prompt(
    fields: list[FormField],
    source_text: str,
) -> str:
    """Prompt fuer Checkbox-Extraktion bauen."""
    checkbox_descriptions = []
    for f in fields:
        if f.field_type == FieldType.CHECKBOX:
            checkbox_descriptions.append(f'  "{f.field_name}": "{f.description}"')

    cb_block = ",\n".join(checkbox_descriptions)

    return f"""Hier ist der Quelltext aus den hochgeladenen medizinischen Dokumenten:

--- QUELLTEXT BEGINN ---
{source_text}
--- QUELLTEXT ENDE ---

Bestimme anhand des Quelltexts, welche der folgenden Checkboxen angekreuzt werden sollen.

CHECKBOXEN:
{{
{cb_block}
}}

Antworte im folgenden JSON-Format (NUR das JSON, kein anderer Text):
{{
  "checkboxes": [
    {{
      "field_name": "FELDNAME",
      "value": "ja",
      "confidence": "high|medium|low"
    }}
  ]
}}

Gib NUR Checkboxen an, die basierend auf dem Quelltext angekreuzt ("ja") werden sollen.
Lasse alle Checkboxen weg, die nicht angekreuzt werden sollen oder bei denen du unsicher bist."""


def _build_retry_prompt(
    fields: list[FormField],
    source_text: str,
) -> str:
    """Erneuter Prompt fuer im ersten Durchgang nicht gefundene Felder."""
    field_list = "\n".join(f"- {f.field_name}: {f.description}" for f in fields)
    return f"""Die folgenden Felder konnten im ersten Durchgang nicht aus dem Quelltext \
extrahiert werden. Bitte versuche erneut, diese Informationen zu finden. Suche auch nach \
indirekten Hinweisen, Synonymen oder aehnlichen Formulierungen.

--- QUELLTEXT BEGINN ---
{source_text}
--- QUELLTEXT ENDE ---

GESUCHTE FELDER:
{field_list}

Antworte im JSON-Format:
{{
  "fields": [
    {{
      "field_name": "FELDNAME",
      "value": "extrahierter Wert",
      "confidence": "high|medium|low"
    }}
  ]
}}

Gib NUR Felder an, fuer die du tatsaechlich einen Wert im Text gefunden hast."""


def extract_fields(
    fields: list[FormField],
    source_text: str,
) -> list[ExtractionResult]:
    """
    Multi-Pass-Extraktion:
      Pass 1: Textfelder extrahieren
      Pass 2: Checkboxen extrahieren
      Pass 3 (optional): Nicht gefundene Textfelder nochmal versuchen
    """
    all_results: list[ExtractionResult] = []

    # --- Pass 1: Textfelder ---
    text_fields = [f for f in fields if f.field_type == FieldType.TEXT]
    if text_fields:
        logger.info(f"Pass 1: Extrahiere {len(text_fields)} Textfelder...")
        prompt = _build_text_fields_prompt(text_fields, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt)
            results = _parse_response(response, "fields")
            all_results.extend(results)
            logger.info(f"Pass 1: {len(results)} Textfelder extrahiert")
        except Exception as e:
            logger.error(f"Pass 1 fehlgeschlagen: {e}")

    # --- Pass 2: Checkboxen ---
    checkbox_fields = [f for f in fields if f.field_type == FieldType.CHECKBOX]
    if checkbox_fields:
        logger.info(f"Pass 2: Extrahiere {len(checkbox_fields)} Checkboxen...")
        prompt = _build_checkbox_prompt(checkbox_fields, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt)
            results = _parse_response(response, "checkboxes")
            all_results.extend(results)
            logger.info(f"Pass 2: {len(results)} Checkboxen extrahiert")
        except Exception as e:
            logger.error(f"Pass 2 fehlgeschlagen: {e}")

    # --- Pass 3: Retry fuer nicht gefundene Textfelder ---
    filled_names = {r.field_name for r in all_results}
    unfilled_text = [f for f in text_fields if f.field_name not in filled_names]

    if unfilled_text and len(unfilled_text) < len(text_fields):
        logger.info(
            f"Pass 3: Versuche {len(unfilled_text)} nicht gefundene Felder erneut..."
        )
        prompt = _build_retry_prompt(unfilled_text, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt)
            results = _parse_response(response, "fields")
            all_results.extend(results)
            logger.info(f"Pass 3: {len(results)} zusaetzliche Felder extrahiert")
        except Exception as e:
            logger.error(f"Pass 3 fehlgeschlagen: {e}")

    logger.info(f"Extraktion abgeschlossen: {len(all_results)} Felder insgesamt")
    return all_results


def _parse_response(raw: str, key: str) -> list[ExtractionResult]:
    """JSON-Antwort von Ollama parsen, mit Fallback-Logik."""
    cleaned = raw.strip()

    # Markdown Code-Bloecke entfernen
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    data = None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                logger.error(f"JSON-Parsing fehlgeschlagen: {raw[:500]}")
                return []
        else:
            logger.error(f"Kein JSON in Ollama-Antwort gefunden: {raw[:500]}")
            return []

    if data is None:
        return []

    results = []
    for item in data.get(key, []):
        if "field_name" in item and "value" in item:
            results.append(
                ExtractionResult(
                    field_name=item["field_name"],
                    value=str(item["value"]),
                    confidence=item.get("confidence", "medium"),
                )
            )
    return results
