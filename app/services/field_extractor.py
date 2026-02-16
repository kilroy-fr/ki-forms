import json
import logging
import re
from pathlib import Path
from typing import Optional

from app.models.form_schema import FormField, FieldType, ExtractionResult
from app.services.ollama_client import chat_completion

logger = logging.getLogger(__name__)

# ICD-10-Codes Cache
_icd10_codes: Optional[list[dict]] = None

# Die 6 großen Textfelder, die separat extrahiert werden
LARGE_TEXT_FIELDS = {
    "ANAMNESE",
    "FUNKTIONSEINSCHRAENKUNGEN",
    "THERAPIE",
    "UNTERSUCHUNGSBEFUNDE",
    "MED_TECHN_BEFUNDE",
    "LEBENSUMSTAENDE",
}

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
7. Bei Unsicherheit setze confidence auf "low" statt zu raten.
8. Extrahiere NUR die im User-Prompt aufgelisteten Felder. Ignoriere alle anderen Informationen.

HINWEISE ZUR EXTRAKTION:

DIAGNOSEN:
- Fokussiere auf FUNKTIONSEINSCHRAENKUNGEN, nicht nur die Diagnose selbst
- Beispiel: Statt "Bandscheibenvorfall" -> "schmerzhafte Bewegungseinschraenkung der LWS mit Schwaeche"
- Primaere rehabilitationsbegrundende Diagnose an erster Stelle

ANAMNESE UND FUNKTIONSEINSCHRAENKUNGEN:
- Detaillierte Darstellung von Beschwerden und Beeintraechtigungen
- Bio-psychosoziales Modell beachten

THERAPIE UND BEHANDLUNG:
- Bisherige und aktuelle Therapien mit Art, Umfang und Dosierungen
- Arbeitsunfaehigkeit: Zeitpunkt und Dauer

KONTEXTFAKTOREN:
- Familiaere Belastungen, Pflegeverantwortung
- Finanzielle Schwierigkeiten, Arbeitsplatzprobleme

BESONDERHEITEN:
- Onkologie: Primaertherapie-Status, Chemotherapie-Schema
- Abhaengigkeitserkrankungen: Suchtberatung, Substitutionsbehandlung
- Psychische Erkrankungen: Schweregradeinschaetzung"""


def _load_icd10_codes() -> list[dict]:
    """Laden der ICD-10-Codes aus der JSON-Datei (mit Caching)."""
    global _icd10_codes
    if _icd10_codes is not None:
        return _icd10_codes

    icd10_path = Path(__file__).parent.parent.parent / "data" / "icd10_codes_2025.json"
    try:
        with open(icd10_path, "r", encoding="utf-8") as f:
            _icd10_codes = json.load(f)
            logger.info(f"ICD-10-Codes geladen: {len(_icd10_codes)} Einträge")
            return _icd10_codes
    except Exception as e:
        logger.error(f"Fehler beim Laden der ICD-10-Codes: {e}")
        return []


def _filter_relevant_icd10_codes(
    diagnosis_text: str,
    all_codes: list[dict],
    max_results: int = 150,
) -> list[dict]:
    """
    Filtert ICD-10-Codes, die für die Diagnose relevant sein könnten.
    Verwendet einfaches Keyword-Matching auf der Krankheitsbezeichnung.
    """
    # Extrahiere Schlüsselwörter aus der Diagnose (Wörter mit min. 3 Zeichen)
    words = diagnosis_text.lower().split()
    keywords = [w.strip('.,;:!?()[]') for w in words if len(w) >= 3]

    if not keywords:
        # Fallback: Returniere eine Auswahl verschiedener Code-Bereiche
        return all_codes[:max_results]

    # Score jeden ICD-10-Code basierend auf Keyword-Matches
    scored_codes = []
    for code in all_codes:
        krankheit_lower = code['Krankheit'].lower()
        score = sum(1 for kw in keywords if kw in krankheit_lower)
        if score > 0:
            scored_codes.append((score, code))

    # Sortiere nach Score (absteigend) und nimm die Top-Ergebnisse
    scored_codes.sort(key=lambda x: x[0], reverse=True)
    relevant_codes = [code for _, code in scored_codes[:max_results]]

    # Wenn keine relevanten Codes gefunden, returniere eine Auswahl
    if not relevant_codes:
        logger.warning(f"Keine relevanten ICD-10-Codes für '{diagnosis_text[:50]}...' gefunden")
        return all_codes[:max_results]

    logger.info(f"Gefiltert: {len(relevant_codes)} relevante ICD-10-Codes von {len(all_codes)}")
    return relevant_codes


def _build_icd10_validation_prompt(
    diagnosis_text: str,
    diagnosis_number: int,
    icd10_codes: list[dict],
) -> str:
    """Prompt zum Abgleich einer Diagnose mit ICD-10-Codes."""
    # Filtere relevante Codes basierend auf der Diagnose
    relevant_codes = _filter_relevant_icd10_codes(diagnosis_text, icd10_codes, max_results=150)

    codes_text = "\n".join([f"{c['Code']}: {c['Krankheit']}" for c in relevant_codes])

    total_codes = len(icd10_codes)
    shown_codes = len(relevant_codes)

    return f"""Aufgabe: Bestimme den passenden ICD-10-Code für die folgende Diagnose.

