import json
import logging
import re

from app.models.form_schema import FormField, FieldType, ExtractionResult
from app.config import settings
from app.services.ollama_client import chat_completion, unload_all_models
from app.services import icd_catalog

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

# Fallback-Zeichenbudget, wenn ein Feld kein max_chars in der Definition hat
_DEFAULT_FIELD_CHARS = 700

# Obergrenze für das Limit, das dem Modell im Prompt genannt wird.
#
# max_chars ist die KAPAZITAET des PDF-Widgets, nicht die sinnvolle Textlaenge.
# LEBENSUMSTAENDE fasst z.B. 2700 Zeichen, der reale Inhalt eines Arztbriefs
# dazu sind aber 300-500. Nennt man dem Modell die 2700, liest es die Zahl als
# Zielvorgabe und fuellt mit umformulierten Dubletten auf, bis das Budget voll
# ist. Deshalb wird das im Prompt genannte Limit hier gedeckelt; max_chars
# bleibt als harte PDF-Grenze in _enforce_char_limits erhalten.
_PROMPT_CHAR_CAP = 1200


def _prompt_budget(field: FormField) -> int:
    """Zeichenlimit, das dem Modell fuer ein Feld genannt wird."""
    return min(field.max_chars or _DEFAULT_FIELD_CHARS, _PROMPT_CHAR_CAP)

_SYSTEM_BASE = """\
Du bist ein medizinischer Dokumentationsassistent. Deine Aufgabe ist es, aus \
medizinischen Quelldokumenten (Arztbriefe, Befundberichte, Entlassungsbriefe etc.) \
die relevanten Informationen zu extrahieren und den Feldern eines Formulars der \
Deutschen Rentenversicherung (Befundbericht S0051) zuzuordnen.

Der Bericht wird vom Sozialmedizinischen Dienst gelesen. Schreibe deshalb in \
knappem, sachlichem aerztlichem Befundstil - kurze vollstaendige Saetze, keine \
Stichwortfragmente und keine Aufzaehlungszeichen.

WICHTIGE REGELN:
1. Extrahiere NUR Informationen, die TATSAECHLICH im Quelltext vorhanden sind.
2. Erfinde NIEMALS Informationen. Wenn eine Information nicht im Text steht, lasse das Feld weg.
3. Fuer Datumsfelder verwende das Format TT.MM.JJJJ.
4. Fuer Checkboxen antworte mit "ja" oder "nein".
5. Fuer ICD-10-Codes gib den exakten Code an (z.B. M54.5).
6. Bei Unsicherheit setze confidence auf "low" statt zu raten.
7. Extrahiere NUR die im User-Prompt aufgelisteten Felder. Ignoriere alle anderen Informationen."""

# Feldspezifische Hinweise. Werden pro Pass nur fuer die tatsaechlich angefragten
# Felder in den System-Prompt gemischt - sonst blutet Inhalt zwischen den Feldern
# durch (z.B. Funktionseinschraenkungen, die in der Anamnese landen).
FIELD_GUIDANCE: dict[str, str] = {
    "DIAGNOSEN": """\
DIAGNOSEN:
- Fokussiere auf FUNKTIONSEINSCHRAENKUNGEN, nicht nur die Diagnose selbst
- Beispiel: Statt "Bandscheibenvorfall" -> "schmerzhafte Bewegungseinschraenkung der LWS mit Schwaeche"
- Primaere rehabilitationsbegrundende Diagnose an erster Stelle""",

    "ANAMNESE": """\
ANAMNESE (= "Antragsrelevante Anamnese einschliesslich Krankenhausaufenthalte und Berichte von anderen Fachärzten"):
- Krankheitsverlauf: chronologisch, Beginn und Entwicklung der Erkrankung mit Jahreszahl/Datum
- Stationaere Aufenthalte: Klinik, Aufnahme- und Entlassdatum, Diagnose, wesentliche Behandlung
- Berichte anderer Fachärzte: Fachrichtung, Befunddatum, wesentlicher Befund (aus Arztbriefen, Konsilberichten, Überweisungsberichten, Entlassungsbriefen anderer Ärzte)
- Bisherige ambulante Behandlungen und deren Ergebnis
- KEINE Funktionseinschraenkungen und KEINE Therapiedetails - die gehoeren in eigene Felder""",

    "FUNKTIONSEINSCHRAENKUNGEN": """\
FUNKTIONSEINSCHRAENKUNGEN:
- Fokus auf WAS der Patient NICHT MEHR KANN, nicht auf die Diagnose
- Konkrete koerperliche Einschraenkungen: Gehstrecke, Hebe-/Tragevermögen, Sitzdauer
- Psychische Einschraenkungen: Konzentration, Antrieb, emotionale Belastbarkeit
- Einschraenkungen im Beruf und Alltag mit konkreten Beispielen
- Nicht "Bandscheibenvorfall" sondern "schmerzhafte Bewegungseinschraenkung der LWS mit muskulaerer Schwaeche"
- KEINE Krankheitsgeschichte - die gehoert in die Anamnese""",

    "THERAPIE": """\
THERAPIE:
- Art, Umfang und Anzahl der Physio- und Psychotherapiesitzungen
- Aktuelle Medikamente NUR mit Wirkstoff- oder Handelsnamen, ohne Dosierung und
  ohne Einnahmeschema (Dosierungen werden aus dem Quelltext regelmaessig
  verdreht uebernommen und gehoeren nicht in dieses Formular)
- Alle Maßnahmen bezogen auf die antragsbegründenden Diagnosen
- Bei Abhaengigkeitserkrankungen: Suchtberatung, Substitutionsbehandlung
- Bei Onkologie: Primaertherapie-Status, Chemotherapie-Schema""",

    "UNTERSUCHUNGSBEFUNDE": """\
UNTERSUCHUNGSBEFUNDE:
- Klinische Befunde zur antragsbegründenden Diagnose (psychisch, orthopaedisch, kardiologisch)
- Fachspezifische Befunderhebung je nach Erkrankung
- Auch knappe Beobachtungen zaehlen ("Reflexe seitengleich", "psychisch stabil")
- Nur selbst erhobene klinische Befunde, KEINE Geraete- oder Laborwerte""",

    "MED_TECHN_BEFUNDE": """\
MEDIZINISCH-TECHNISCHE BEFUNDE:
- Laborwerte mit relevanten Parametern
- Bildgebende Befunde (Roentgen, CT, MRT) mit Datum und Ergebnis
- EKG, Lungenfunktion, Sonographie und andere apparative Befunde
- Nur apparativ/laborchemisch Erhobenes, KEINE klinische Untersuchung""",

    "LEBENSUMSTAENDE": """\
KONTEXTFAKTOREN / LEBENSUMSTAENDE:
- Familiaere Belastungen: Konflikte, Trauerfaelle, Pflegeverantwortung
- Finanzielle Schwierigkeiten (Schulden), Arbeitsplatzprobleme
- Erziehungsverantwortung, besondere Taetigkeitsfaktoren am Arbeitsplatz
- Soziales Umfeld und Wohnsituation, soweit im Quelltext beschrieben""",
}

