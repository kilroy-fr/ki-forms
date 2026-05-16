import json
import logging
import re

from app.models.form_schema import FormField, FieldType, ExtractionResult
from app.config import settings
from app.services.ollama_client import chat_completion, unload_all_models

logger = logging.getLogger(__name__)

# Große Textfelder werden einzeln extrahiert (je ein Pass pro Feld),
# damit das Output-Token-Budget nie erschöpft wird
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

ANAMNESE (= "Antragsrelevante Anamnese einschliesslich Krankenhausaufenthalte und Berichte von anderen Fachärzten"):
- Krankheitsverlauf: chronologisch, Beginn und Entwicklung der Erkrankung mit Jahreszahl/Datum
- Stationaere Aufenthalte: Klinik, Aufnahme- und Entlassdatum, Diagnose, wesentliche Behandlung
- Berichte anderer Fachärzte: Fachrichtung, Befunddatum, wesentlicher Befund (aus Arztbriefen, Konsilberichten, Überweisungsberichten, Entlassungsbriefen anderer Ärzte)
- Bisherige ambulante Behandlungen und deren Ergebnis
- Nur Informationen, die tatsaechlich im Quelltext stehen (direkt oder als Zusammenfassung aus Fremdberichten)

FUNKTIONSEINSCHRAENKUNGEN:
- Fokus auf WAS der Patient NICHT MEHR KANN, nicht nur auf die Diagnose
- Konkrete koerperliche Einschraenkungen: Gehstrecke, Hebe-/Tragevermögen, Sitzdauer
- Psychische Einschraenkungen: Konzentration, Antrieb, emotionale Belastbarkeit
- Einschraenkungen im Beruf und Alltag mit konkreten Beispielen
- Nicht "Bandscheibenvorfall" sondern "schmerzhafte Bewegungseinschraenkung der LWS mit muskulaerer Schwaeche"

THERAPIE:
- Art, Umfang und Anzahl der Physio- und Psychotherapiesitzungen
- Aktuelle Medikamente mit exakter Dosierung und Einnahmedauer
- Alle Maßnahmen bezogen auf die antragsbegründenden Diagnosen

UNTERSUCHUNGSBEFUNDE:
- Klinische Befunde zur antragsbegründenden Diagnose (psychisch, orthopaedisch, kardiologisch)
- Fachspezifische Befunderhebung je nach Erkrankung

MEDIZINISCH-TECHNISCHE BEFUNDE:
- Laborwerte mit relevanten Parametern
- Bildgebende Befunde (Roentgen, CT, MRT) mit Datum und Ergebnis
- EKG, Lungenfunktion, Sonographie und andere apparative Befunde

KONTEXTFAKTOREN:
- Familiaere Belastungen: Konflikte, Trauerfaelle, Pflegeverantwortung
- Finanzielle Schwierigkeiten (Schulden), Arbeitsplatzprobleme
- Erziehungsverantwortung, besondere Taetigkeitsfaktoren am Arbeitsplatz

BESONDERHEITEN:
- Onkologie: Primaertherapie-Status, Chemotherapie-Schema
- Abhaengigkeitserkrankungen: Suchtberatung, Substitutionsbehandlung
- Psychische Erkrankungen: Schweregradeinschaetzung"""


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
    """Prompt für große Textfeld-Extraktion bauen (narrative Abschnitte, ein Feld pro Pass)."""
    field_descriptions = []
    for f in fields:
        if f.field_type == FieldType.TEXT and f.extract_from_ai:
            field_descriptions.append(f'  "{f.field_name}": "{f.description}"')

    fields_block = ",\n".join(field_descriptions)

    return f"""Hier ist der Quelltext aus den hochgeladenen medizinischen Dokumenten:

--- QUELLTEXT BEGINN ---
{source_text}
--- QUELLTEXT ENDE ---

WICHTIG: Du extrahierst jetzt AUSSCHLIESSLICH den folgenden narrativen Textabschnitt.
Der Text muss in ein PDF-Formularfeld passen - fasse pragnant zusammen.

Extrahiere und fasse zusammen:

FELD:
{{
{fields_block}
}}

EXTRAKTIONSREGELN:
1. Fasse praegnant zusammen - max. 800 Zeichen insgesamt, kein wörtlicher Auszug
2. Kurze Aussagen, je eine pro Zeile (keine Aufzaehlungszeichen wie - oder *)
3. Nur die medizinisch wesentlichen Fakten, keine vollstaendigen Sätze
4. Bei mehreren relevanten Stellen im Quelltext: Kombiniere das Wesentliche
5. Wenn der gesuchte Inhalt nicht im Text vorkommt, lasse das Feld komplett weg
6. Der "field_name" in der Antwort MUSS exakt dem Feldnamen in der Anfrage entsprechen