DIAGNOSE {diagnosis_number}:
{diagnosis_text}

WICHTIG:
- Gib NUR einen ICD-10-Code an, wenn du dir SICHER bist
- Wenn du unsicher bist, gib KEINEN Code an
- Der Code muss exakt dem ICD-10-Standard entsprechen (z.B. M54.5, F32.1)
- Setze confidence auf "high" nur wenn die Zuordnung eindeutig ist

Die folgenden {shown_codes} ICD-10-Codes wurden als besonders relevant gefiltert (von insgesamt {total_codes}):
{codes_text}

Antworte im folgenden JSON-Format (NUR das JSON, kein anderer Text):
{{
  "icd10_code": "CODE" oder null,
  "confidence": "high|medium|low",
  "reasoning": "Kurze Begründung"
}}

Wenn kein passender Code gefunden wurde oder du unsicher bist, setze "icd10_code" auf null."""


def _strip_icd10_suffix(code: str) -> str:
    """
    Entfernt Seitenlokalisations-Suffixe von ICD-10-Codes.

    Suffixe: L (links), R (rechts), G (gesichert), V (Verdacht),
             Z (Zustand nach), A (ausgeschlossen), etc.
    Kombinationen: LG, RG, LV, RV, etc.

    Beispiele:
        M54.5 L -> M54.5
        M54.5L -> M54.5
        M54.5 LG -> M54.5
        M54.5LG -> M54.5
    """
    if not code:
        return code

    # Regex-Pattern für ICD-10-Suffixe am Ende
    # Matcht optional ein Leerzeichen, gefolgt von 1-2 Buchstaben am Ende
    pattern = r'\s*[A-Z]{1,2}$'

    cleaned = re.sub(pattern, '', code.strip())
    return cleaned


def _validate_icd10_code(code: str, icd10_codes: list[dict]) -> bool:
    """Prüft, ob ein ICD-10-Code in der Liste existiert."""
    if not code or code.upper() == "UNDEF":
        return False

    # Entferne Seitenlokalisations-Suffixe vor dem Abgleich
    code_cleaned = _strip_icd10_suffix(code)
    code_upper = code_cleaned.upper().strip()

    for entry in icd10_codes:
        if entry["Code"].upper() == code_upper:
            return True
    return False


def _build_text_fields_prompt(
    fields: list[FormField],
    source_text: str,
) -> str:
    """Prompt fuer Textfeld-Extraktion bauen."""
    field_descriptions = []
    for f in fields:
        if f.field_type == FieldType.TEXT and f.extract_from_ai:
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


def _build_large_text_fields_prompt(
    fields: list[FormField],
    source_text: str,
) -> str:
    """Prompt für große Textfeld-Extraktion bauen (narrative Abschnitte)."""
    field_descriptions = []
    for f in fields:
        if f.field_type == FieldType.TEXT and f.extract_from_ai and f.field_name in LARGE_TEXT_FIELDS:
            field_descriptions.append(f'  "{f.field_name}": "{f.description}"')

    fields_block = ",\n".join(field_descriptions)

    return f"""Hier ist der Quelltext aus den hochgeladenen medizinischen Dokumenten:

--- QUELLTEXT BEGINN ---
{source_text}
--- QUELLTEXT ENDE ---

WICHTIG: Du extrahierst jetzt AUSSCHLIESSLICH die großen narrativen Textabschnitte.
Diese Felder enthalten detaillierte medizinische Beschreibungen und können mehrere Absätze umfassen.

Extrahiere die folgenden VOLLSTAENDIGEN Textabschnitte aus dem Quelltext:

FELDER:
{{
{fields_block}
}}

EXTRAKTIONSREGELN FÜR GROSSE TEXTFELDER:
1. Extrahiere VOLLSTAENDIGE Absätze und Beschreibungen, nicht nur Stichworte
2. Behalte die Struktur und Formatierung des Originaltextes bei
3. Erfasse ALLE relevanten Details für das jeweilige Feld
4. Bei mehreren relevanten Abschnitten: Kombiniere sie sinnvoll
5. Entferne keine medizinisch relevanten Informationen
6. Wenn ein Abschnitt nicht im Text vorkommt, lasse das Feld komplett weg

Antworte im folgenden JSON-Format (NUR das JSON, kein anderer Text oder Code-Block):
{{
  "fields": [
    {{
      "field_name": "FELDNAME",
      "value": "vollständiger extrahierter Textabschnitt mit allen Details",
      "confidence": "high|medium|low"
    }}
  ]
}}

WICHTIG: Antworte mit reinem JSON ohne ```-Markierungen oder zusätzlichen Text."""


def _build_checkbox_prompt(
    fields: list[FormField],
    source_text: str,
) -> str:
    """Prompt fuer Checkbox-Extraktion bauen."""
    checkbox_descriptions = []
    for f in fields:
        if f.field_type == FieldType.CHECKBOX and f.extract_from_ai:
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


def _validate_diagnoses_icd10(
    all_results: list[ExtractionResult],
) -> list[ExtractionResult]:
    """
    Pass 4: ICD-10-Validierung für Diagnosen 1-4.

    Prüft für jede Diagnose, ob:
    - Ein Diagnosetext vorhanden ist
    - Der ICD-10-Code fehlt oder die Confidence nicht auf "high" steht

    Wenn ja, wird versucht, den ICD-10-Code zu bestimmen.
    """
    icd10_codes = _load_icd10_codes()
    if not icd10_codes:
        logger.warning("ICD-10-Codes konnten nicht geladen werden, Pass 4 wird übersprungen")
        return []

    new_results = []

    # Prüfe Diagnosen 1-4
    for i in range(1, 5):
        diagnosis_field = f"VERS_DIAGNOSE_{i}"
        icd10_field = f"VERS_DIAGNOSESCH_{i}"

        # Suche nach der Diagnose in den Ergebnissen
        diagnosis_result = next(
            (r for r in all_results if r.field_name == diagnosis_field),
            None
        )

        # Wenn keine Diagnose vorhanden, überspringe
        if not diagnosis_result or not diagnosis_result.value:
            continue

        # Prüfe, ob ICD-10-Code vorhanden und sicher ist
        icd10_result = next(
            (r for r in all_results if r.field_name == icd10_field),
            None
        )

        needs_validation = False
        if not icd10_result or not icd10_result.value:
            needs_validation = True
            logger.info(f"Diagnose {i}: Kein ICD-10-Code vorhanden")
        elif icd10_result.confidence != "high":
            needs_validation = True
            logger.info(f"Diagnose {i}: ICD-10-Code '{icd10_result.value}' nicht sicher (confidence={icd10_result.confidence})")
        elif not _validate_icd10_code(icd10_result.value, icd10_codes):
            needs_validation = True
            logger.info(f"Diagnose {i}: ICD-10-Code '{icd10_result.value}' nicht in Datenbank gefunden")

        if needs_validation:
            logger.info(f"Diagnose {i}: Versuche ICD-10-Code zu bestimmen für '{diagnosis_result.value}'")
            prompt = _build_icd10_validation_prompt(
                diagnosis_result.value,
                i,
                icd10_codes
            )

            try:
                response = chat_completion(SYSTEM_PROMPT, prompt)
                # Parse JSON-Antwort
                cleaned = response.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.split("\n")
                    lines = lines[1:]
                    if lines and lines[-1].strip().startswith("```"):
                        lines = lines[:-1]
                    cleaned = "\n".join(lines).strip()

                data = json.loads(cleaned)

                if data.get("icd10_code") and data["icd10_code"] != "null":
                    # Validiere den vorgeschlagenen Code
                    proposed_code = data["icd10_code"]
                    # Entferne Seitenlokalisations-Suffixe
                    proposed_code_cleaned = _strip_icd10_suffix(proposed_code)
                    if _validate_icd10_code(proposed_code, icd10_codes):
                        confidence = data.get("confidence", "medium")
                        logger.info(
                            f"Diagnose {i}: ICD-10-Code '{proposed_code_cleaned}' gefunden "
                            f"(confidence={confidence}, reasoning={data.get('reasoning', 'N/A')})"
                        )
                        new_results.append(
                            ExtractionResult(
                                field_name=icd10_field,
                                value=proposed_code_cleaned,
                                confidence=confidence,
                            )
                        )
                    else:
                        logger.warning(
                            f"Diagnose {i}: Vorgeschlagener Code '{proposed_code}' "
                            "nicht in ICD-10-Datenbank gefunden"
                        )
                else:
                    logger.info(f"Diagnose {i}: Kein passender ICD-10-Code gefunden")

            except Exception as e:
                logger.error(f"Diagnose {i}: Fehler bei ICD-10-Validierung: {e}")

    return new_results