# Vollstaendiger System-Prompt (alle Hinweise) fuer Paesse, die viele
# unterschiedliche Felder auf einmal abfragen (Pass 1, 3 und 4).
SYSTEM_PROMPT = _SYSTEM_BASE + "\n\nHINWEISE ZUR EXTRAKTION:\n\n" + "\n\n".join(
    FIELD_GUIDANCE.values()
)

# Vorschaltfrage je narrativem Feld: "Steht dazu ueberhaupt etwas im Quelltext?"
#
# Notwendig, weil weder die Prompt-Regeln noch die Belegpflicht Erfindungen
# verhindern: das Modell zitiert dann einfach einen beliebigen echten Satz und
# leitet daraus Inhalt ab, der nirgends steht. Im Test an einem echten
# Entlassungsbrief hat der Gate genau die beiden erfundenen Felder erkannt
# (FUNKTIONSEINSCHRAENKUNGEN, LEBENSUMSTAENDE), an denen die Belegpruefung
# vorbeilief. Die Frageformulierung ist gegen diesen Brief validiert -
# Aenderungen bitte erneut gegen echte Dokumente pruefen.
GATE_QUESTIONS: dict[str, str] = {
    "ANAMNESE": (
        "Angaben zum Krankheitsverlauf, zu stationaeren Aufenthalten oder zu "
        "Berichten anderer Fachaerzte"
    ),
    "FUNKTIONSEINSCHRAENKUNGEN": (
        "Angaben dazu, was die Patientin oder der Patient krankheitsbedingt "
        "koerperlich oder psychisch NICHT MEHR KANN (Gehstrecke, Heben, "
        "Sitzdauer, Konzentration, Selbstversorgung)"
    ),
    "THERAPIE": (
        "Angaben zu Behandlungen, Operationen, Medikamenten oder Physiotherapie"
    ),
    "UNTERSUCHUNGSBEFUNDE": (
        "selbst erhobene klinische Untersuchungsbefunde (Inspektion, Tastbefund, "
        "Reflexe, psychischer Befund)"
    ),
    "MED_TECHN_BEFUNDE": (
        "Laborwerte oder apparative Befunde wie Roentgen, CT, MRT, EKG"
    ),
    "LEBENSUMSTAENDE": (
        "Angaben zu familiaeren Belastungen, Erziehungsverantwortung, finanziellen "
        "Schwierigkeiten, Arbeitsplatzproblemen oder Wohnsituation"
    ),
}

_GATE_SYSTEM = (
    "Du pruefst, ob ein medizinischer Quelltext eine bestimmte Art von Information "
    "enthaelt. Antworte ausschliesslich mit JA oder NEIN. Antworte NEIN, wenn die "
    "Information nur erschlossen oder vermutet werden koennte, aber nicht "
    "ausdruecklich im Text steht."
)