Antworte im folgenden JSON-Format (NUR das JSON, kein anderer Text oder Code-Block):
{{
  "fields": [
    {{
      "field_name": "FELDNAME",
      "value": "pragnante Zusammenfassung (max. 800 Zeichen)",
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


def extract_fields(
    fields: list[FormField],
    source_text: str,
) -> list[ExtractionResult]:
    """
    Multi-Pass-Extraktion:
      Pass 1: Kleine Textfelder + Diagnosen (ohne große Textfelder)
      Pass 2: Große narrative Textfelder (ANAMNESE, FUNKTIONSEINSCHRAENKUNGEN, etc.)
      Pass 3: Checkboxen extrahieren
      Pass 4 (optional): Nicht gefundene kleine Textfelder nochmal versuchen
    """
    all_results: list[ExtractionResult] = []

    # VRAM komplett freigeben, bevor neues Modell geladen wird
    unload_all_models()

    # Textfelder aufteilen: kleine vs. große
    text_fields = [f for f in fields if f.field_type == FieldType.TEXT and f.extract_from_ai]
    small_text_fields = [f for f in text_fields if f.field_name not in LARGE_TEXT_FIELDS]
    large_text_fields = [f for f in text_fields if f.field_name in LARGE_TEXT_FIELDS]

    # Größerer Context für Pässe mit vollem Quelltext (passt noch vollständig in VRAM)
    large_ctx = settings.OLLAMA_NUM_CTX_LARGE

    # Bei großen Quelltexten kleineres Modell verwenden (passt vollständig in VRAM → 100% GPU)
    text_len = len(source_text)
    if text_len >= settings.LARGE_TEXT_THRESHOLD:
        model = settings.OLLAMA_MODEL_SMALL
        logger.info(
            f"Großer Quelltext ({text_len} Zeichen >= {settings.LARGE_TEXT_THRESHOLD}): "
            f"verwende kleineres Modell {model}"
        )
    else:
        model = None  # Standard-Modell aus Settings
        logger.info(f"Quelltext ({text_len} Zeichen): verwende Standard-Modell {settings.OLLAMA_MODEL}")

    # --- Pass 1: Kleine Textfelder (schnelle Extraktion) ---
    if small_text_fields:
        logger.info(f"Pass 1: Extrahiere {len(small_text_fields)} kleine Textfelder (num_ctx={large_ctx}, model={model or settings.OLLAMA_MODEL})...")
        prompt = _build_text_fields_prompt(small_text_fields, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt, num_ctx=large_ctx, model=model)
            results = _parse_response(response, "fields")
            all_results.extend(results)
            logger.info(f"Pass 1: {len(results)} kleine Textfelder extrahiert")
        except Exception as e:
            logger.error(f"Pass 1 fehlgeschlagen: {e}")

    # --- Pass 2.x: Große Textfelder ---
    # UNTERSUCHUNGSBEFUNDE und MED_TECHN_BEFUNDE werden gemeinsam in einem Call verarbeitet,
    # da sie thematisch zusammengehören und das Output-Budget zusammen nicht erschöpft wird.
    _BEFUND_GROUP = {"UNTERSUCHUNGSBEFUNDE", "MED_TECHN_BEFUNDE"}
    befund_batch = [f for f in large_text_fields if f.field_name in _BEFUND_GROUP]
    single_fields = [f for f in large_text_fields if f.field_name not in _BEFUND_GROUP]

    large_field_batches: list[list] = [[f] for f in single_fields]
    if befund_batch:
        large_field_batches.append(befund_batch)

    for pass_idx, batch in enumerate(large_field_batches, start=1):
        field_names = ", ".join(f.field_name for f in batch)
        logger.info(
            f"Pass 2.{pass_idx} ({field_names}): Extrahiere {len(batch)} Textfeld(er) "
            f"(num_ctx={large_ctx}, model={model or settings.OLLAMA_MODEL})..."
        )
        prompt = _build_large_text_fields_prompt(batch, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt, num_ctx=large_ctx, model=model, num_predict=8192)
            logger.debug(f"Pass 2.{pass_idx} ({field_names}) Raw-Antwort ({len(response)} Zeichen): {response[:500]}")
            results = _parse_response(response, "fields")
            all_results.extend(results)
            logger.info(f"Pass 2.{pass_idx} ({field_names}): {len(results)} Felder extrahiert")
        except Exception as e:
            logger.error(f"Pass 2.{pass_idx} ({field_names}) fehlgeschlagen: {e}")

    # --- Pass 3: Checkboxen ---
    checkbox_fields = [f for f in fields if f.field_type == FieldType.CHECKBOX and f.extract_from_ai]
    if checkbox_fields:
        logger.info(f"Pass 3: Extrahiere {len(checkbox_fields)} Checkboxen (num_ctx={large_ctx}, model={model or settings.OLLAMA_MODEL})...")
        prompt = _build_checkbox_prompt(checkbox_fields, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt, num_ctx=large_ctx, model=model)
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
            f"Pass 4: Versuche {len(unfilled_small_text)} nicht gefundene kleine Felder erneut (num_ctx={large_ctx}, model={model or settings.OLLAMA_MODEL})..."
        )
        prompt = _build_retry_prompt(unfilled_small_text, source_text)
        try:
            response = chat_completion(SYSTEM_PROMPT, prompt, num_ctx=large_ctx, model=model)
            results = _parse_response(response, "fields")
            all_results.extend(results)
            logger.info(f"Pass 4: {len(results)} zusaetzliche Felder extrahiert")
        except Exception as e:
            logger.error(f"Pass 4 fehlgeschlagen: {e}")

    logger.info(f"Extraktion abgeschlossen: {len(all_results)} Felder insgesamt")
    return all_results


def _strip_json_comments(json_str: str) -> str:
    """Entfernt // und /* */ Kommentare aus JSON-ähnlichem Text (zeichengenau, string-sicher)."""
    result = []
    i = 0
    in_string = False
    while i < len(json_str):
        char = json_str[i]
        # Toggle string-Modus bei nicht-escaptem Anführungszeichen
        if char == '"' and (i == 0 or json_str[i - 1] != '\\'):
            in_string = not in_string
        if not in_string and char == '/' and i + 1 < len(json_str):
            next_char = json_str[i + 1]
            # // Zeilenkommentar: bis Zeilenende überspringen
            if next_char == '/':
                while i < len(json_str) and json_str[i] != '\n':
                    i += 1
                continue
            # /* */ Block-Kommentar: bis */ überspringen
            if next_char == '*':
                i += 2
                while i < len(json_str) - 1:
                    if json_str[i] == '*' and json_str[i + 1] == '/':
                        i += 2
                        break
                    i += 1
                continue
        result.append(char)
        i += 1
    return ''.join(result)


def _fix_invalid_escapes(json_str: str) -> str:
    """Repariert ungültige Escape-Sequenzen in JSON-Strings (z.B. \\1 → 1)."""
    # Innerhalb von JSON-Strings: ersetze \X durch X, wenn X kein gültiges Escape-Zeichen ist
    # Gültige JSON-Escapes: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
    valid_escapes = set('"\\\\/bfnrtu')

    result = []
    i = 0
    in_string = False
    while i < len(json_str):
        char = json_str[i]
        if char == '"' and (i == 0 or json_str[i - 1] != '\\'):
            in_string = not in_string
        if in_string and char == '\\' and i + 1 < len(json_str):
            next_char = json_str[i + 1]
            if next_char not in valid_escapes:
                # Ungültiges Escape: Backslash entfernen
                i += 1
                continue
        result.append(char)
        i += 1
    return ''.join(result)


def _close_truncated_json(json_str: str) -> str:
    """
    Repariert abgeschnittenes LLM-JSON in einem Durchlauf:
    - Escaped literal Steuerzeichen (\\n, \\r, \\t ...) innerhalb von Strings
    - Schliesst nicht-terminierten String am Ende (fehlendes Anführungszeichen)
    - Schliesst offene { } und [ ] Strukturen am Ende

    Hintergrund: LLMs geben bei langen Werten manchmal JSON aus, dessen
    String-Wert nicht mit " abgeschlossen wird und dem die schliessenden
    Strukturzeichen fehlen. json.loads() schlägt dann mit 'Unterminated string'
    oder 'Kein JSON gefunden' fehl.
    """
    result = []
    in_string = False
    depth_stack: list[str] = []
    i = 0
    while i < len(json_str):
        char = json_str[i]
        if char == '"' and (i == 0 or json_str[i - 1] != '\\'):
            in_string = not in_string
            result.append(char)
        elif in_string:
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif ord(char) < 0x20:
                result.append(f'\\u{ord(char):04x}')
            else:
                result.append(char)
        else:
            if char == '{':
                depth_stack.append('}')
            elif char == '[':
                depth_stack.append(']')
            elif char in ('}', ']'):
                if depth_stack and depth_stack[-1] == char:
                    depth_stack.pop()
            result.append(char)
        i += 1
    if in_string:
        result.append('"')
    for closer in reversed(depth_stack):
        result.append(closer)
    return ''.join(result)


def _repair_json(json_str: str) -> str:
    """Versucht, häufige JSON-Fehler zu reparieren."""
    # Entferne // Kommentare (Modell fügt diese manchmal ein)
    json_str = _strip_json_comments(json_str)

    # Repariere ungültige Escape-Sequenzen (z.B. \1, \l aus OCR-Artefakten)
    json_str = _fix_invalid_escapes(json_str)

    # Escaped Steuerzeichen, schliesst unterminierten Strings und offene Strukturen
    json_str = _close_truncated_json(json_str)

    # Entferne trailing commas vor ] oder }
    json_str = re.sub(r',(\s*[\]}])', r'\1', json_str)

    # Entferne mehrfache Kommas
    json_str = re.sub(r',\s*,', ',', json_str)

    return json_str


def _repair_truncated_json(json_str: str) -> str | None:
    """
    Versucht, abgeschnittenes JSON zu reparieren, indem das letzte
    unvollständige Objekt entfernt und die Struktur geschlossen wird.
    Rettet bereits vollständige Felder aus einer abgeschnittenen Antwort.
    Gibt None zurück, wenn keine Reparatur möglich ist.
    """
    # Finde das letzte vollständig abgeschlossene Objekt im "fields"/"checkboxes"-Array
    # Suche nach dem letzten '},' oder '}' gefolgt von einem weiteren '{' (= nächstes Objekt begonnen)
    # oder dem letzten komplett geschlossenen Objekt vor dem Abbruch

    # Strategie: Finde alle vollständigen {…}-Blöcke mit field_name
    # und baue daraus ein gültiges JSON
    pattern = r'\{[^{}]*"field_name"\s*:\s*"[^"]+"\s*,[^{}]*"value"\s*:\s*(?:"(?:[^"\\]|\\.)*"|"[^"]*)[^{}]*\}'
    matches = list(re.finditer(pattern, json_str, re.DOTALL))
    if not matches:
        return None

    # Bestimme den Key (fields oder checkboxes)
    key_match = re.search(r'"(fields|checkboxes)"\s*:\s*\[', json_str)
    key = key_match.group(1) if key_match else "fields"

    # Validiere jeden Match einzeln und behalte nur gültige
    valid_objects = []
    for m in matches:
        obj_str = m.group()
        # Trailing comma entfernen falls vorhanden
        obj_str = re.sub(r',(\s*\})', r'\1', obj_str)
        try:
            json.loads(obj_str)
            valid_objects.append(obj_str)
        except json.JSONDecodeError:
            continue

    if not valid_objects:
        return None

    repaired = '{"' + key + '": [' + ', '.join(valid_objects) + ']}'
    logger.info(f"Abgeschnittenes JSON repariert: {len(valid_objects)} vollständige Felder gerettet")
    return repaired


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

    # JSON-Reparatur versuchen
    cleaned = _repair_json(cleaned)

    data = None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"Erster JSON-Parse-Versuch fehlgeschlagen, versuche Extraktion...")
        # Versuche, JSON aus der Antwort zu extrahieren (entfernt Preamble-Text)
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            extracted = match.group()
            # Nochmal Reparatur versuchen auf extrahiertem JSON
            extracted = _repair_json(extracted)
            try:
                data = json.loads(extracted)
                logger.info("JSON erfolgreich nach Extraktion und Reparatur geparst")
            except json.JSONDecodeError as e2:
                # Letzter Versuch: abgeschnittenes JSON reparieren
                repaired = _repair_truncated_json(cleaned)
                if repaired:
                    try:
                        data = json.loads(repaired)
                    except json.JSONDecodeError:
                        pass
                if data is None:
                    logger.error(f"JSON-Parsing fehlgeschlagen bei Position {e2.pos}: {e2.msg}")
                    logger.error(f"Kontext um Fehlerposition: ...{extracted[max(0, e2.pos-100):e2.pos+100]}...")
                    logger.error(f"Vollständige Antwort ({len(raw)} Zeichen): {raw}")
                    return []
        else:
            # Kein JSON-Block gefunden — versuche abgeschnittenes JSON zu reparieren
            repaired = _repair_truncated_json(cleaned)
            if repaired:
                try:
                    data = json.loads(repaired)
                except json.JSONDecodeError:
                    pass
            if data is None:
                logger.error(f"Kein JSON in Ollama-Antwort gefunden: {raw}")
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