def _clean_icd10_results(results: list[ExtractionResult]) -> list[ExtractionResult]:
    """
    Post-Processing: Bereinigt ICD-10-Codes von Seitenlokalisations-Suffixen.
    Betrifft Felder: VERS_DIAGNOSESCH_1 bis VERS_DIAGNOSESCH_4
    """
    icd10_fields = {f"VERS_DIAGNOSESCH_{i}" for i in range(1, 5)}

    cleaned_results = []
    for result in results:
        if result.field_name in icd10_fields and result.value:
            cleaned_value = _strip_icd10_suffix(result.value)
            if cleaned_value != result.value:
                logger.info(f"ICD-10-Code bereinigt: '{result.value}' -> '{cleaned_value}'")
            cleaned_results.append(
                ExtractionResult(
                    field_name=result.field_name,
                    value=cleaned_value,
                    confidence=result.confidence,
                )
            )
        else:
            cleaned_results.append(result)

    return cleaned_results


def extract_fields(
    fields: list[FormField],
    source_text: str,
) -> list[ExtractionResult]:
    """
    Multi-Pass-Extraktion (optimiert für große Textfelder):
      Pass 1: Kleine Textfelder + Diagnosen (ohne große Textfelder)
      Pass 2: Große narrative Textfelder (ANAMNESE, FUNKTIONSEINSCHRAENKUNGEN, etc.)
      Pass 3: Checkboxen extrahieren
      Pass 4 (optional): Nicht gefundene kleine Textfelder nochmal versuchen
      Pass 5 (optional): ICD-10-Validierung für Diagnosen 1-4
      Post-Processing: ICD-10-Codes bereinigen
    """
    all_results: list[ExtractionResult] = []

    # Textfelder aufteilen: kleine vs. große
    text_fields = [f for f in fields if f.field_type == FieldType.TEXT and f.extract_from_ai]
    small_text_fields = [f for f in text_fields if f.field_name not in LARGE_TEXT_FIELDS]
    large_text_fields = [f for f in text_fields if f.field_name in LARGE_TEXT_FIELDS]

    # --- Pass 1: Kleine Textfelder (schnelle Extraktion) ---
    if small_text_fields:
        logger.info(f"Pass 1: Extrahiere {len(small_text_fields)} kleine Textfelder...")
        prompt = _build_text_fields_prompt(small_text_fields, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt)
            results = _parse_response(response, "fields")
            all_results.extend(results)
            logger.info(f"Pass 1: {len(results)} kleine Textfelder extrahiert")
        except Exception as e:
            logger.error(f"Pass 1 fehlgeschlagen: {e}")

    # --- Pass 2: Große Textfelder (narrative Abschnitte) ---
    if large_text_fields:
        logger.info(f"Pass 2: Extrahiere {len(large_text_fields)} große Textfelder...")
        prompt = _build_large_text_fields_prompt(large_text_fields, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt)
            results = _parse_response(response, "fields")
            all_results.extend(results)
            logger.info(f"Pass 2: {len(results)} große Textfelder extrahiert")
        except Exception as e:
            logger.error(f"Pass 2 fehlgeschlagen: {e}")

    # --- Pass 3: Checkboxen ---
    checkbox_fields = [f for f in fields if f.field_type == FieldType.CHECKBOX and f.extract_from_ai]
    if checkbox_fields:
        logger.info(f"Pass 3: Extrahiere {len(checkbox_fields)} Checkboxen...")
        prompt = _build_checkbox_prompt(checkbox_fields, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt)
            results = _parse_response(response, "checkboxes")
            all_results.extend(results)
            logger.info(f"Pass 3: {len(results)} Checkboxen extrahiert")
        except Exception as e:
            logger.error(f"Pass 3 fehlgeschlagen: {e}")

    # --- Pass 4: Retry für nicht gefundene kleine Textfelder ---
    filled_names = {r.field_name for r in all_results}
    unfilled_small_text = [f for f in small_text_fields if f.field_name not in filled_names]

    if unfilled_small_text and len(unfilled_small_text) < len(small_text_fields):
        logger.info(
            f"Pass 4: Versuche {len(unfilled_small_text)} nicht gefundene kleine Felder erneut..."
        )
        prompt = _build_retry_prompt(unfilled_small_text, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt)
            results = _parse_response(response, "fields")
            all_results.extend(results)
            logger.info(f"Pass 4: {len(results)} zusaetzliche Felder extrahiert")
        except Exception as e:
            logger.error(f"Pass 4 fehlgeschlagen: {e}")

    # --- Pass 5: ICD-10-Validierung für Diagnosen ---
    logger.info("Pass 5: ICD-10-Validierung für Diagnosen 1-4...")
    try:
        icd10_results = _validate_diagnoses_icd10(all_results)
        if icd10_results:
            # Entferne alte ICD-10-Einträge für die validierten Diagnosen
            validated_fields = {r.field_name for r in icd10_results}
            all_results = [r for r in all_results if r.field_name not in validated_fields]
            all_results.extend(icd10_results)
            logger.info(f"Pass 5: {len(icd10_results)} ICD-10-Codes validiert/ergänzt")
        else:
            logger.info("Pass 5: Keine ICD-10-Codes ergänzt")
    except Exception as e:
        logger.error(f"Pass 5 fehlgeschlagen: {e}")

    # --- Post-Processing: ICD-10-Codes bereinigen ---
    logger.info("Post-Processing: Bereinige ICD-10-Codes von Seitenlokalisations-Suffixen...")
    all_results = _clean_icd10_results(all_results)

    logger.info(f"Extraktion abgeschlossen: {len(all_results)} Felder insgesamt")
    return all_results


def _parse_response(raw: str, key: str) -> list[ExtractionResult]:
    """JSON-Antwort von Ollama parsen, mit Fallback-Logik."""
    cleaned = raw.strip()

    # Zuerst versuchen, Code-Blöcke zu extrahieren (auch wenn sie nicht am Anfang stehen)
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if code_block_match:
        cleaned = code_block_match.group(1).strip()
    # Fallback: Markdown Code-Bloecke am Anfang entfernen
    elif cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    data = None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Versuche, JSON aus der Antwort zu extrahieren (entfernt Preamble-Text)
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