_GATE_SCHEMA = {
    "type": "object",
    "properties": {"antwort": {"type": "string", "enum": ["JA", "NEIN"]}},
    "required": ["antwort"],
}


def _build_system_prompt(field_names: list[str]) -> str:
    """System-Prompt nur mit den Hinweisen der angefragten Felder."""
    parts = [FIELD_GUIDANCE[n] for n in field_names if n in FIELD_GUIDANCE]
    if not parts:
        return _SYSTEM_BASE
    return _SYSTEM_BASE + "\n\nHINWEISE ZUR EXTRAKTION:\n\n" + "\n\n".join(parts)


def _build_response_schema(
    key: str,
    allowed_field_names: list[str],
    require_beleg: bool = False,
) -> dict:
    """
    JSON-Schema fuer Ollamas "format"-Parameter.

    Der Enum auf field_name garantiert, dass das Modell keine erfundenen oder
    verstuemmelten Feldnamen zurueckgibt - das musste vorher per Prompt-Regel
    erbeten werden und schlug regelmaessig fehl.

    require_beleg erzwingt zusaetzlich ein woertliches Quelltextzitat pro Feld.
    Das Zitat wird anschliessend in _verify_grounding gegen den Quelltext
    geprueft - dadurch wandert die Halluzinationspruefung vom Modell (das sein
    eigenes Werk begutachten wuerde) in deterministischen Code.
    """
    properties = {
        "field_name": {"type": "string", "enum": allowed_field_names},
        "value": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    }
    required = ["field_name", "value", "confidence"]

    if require_beleg:
        properties["beleg"] = {"type": "string"}
        required.append("beleg")

    return {
        "type": "object",
        "properties": {
            key: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        },
        "required": [key],
    }


def _num_predict_for(fields: list[FormField], with_beleg: bool = False) -> int:
    """
    Output-Budget aus dem Zeichenlimit der Felder ableiten.

    Wichtig, weil num_ctx das GESAMTfenster ist: jedes Token, das hier reserviert
    wird, fehlt dem Quelltext. Deutsch liegt bei grob 3 Zeichen pro Token, mit
    2 wird konservativ gerechnet; dazu JSON-Overhead pro Feld.

    with_beleg reserviert zusaetzlich Platz fuer das woertliche Quelltextzitat.
    Ohne diesen Zuschlag wuerde das Zitat das Budget des eigentlichen Werts
    aufzehren und die Antwort mitten im Satz abbrechen.
    """
    budget = sum(_prompt_budget(f) for f in fields)
    per_field = 128 + (192 if with_beleg else 0)
    return int(budget / 2) + per_field * len(fields) + 256


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


_LARGE_TEXT_EXAMPLE = """\
Beispiel fuer den erwarteten Stil (Feld ANAMNESE, gekuerzt):
"Seit 2019 zunehmende Lumboischialgie rechts mit Ausstrahlung in das rechte Bein. \
Stationaere Behandlung im Klinikum Ansbach vom 02.03.2021 bis 11.03.2021 bei \
Bandscheibenvorfall L4/L5, konservative Therapie mit Analgesie und Krankengymnastik. \
Der orthopaedische Befundbericht von Dr. Mueller vom 14.06.2023 beschreibt eine \
persistierende Schmerzsymptomatik. Ambulante Physiotherapie 2022 und 2023 ohne \
anhaltende Besserung."\
"""


def _build_large_text_fields_prompt(
    fields: list[FormField],
    source_text: str,
) -> str:
    """
    Prompt für große Textfeld-Extraktion bauen (narrative Abschnitte).

    Das Zeichenlimit kommt pro Feld aus FormField.max_chars und entspricht der
    tatsaechlichen Kapazitaet des PDF-Widgets. Frueher galt hier pauschal
    "800 Zeichen insgesamt" - das war fuer UNTERSUCHUNGSBEFUNDE zu viel, fuer
    LEBENSUMSTAENDE um ein Vielfaches zu wenig, und bei zwei Feldern im selben
    Pass teilten sich beide das Budget.
    """
    field_descriptions = []
    for f in fields:
        if f.field_type == FieldType.TEXT and f.extract_from_ai:
            field_descriptions.append(
                f'  "{f.field_name}" (max. {_prompt_budget(f)} Zeichen): "{f.description}"'
            )

    fields_block = "\n".join(field_descriptions)
    is_multi = len(field_descriptions) > 1
    scope_hint = (
        "Die Felder sind inhaltlich streng zu trennen - ordne jede Information "
        "genau einem Feld zu."
        if is_multi
        else "Du bearbeitest ausschliesslich dieses eine Feld."
    )

    return f"""Hier ist der Quelltext aus den hochgeladenen medizinischen Dokumenten:

--- QUELLTEXT BEGINN ---
{source_text}
--- QUELLTEXT ENDE ---

Erstelle den Inhalt fuer die folgenden Formularfelder des Befundberichts.
{scope_hint}

FELD(ER):
{fields_block}

EXTRAKTIONSREGELN:
1. Das Zeichenlimit ist eine OBERGRENZE pro Feld, kein Richtwert. Laengerer Text
   wird im PDF ohne Warnung abgeschnitten. Kuerzer ist besser als laenger: hoere
   auf, sobald der Quelltext nichts Neues mehr hergibt.
2. Schreibe jede Information GENAU EINMAL. Wiederhole keine Aussage, auch nicht
   umformuliert, und fuelle nicht auf, um das Limit zu erreichen.
3. Kurze, vollstaendige Saetze im aerztlichen Befundstil. Keine Aufzaehlungszeichen,
   keine Zeilenumbrueche, keine Stichwortfragmente.
4. Konkrete Angaben statt Allgemeinplaetzen: Datum, Klinik, Messwert,
   Fachrichtung - wann immer sie im Quelltext stehen.
5. Medikamente NUR mit Namen nennen, ohne Dosierung, Einnahmeschema oder
   Einnahmedauer. Also "Levofloxacin und Rifampicin", nicht "Levofloxacin
   2 x 500 mg taeglich".
6. Bei mehreren relevanten Stellen im Quelltext: das Wesentliche zusammenfuehren,
   chronologisch geordnet.
7. Wenn der gesuchte Inhalt nicht im Quelltext vorkommt, lasse das Feld komplett weg.
   Erfinde nichts und schreibe keine Platzhalter.
8. Stelle KEINE Zusammenhaenge her, die nicht ausdruecklich im Quelltext stehen.
   Keine Ursachen ("aufgrund von"), keine Folgen, keine Wertungen und keine
   Zeit- oder Ortsangaben ergaenzen, die dort nicht ausdruecklich genannt sind.
9. Belege jedes Feld mit "beleg": ein WOERTLICH aus dem Quelltext kopierter Satz,
   auf den sich dein Wert stuetzt. Kopiere exakt, auch mit Schreibfehlern, und
   formuliere den Beleg NICHT um. Findest du keine Stelle, die du woertlich
   zitieren kannst, steht die Information nicht im Text - lasse das Feld weg.

{_LARGE_TEXT_EXAMPLE}"""


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

    # Bei großen Quelltexten ggf. anderes Modell verwenden.
    # Ist OLLAMA_MODEL_SMALL identisch zu OLLAMA_MODEL, ist der Wechsel abgeschaltet.
    text_len = len(source_text)
    if text_len >= settings.LARGE_TEXT_THRESHOLD and settings.OLLAMA_MODEL_SMALL != settings.OLLAMA_MODEL:
        model = settings.OLLAMA_MODEL_SMALL
        logger.warning(
            f"Großer Quelltext ({text_len} Zeichen >= {settings.LARGE_TEXT_THRESHOLD}): "
            f"wechsle von {settings.OLLAMA_MODEL} auf {model}. Das kostet spürbar "
            f"Qualität bei den narrativen Feldern - OLLAMA_MODEL_SMALL auf denselben "
            f"Wert wie OLLAMA_MODEL setzen, um den Wechsel abzuschalten."
        )
    else:
        model = None  # Standard-Modell aus Settings
        logger.info(f"Quelltext ({text_len} Zeichen): verwende Modell {settings.OLLAMA_MODEL}")

    # --- Pass 1: Kleine Textfelder (schnelle Extraktion) ---
    if small_text_fields:
        logger.info(f"Pass 1: Extrahiere {len(small_text_fields)} kleine Textfelder (num_ctx={large_ctx}, model={model or settings.OLLAMA_MODEL})...")
        prompt = _build_text_fields_prompt(small_text_fields, source_text)
        try:
            response = chat_completion(
                SYSTEM_PROMPT,
                prompt,
                num_ctx=large_ctx,
                model=model,
                response_schema=_build_response_schema(
                    "fields", [f.field_name for f in small_text_fields]
                ),
            )
            results = _parse_response(response, "fields")
            all_results.extend(results)
            logger.info(f"Pass 1: {len(results)} kleine Textfelder extrahiert")
        except Exception as e:
            logger.error(f"Pass 1 fehlgeschlagen: {e}")

    # --- Gate: Gibt der Quelltext zu den narrativen Feldern ueberhaupt etwas her? ---
    # Laeuft vor Pass 2, damit der Quelltext danach im Prefix-Cache von Ollama liegt.
    content_gates = _run_content_gates(large_text_fields, source_text, large_ctx, model)

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
        batch_names = [f.field_name for f in batch]
        field_names = ", ".join(batch_names)
        num_predict = _num_predict_for(batch, with_beleg=True)
        logger.info(
            f"Pass 2.{pass_idx} ({field_names}): Extrahiere {len(batch)} Textfeld(er) "
            f"(num_ctx={large_ctx}, num_predict={num_predict}, model={model or settings.OLLAMA_MODEL})..."
        )
        prompt = _build_large_text_fields_prompt(batch, source_text)
        try:
            response = chat_completion(
                _build_system_prompt(batch_names),
                prompt,
                # Etwas Temperatur und eine erhöhte Wiederholungsstrafe: bei 0.0
                # produziert das Modell auf den langen Feldern Dubletten, bis das
                # Zeichenbudget voll ist, statt aufzuhören.
                temperature=0.2,
                num_ctx=large_ctx,
                model=model,
                num_predict=num_predict,
                response_schema=_build_response_schema(
                    "fields", batch_names, require_beleg=True
                ),
                # 1.15 statt hoeher: ab ca. 1.25 bestraft das Modell auch legitime
                # Wortbestandteile und erzeugt Wortverstuemmelungen wie
                # "Immobilienkahrs" statt "Immobilienkredits".
                repeat_penalty=1.15,
            )
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
            response = chat_completion(
                SYSTEM_PROMPT,
                prompt,
                num_ctx=large_ctx,
                model=model,
                response_schema=_build_response_schema(
                    "checkboxes", [f.field_name for f in checkbox_fields]
                ),
            )
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
            response = chat_completion(
                SYSTEM_PROMPT,
                prompt,
                num_ctx=large_ctx,
                model=model,
                response_schema=_build_response_schema(
                    "fields", [f.field_name for f in unfilled_small_text]
                ),
            )
            results = _parse_response(response, "fields")
            all_results.extend(results)
            logger.info(f"Pass 4: {len(results)} zusaetzliche Felder extrahiert")
        except Exception as e:
            logger.error(f"Pass 4 fehlgeschlagen: {e}")

    # Dedup NUR auf den narrativen Feldern: nur dort laeuft das Modell in
    # Wiederholungsschleifen. Auf kurzen Feldern richtet die Satzlogik dagegen
    # Schaden an - "Overmans, Dr. med. Gertrud" ist kein Satzpaar, und der
    # Vorname waere als angefangener Schlusssatz verworfen worden.
    for r in all_results:
        if r.field_name in LARGE_TEXT_FIELDS:
            r.value = _deduplicate_sentences(r.field_name, r.value)
    _enforce_char_limits(all_results, fields)
    _verify_grounding(all_results, source_text)
    # Nach der Belegpruefung: der Gate ist das staerkere Signal. Ein Beleg kann
    # echt sein und den Wert trotzdem nicht stuetzen - dann soll das Ergebnis
    # des Gates gelten und nicht durch eine bestandene Belegpruefung ueberdeckt
    # werden.
    _apply_content_gates(all_results, content_gates)
    all_results = _validate_icd_codes(all_results)

    logger.info(f"Extraktion abgeschlossen: {len(all_results)} Felder insgesamt")
    return all_results


# Laenge der Wortketten, mit denen ein Beleg im Quelltext gesucht wird.
# 4 Woerter sind lang genug, dass zufaellige Uebereinstimmungen unwahrscheinlich
# werden, und kurz genug, dass ein einzelner OCR-Fehler nicht den ganzen Beleg
# entwertet - er zerstoert nur die vier Ketten, die ueber ihn laufen.
_SHINGLE_SIZE = 4
# Anteil der Wortketten eines Belegs, die im Quelltext vorkommen muessen.
# Bewusst niedrig: der OCR-Text ist fehlerhaft ("reizIose" statt "reizlose",
# "D&bridement" statt "Debridement"), ein korrektes Zitat erreicht deshalb nie
# 100%. Erfundene Saetze liegen dagegen typischerweise nahe null.
_GROUNDING_THRESHOLD = 0.45


def _run_content_gates(
    fields: list[FormField],
    source_text: str,
    num_ctx: int,
    model: str | None,
) -> dict[str, bool]:
    """
    Vor der Extraktion pro narrativem Feld fragen, ob der Quelltext dazu
    ueberhaupt etwas hergibt.

    Liefert {feldname: True/False}. Felder ohne Eintrag gelten als ungeprueft -
    faellt ein Aufruf aus, wird das Feld NICHT abgewertet (fail-open), denn ein
    Ollama-Fehler ist kein Hinweis auf eine Erfindung.

    Der Quelltext steht im Prompt bewusst VORNE und identisch fuer alle Fragen:
    dadurch greift der Prefix-Cache von Ollama und die Fragen 2 bis n kosten
    fast nichts (gemessen 2,4 s fuer sechs Felder bei 47 s Gesamtlaufzeit).
    """
    gates: dict[str, bool] = {}

    for field in fields:
        question = GATE_QUESTIONS.get(field.field_name)
        if not question:
            continue

        prompt = (
            f"--- QUELLTEXT BEGINN ---\n{source_text}\n--- QUELLTEXT ENDE ---\n\n"
            f"Enthaelt dieser Quelltext {question}?\n\n"
            f"Antworte nur mit JA oder NEIN."
        )
        try:
            raw = chat_completion(
                _GATE_SYSTEM,
                prompt,
                num_ctx=num_ctx,
                model=model,
                num_predict=16,
                response_schema=_GATE_SCHEMA,
            )
        except Exception as e:
            logger.warning(f"Gate {field.field_name} fehlgeschlagen: {e} - ungeprueft")
            continue

        try:
            answer = json.loads(raw).get("antwort", "").strip().upper()
        except (json.JSONDecodeError, AttributeError):
            logger.warning(
                f"Gate {field.field_name}: unerwartete Antwort {raw[:80]!r} - ungeprueft"
            )
            continue

        if answer not in ("JA", "NEIN"):
            logger.warning(
                f"Gate {field.field_name}: unerwartete Antwort {answer!r} - ungeprueft"
            )
            continue

        gates[field.field_name] = answer == "JA"

    ohne_inhalt = sorted(n for n, hat in gates.items() if not hat)
    logger.info(
        f"Gate: {len(gates)}/{len(fields)} Felder geprueft"
        + (f", ohne Quelltextgrundlage: {', '.join(ohne_inhalt)}" if ohne_inhalt else "")
    )
    return gates


def _apply_content_gates(
    results: list[ExtractionResult],
    gates: dict[str, bool],
) -> None:
    """
    Felder abwerten, zu denen der Gate keine Quelltextgrundlage gesehen hat.

    Bewusst kein Verwerfen: der Gate lag im Test bei 5 von 6 Feldern richtig,
    der eine Fehler war ein faelschliches NEIN auf UNTERSUCHUNGSBEFUNDE. Als
    harter Filter haette er dort einen korrekten Befund geloescht; als
    Konfidenzsignal kostet er nur ein Badge in der Review-UI.
    """
    for r in results:
        if gates.get(r.field_name, True):
            continue
        logger.warning(
            f"{r.field_name}: Quelltext gibt laut Vorabpruefung nichts her, das Modell "
            f"hat trotzdem geliefert - confidence auf low gesetzt"
        )
        r.confidence = "low"


def _normalize_for_matching(text: str) -> list[str]:
    """Text auf vergleichbare Wortliste reduzieren (Umlaute, Satzzeichen, Ziffern egal)."""
    normalized = (text or "").lower().translate(_UMLAUT_MAP)
    return re.findall(r"\w+", normalized)


def _shingles(words: list[str], size: int = _SHINGLE_SIZE) -> set[tuple[str, ...]]:
    """Alle ueberlappenden Wortketten fester Laenge."""
    if len(words) < size:
        return set()
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def _grounding_score(beleg: str, source_words: list[str], source_shingles: set) -> float:
    """
    Anteil des Belegs, der sich im Quelltext wiederfindet (0.0-1.0).

    Bei sehr kurzen Belegen greift die Wortkettenpruefung nicht, dann wird auf
    einen einfachen Wortabgleich zurueckgefallen.
    """
    words = _normalize_for_matching(beleg)
    if not words:
        return 0.0

    beleg_shingles = _shingles(words)
    if not beleg_shingles:
        vocabulary = set(source_words)
        return sum(w in vocabulary for w in words) / len(words)

    return len(beleg_shingles & source_shingles) / len(beleg_shingles)


def _verify_grounding(
    results: list[ExtractionResult],
    source_text: str,
) -> None:
    """
    Belege der narrativen Felder gegen den Quelltext pruefen.

    Das Modell erfindet bei Feldern, zu denen der Quelltext nichts hergibt,
    plausibel klingenden Inhalt und vergibt dafuer auch noch confidence "high" -
    im Test an einem echten Entlassungsbrief betraf das FUNKTIONSEINSCHRAENKUNGEN
    und LEBENSUMSTAENDE, zu denen dort kein Wort steht. Verschaerfte Prompt-Regeln
    haben das nicht verhindert.

    Ein nicht belegbarer Wert wird NICHT verworfen, sondern auf confidence "low"
    gesetzt. Der Inhalt ist medizinisch oft nicht abwegig - er steht nur nicht im
    Dokument. Diese Entscheidung gehoert der Aerztin im Review, nicht dem Code.
    """
    source_words = _normalize_for_matching(source_text)
    source_shingles = _shingles(source_words)

    for r in results:
        if r.field_name not in LARGE_TEXT_FIELDS:
            continue

        if not r.beleg:
            logger.warning(
                f"{r.field_name}: kein Beleg geliefert - confidence auf low gesetzt"
            )
            r.confidence = "low"
            continue

        score = _grounding_score(r.beleg, source_words, source_shingles)
        if score < _GROUNDING_THRESHOLD:
            logger.warning(
                f"{r.field_name}: Beleg nur zu {score:.0%} im Quelltext auffindbar "
                f"(Schwelle {_GROUNDING_THRESHOLD:.0%}) - moeglicherweise erfunden, "
                f"confidence auf low gesetzt. Beleg: {r.beleg[:120]!r}"
            )
            r.confidence = "low"
        else:
            logger.debug(f"{r.field_name}: Beleg zu {score:.0%} gedeckt")


_DIAGNOSE_FIELD = re.compile(r"^VERS_DIAGNOSE_(\d+)$")
_DIAGNOSESCH_FIELD = re.compile(r"^VERS_DIAGNOSESCH_(\d+)$")


def _validate_icd_codes(results: list[ExtractionResult]) -> list[ExtractionResult]:
    """
    ICD-Codes gegen den Katalog pruefen und wo moeglich korrigieren.

    Drei Stufen, je Diagnose-Nummer gegen den zugehoerigen Diagnosetext:
      1. Findet der Katalog zum Diagnosetext einen eindeutigen Code, gilt dieser.
         Der Katalog schlaegt das Modell - "Ehlers-Danlos Syndrom" ist Q79.6,
         egal was das Modell geraten hat.
      2. Existiert der Code des Modells gar nicht im Katalog, wird er verworfen.
         Ein leeres Feld ist besser als ein erfundener Schluessel im DRV-Formular.
      3. Existiert er, wird aber vom Katalogtext nicht gestuetzt, bleibt er mit
         confidence "low" stehen. Bewusst kein Verwerfen: der korrekte T84.5
         heisst im Katalog "Infektion durch eine Gelenkendoprothese" und teilt
         mit "Fruehinfekt der Huefttotalendoprothese" kein einziges Wort - eine
         fehlende Textdeckung beweist also nichts.
    """
    if not icd_catalog.is_available():
        logger.warning("ICD-Katalog nicht verfuegbar - Codes werden ungeprueft uebernommen")
        return results

    diagnosis_texts = {
        m.group(1): r.value
        for r in results
        if (m := _DIAGNOSE_FIELD.match(r.field_name))
    }

    kept: list[ExtractionResult] = []
    for r in results:
        match = _DIAGNOSESCH_FIELD.match(r.field_name)
        if not match:
            kept.append(r)
            continue

        text = diagnosis_texts.get(match.group(1), "")
        original = r.value

        # Stufe 1: Katalog-Nachschlag aus dem Diagnosetext
        hit = icd_catalog.lookup_code(text) if text else None
        if hit:
            if icd_catalog.normalize_code(original) != hit.code:
                logger.warning(
                    f"{r.field_name}: Modell lieferte '{original}', Katalog ergibt "
                    f"{hit.code} ({hit.term}) fuer '{text[:60]}' - korrigiert"
                )
            r.value = hit.code
            r.confidence = "high"
            kept.append(r)
            continue

        # Stufe 2: Code existiert nicht
        if not icd_catalog.is_valid_code(original):
            logger.warning(
                f"{r.field_name}: '{original}' ist kein gueltiger ICD-10-Code "
                f"(Diagnose '{text[:60]}') - Feld bleibt leer"
            )
            continue

        # Stufe 3: gueltig, aber vom Katalogtext nicht gestuetzt
        if not icd_catalog.is_corroborated(text, original):
            logger.warning(
                f"{r.field_name}: '{original}' heisst im Katalog "
                f"'{icd_catalog.official_term(original)}', die Diagnose lautet "
                f"'{text[:60]}' - ungeprueft, confidence auf low gesetzt"
            )
            r.confidence = "low"
        kept.append(r)

    return kept


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
# Abkuerzungen, die im medizinischen Text NIE einen Satz beenden. Nach ihnen darf
# nicht getrennt werden, sonst zerfaellt "Z. n. Primaerimplantation" in zwei
# vermeintliche Saetze. Bewusst ohne "tgl.", "etc." oder "usw." - die stehen
# regelmaessig am Satzende.
_ABBREVIATIONS = frozenset(
    "dr med prof dipl ca ggf evtl inkl exkl sog vgl bzw ehem geb verh "
    "nr abs bspw insb".split()
)
# Letztes Wort vor dem Punkt und dessen Ziffernanteil
_LAST_TOKEN = re.compile(r"([\w.]+)\.$")

# Umlaut-Normalisierung fuer den Aehnlichkeitsvergleich: OCR-Text und Modell
# mischen "Haushaltsführung" und "Haushaltsfuehrung", sonst gelten sie als
# verschiedene Woerter und Dubletten rutschen durch.
_UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
# Fuellwoerter, die beim Aehnlichkeitsvergleich nichts zur Aussage beitragen
_STOPWORDS = frozenset(
    "der die das den dem des ein eine einer eines einem und oder mit bei von "
    "im in am an auf fuer für zur zum seit sowie sind ist bestehen besteht "
    "wegen aufgrund durch als sich es zu la".split()
)


def _ends_with_abbreviation(part: str) -> bool:
    """
    Prueft, ob ein Textstueck auf einer Abkuerzung endet statt auf einem Satzende.

    Drei Faelle, die im Arztbrief staendig vorkommen:
    - bekannte Abkuerzung ("Dr.", "med.", "ca.")
    - einzelner Buchstabe ("Z. n.", "V. a.", "o. d.", "i. v.", "z. B.")
    - ein- bis zweistellige Zahl ("vom 25.09. bis"); vierstellige Jahreszahlen
      sind ausgenommen, weil "... am 30.07.2024." sehr wohl ein Satzende ist
    """
    part = part.rstrip()
    if not part.endswith("."):
        return False

    match = _LAST_TOKEN.search(part)
    if not match:
        return False

    token = match.group(1).rstrip(".").rsplit(".", 1)[-1]
    if not token:
        return False
    if token.lower() in _ABBREVIATIONS:
        return True
    if len(token) == 1 and token.isalpha():
        return True
    return token.isdigit() and len(token) <= 2


def _split_sentences(text: str) -> list[str]:
    """
    Text in Saetze zerlegen, ohne an Abkuerzungen zu trennen.

    Erst grob an jedem Satzzeichen trennen, dann die Teile wieder zusammen-
    fuehren, deren Trennstelle nur eine Abkuerzung war. Im Zweifel wird
    zusammengefuehrt: zwei faelschlich verbundene Saetze kosten nur etwas
    Trennschaerfe bei der Dublettenerkennung, eine faelschlich getrennte
    Abkuerzung dagegen echten Inhalt.
    """
    parts = [p for p in _SENTENCE_SPLIT.split(text or "") if p.strip()]
    if not parts:
        return []

    merged = [parts[0]]
    for part in parts[1:]:
        if _ends_with_abbreviation(merged[-1]):
            merged[-1] = f"{merged[-1].rstrip()} {part.lstrip()}"
        else:
            merged.append(part)
    return [p.strip() for p in merged if p.strip()]


def _deduplicate_sentences(field_name: str, value: str) -> str:
    """
    Entfernt wiederholte und umformulierte Saetze aus einer Antwort.

    Hat ein Feld ein grosses Zeichenbudget, im Quelltext aber wenig Inhalt,
    laufen kleinere Modelle in Wiederholungsschleifen und fuellen mit
    Umformulierungen auf (typisch bei LEBENSUMSTAENDE). Ueber Sampling-Parameter
    ist das nur unzuverlaessig in den Griff zu bekommen - eine hoehere
    repeat_penalty stoppt zwar die Schleife, verstuemmelt dafuer aber Woerter.
    Deshalb hier deterministisch nachbereinigen.
    """
    sentences = _split_sentences(value)
    if len(sentences) < 2:
        return value

    # Angefangenen Schlusssatz verwerfen: entsteht, wenn num_predict die Antwort
    # mitten im Satz abschneidet. Ein Fragment im Formular ist schlechter als ein
    # fehlender Satz.
    dropped_fragment = False
    if len(sentences) > 1 and not sentences[-1].rstrip().endswith((".", "!", "?")):
        sentences = sentences[:-1]
        dropped_fragment = True

    kept: list[str] = []
    kept_tokens: list[frozenset] = []

    for sentence in sentences:
        tokens = frozenset(
            w for w in re.findall(r"\w+", sentence.lower().translate(_UMLAUT_MAP))
            if w not in _STOPWORDS
        )
        if not tokens:
            continue

        # Jaccard-Aehnlichkeit gegen alle bisher behaltenen Saetze
        duplicate = False
        for prev in kept_tokens:
            overlap = len(tokens & prev)
            union = len(tokens | prev)
            if union and overlap / union >= 0.6:
                duplicate = True
                break

        if not duplicate:
            kept.append(sentence)
            kept_tokens.append(tokens)

    if len(kept) == len(sentences) and not dropped_fragment:
        return value

    cleaned = " ".join(kept)
    removed = len(sentences) - len(kept)
    details = f"{removed} Wiederholung(en)" if removed else ""
    if dropped_fragment:
        details = (details + ", " if details else "") + "1 abgeschnittener Satz"
    logger.warning(
        f"{field_name}: {details} entfernt ({len(value)} -> {len(cleaned)} Zeichen)"
    )
    return cleaned


def _enforce_char_limits(
    results: list[ExtractionResult],
    fields: list[FormField],
) -> None:
    """
    Kuerzt zu lange Werte an der Wortgrenze und loggt das.

    Sicherheitsnetz fuer den Fall, dass das Modell das Zeichenlimit ignoriert:
    ohne diese Stelle wuerde erst pdf_filler kuerzen - mitten im Wort und ohne
    jede Meldung, sodass der Verlust niemandem auffaellt.
    """
    limits = {f.field_name: f.max_chars for f in fields if f.max_chars}

    for r in results:
        limit = limits.get(r.field_name)
        if not limit or len(r.value) <= limit:
            continue

        cut = r.value[:limit]
        # Bevorzugt an einer Satzgrenze trennen; sonst an Semikolon oder Komma,
        # damit kein angefangener Teilsatz stehenbleibt.
        boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        if boundary < limit * 0.6:
            boundary = max(cut.rfind("; "), cut.rfind(", "))
        if boundary < limit * 0.6:
            boundary = cut.rfind(" ")
        if boundary > 0:
            cut = cut[: boundary + 1].rstrip().rstrip(",;")

        logger.warning(
            f"{r.field_name}: Antwort war {len(r.value)} Zeichen, Limit ist {limit} "
            f"- auf {len(cut)} Zeichen gekuerzt"
        )
        r.value = cut


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
                    beleg=str(item["beleg"]) if item.get("beleg") else None,
                )
            )
    return results
