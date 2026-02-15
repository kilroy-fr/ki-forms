import io
import uuid
import shutil
import json
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, abort, send_file, jsonify

from app.config import settings

forms_bp = Blueprint("forms", __name__)

# In-Memory Session-Speicher
sessions: dict = {}


def _normalize_radio_text(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""

    replacements = {
        "Ã¤": "ä",
        "Ã¶": "ö",
        "Ã¼": "ü",
        "ÃŸ": "ß",
        "鋍": "ä",
        "鋘": "ä",
        "鰐": "ö",
        "黨": "ü",
        "鰃": "ö",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    return " ".join(text.split()).casefold()


def _canonical_radio_token(normalized_text: str) -> str:
    if not normalized_text:
        return ""

    compact = "".join(ch for ch in normalized_text if ch.isalnum() or ch.isspace())
    compact = " ".join(compact.split())

    if compact in {"ja", "yes", "true", "1", "on"}:
        return "yes"
    if compact in {"nein", "no", "false", "0", "off"}:
        return "no"

    if "keine angabe" in compact:
        return "keine_angabe"
    if "personelle" in compact and "hilfe" in compact:
        return "personelle_hilfe"
    if "nicht" in compact and "durchf" in compact:
        return "nicht_durchfuehrbar"
    if "einschr" in compact:
        return "einschraenkungen"
    if "keine" in compact and ("beeintr" in compact or "beein" in compact):
        return "keine_beeintraechtigungen"

    return compact


def _radio_values_match(a: str | None, b: str | None) -> bool:
    a_norm = _normalize_radio_text(a)
    b_norm = _normalize_radio_text(b)
    if not a_norm or not b_norm:
        return False
    if a_norm == b_norm:
        return True
    return _canonical_radio_token(a_norm) == _canonical_radio_token(b_norm)


def _get_form_registry():
    """Lazy import um zirkulaere Imports zu vermeiden."""
    from app.form_definitions.s0051 import S0051_DEFINITION
    return {
        "S0051": S0051_DEFINITION,
    }


@forms_bp.route("/")
def index():
    """Hauptseite: Formularauswahl, Upload, Download."""
    session_id = request.args.get("session")
    form_id = request.args.get("form")
    download_url = None
    if session_id and form_id:
        output_path = settings.OUTPUT_DIR / f"{form_id}_{session_id}.pdf"
        if output_path.exists():
            download_url = url_for("forms.download_file", form_id=form_id, session_id=session_id)
    return render_template("index.html", forms=_get_form_registry(),
                           download_url=download_url, completed_form=form_id if download_url else None)


@forms_bp.route("/form/<form_id>/thumbnail")
def thumbnail(form_id):
    """Thumbnail der ersten PDF-Seite als JPEG."""
    from pdf2image import convert_from_path
    from PIL import Image

    template_path = settings.FORM_TEMPLATE_DIR / f"{form_id}.pdf"
    if not template_path.exists():
        abort(404, "PDF-Vorlage nicht gefunden")

    # Höhere DPI für bessere Qualität
    images = convert_from_path(str(template_path), first_page=1, last_page=1, dpi=200)
    img = images[0]
    # Auf 200px Höhe skalieren
    ratio = 200 / img.height
    new_width = int(img.width * ratio)
    # LANCZOS für beste Qualität beim Verkleinern
    img = img.resize((new_width, 200), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, optimize=True)
    buf.seek(0)
    return send_file(buf, mimetype="image/jpeg")


@forms_bp.route("/form/<form_id>/upload")
def upload_page(form_id):
    """Upload-Seite fuer ein bestimmtes Formular."""
    registry = _get_form_registry()
    if form_id not in registry:
        abort(404, "Formular nicht gefunden")
    return render_template("upload.html", form=registry[form_id])


@forms_bp.route("/form/<form_id>/process", methods=["POST"])
def process_upload(form_id):
    """Dateien hochladen, Text extrahieren, KI-Extraktion durchfuehren."""
    from app.services import pdf_reader, field_extractor
    from app.models.form_schema import FieldStatus

    registry = _get_form_registry()
    if form_id not in registry:
        abort(404, "Formular nicht gefunden")

    form_def = registry[form_id]
    session_id = str(uuid.uuid4())
    session_dir = settings.UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Dateien speichern
    files = request.files.getlist("files")
    saved_paths = []
    for f in files:
        if not f.filename:
            continue
        dest = session_dir / f.filename
        f.save(str(dest))
        saved_paths.append(dest)

    if not saved_paths:
        abort(400, "Keine Dateien hochgeladen")

    # Text aus allen PDFs extrahieren
    source_text = pdf_reader.extract_from_multiple(saved_paths)

    # KI-Feldextraktion
    extraction_results = field_extractor.extract_fields(
        form_def.fields, source_text
    )

    # Ergebnisse in Felder zusammenfuehren
    result_map = {r.field_name: r for r in extraction_results}
    fields = []
    for f in form_def.fields:
        field_copy = f.model_copy()
        if f.field_name in result_map:
            r = result_map[f.field_name]
            field_copy.value = r.value
            field_copy.status = FieldStatus.FILLED
            field_copy.ai_confidence = r.confidence
        fields.append(field_copy)

    # Sender-Daten laden und Behandlungsfelder automatisch befüllen
    if SENDER_DATA_FILE.exists():
        try:
            with open(SENDER_DATA_FILE, "r", encoding="utf-8") as f:
                sender_data = json.load(f)

            # Name der Ärztin/des Arztes zusammensetzen: Titel + Vorname + Name
            arzt_name_parts = []
            if sender_data.get("titel"):
                arzt_name_parts.append(sender_data["titel"])
            if sender_data.get("vorname"):
                arzt_name_parts.append(sender_data["vorname"])
            if sender_data.get("name"):
                arzt_name_parts.append(sender_data["name"])
            arzt_name = " ".join(arzt_name_parts)

            # Aktuelles Datum im Format TT.MM.JJJJ
            from datetime import datetime
            current_date = datetime.now().strftime("%d.%m.%Y")

            # Unterschrift-Feld: "Name, Datum"
            arzt_unters_value = ""
            if arzt_name:
                arzt_unters_value = f"{arzt_name}, {current_date}"

            # Felder befüllen
            for field in fields:
                if field.field_name == "NAME_DER_ÄRZTIN" and arzt_name:
                    field.value = arzt_name
                    field.status = FieldStatus.FILLED
                    field.ai_confidence = "high"
                elif field.field_name == "FACHRICHTUNG" and sender_data.get("fachrichtung"):
                    field.value = sender_data["fachrichtung"]
                    field.status = FieldStatus.FILLED
                    field.ai_confidence = "high"
                elif field.field_name == "TELEFONNUMMER_FÜR_RÜCKFRAGEN" and sender_data.get("telefon"):
                    field.value = sender_data["telefon"]
                    field.status = FieldStatus.FILLED
                    field.ai_confidence = "high"
                elif field.field_name == "ARZT_UNTERS_DATUM" and arzt_unters_value:
                    field.value = arzt_unters_value
                    field.status = FieldStatus.FILLED
                    field.ai_confidence = "high"
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Fehler beim Befüllen der Behandlungsfelder mit Sender-Daten: {e}")

    # Session speichern
    sessions[session_id] = {
        "form_id": form_id,
        "fields": fields,
        "source_text": source_text,
    }

    return redirect(url_for("forms.review_page", form_id=form_id, session_id=session_id))


@forms_bp.route("/form/<form_id>/review/<session_id>")
def review_page(form_id, session_id):
    """Felder pruefen und bearbeiten."""
    from app.models.form_schema import FieldStatus

    session = sessions.get(session_id)
    if not session:
        abort(404, "Sitzung nicht gefunden")

    registry = _get_form_registry()
    fields = session["fields"]
    filled = [f for f in fields if f.status == FieldStatus.FILLED]
    unfilled = [f for f in fields if f.status == FieldStatus.UNFILLED]

    # Felder nach Sektionen gruppieren
    sections: dict[int, list] = {}
    for f in fields:
        sections.setdefault(f.section, []).append(f)

    section_titles = {
        0: "Kopfdaten / Identifikation",
        1: "Behandlung",
        2: "Diagnosen",
        3: "Anamnese",
        4: "Funktionseinschränkungen",
        5: "Aktivitäten und Teilhabe",
        6: "Therapie",
        7: "Untersuchungsbefunde",
        8: "Medizinisch-technische Befunde",
        9: "Lebensumstände",
        10: "Risikofaktoren",
        11: "Arbeitsunfähigkeit / Prognose",
        12: "Bemerkungen",
    }

    long_text_fields = {
        "ANAMNESE", "FUNKTIONSEINSCHRAENKUNGEN", "THERAPIE",
        "UNTERSUCHUNGSBEFUNDE", "MED_TECHN_BEFUNDE", "LEBENSUMSTAENDE",
        "BEMERKUNGEN",
    }

    return render_template(
        "review.html",
        form=registry[form_id],
        session_id=session_id,
        sections=dict(sorted(sections.items())),
        section_titles=section_titles,
        filled_count=len(filled),
        unfilled_count=len(unfilled),
        total_count=len(fields),
        long_text_fields=long_text_fields,
    )


@forms_bp.route("/form/<form_id>/generate/<session_id>", methods=["POST"])
def generate_pdf(form_id, session_id):
    """Ausgefuelltes PDF generieren."""
    from app.services import pdf_filler
    from app.models.form_schema import FieldStatus, FieldType

    session = sessions.get(session_id)
    if not session:
        abort(404, "Sitzung nicht gefunden")

    # Formulardaten vom User uebernehmen
    fields = session["fields"]

    # DEBUG: Zeige alle Formular-Werte
    import logging
    logger = logging.getLogger(__name__)

    logger.debug("=" * 80)
    logger.debug("Verarbeite Formular-Daten")
    logger.debug(f"Anzahl Felder in request.form: {len(request.form)}")

    # Alle Formular-Daten nach Typ gruppieren
    radio_values = {k: v for k, v in request.form.items() if k.startswith('AW_')}
    text_values = {k: v for k, v in request.form.items() if not k.startswith('AW_')}

    logger.debug(f"Radio/Checkbox-Werte (AW_*): {len(radio_values)}")
    if radio_values:
        for key, value in sorted(radio_values.items()):
            logger.debug(f"  {key} = {value}")
    else:
        logger.warning("KEINE Radio-Button-Werte (AW_*) in request.form gefunden!")

    logger.debug(f"Text-Felder: {len(text_values)}")
    if text_values:
        for key, value in sorted(text_values.items()):
            # Nur erste 50 Zeichen loggen
            value_preview = (value[:50] + '...') if len(value) > 50 else value
            logger.debug(f"  {key} = {value_preview}")

    logger.debug("=" * 80)

    radio_fields_set = 0
    for field in fields:
        if field.field_type == FieldType.CHECKBOX:
            field.value = "ja" if field.field_name in request.form else "nein"
        elif field.field_type == FieldType.RADIO:
            # Radio-Button: Prüfe, ob dieser Radio-Button in der Gruppe ausgewählt wurde
            selected_value = request.form.get(field.radio_group)
            if selected_value is not None:
                field.value = "ja" if selected_value == field.field_name else "nein"
            else:
                current_value = (field.value or "").strip()
                current_norm = _normalize_radio_text(current_value)
                prefilled_selected = current_norm in {
                    "ja",
                    "yes",
                    "true",
                    "1",
                    "on",
                    _normalize_radio_text(field.field_name),
                    _normalize_radio_text(field.pdf_state),
                }
                if not prefilled_selected:
                    prefilled_selected = (
                        _radio_values_match(current_value, field.field_name) or
                        _radio_values_match(current_value, field.pdf_state)
                    )
                field.value = "ja" if prefilled_selected else "nein"
            if field.value == "ja":
                radio_fields_set += 1
                logger.debug(f"Radio {field.radio_group} -> {field.field_name} (pdf_state={field.pdf_state})")
        else:
            submitted_value = request.form.get(field.field_name)
            if submitted_value is not None:
                field.value = submitted_value
        if field.value and field.value not in ("", "nein"):
            field.status = FieldStatus.MANUAL

    logger.debug(f"{radio_fields_set} Radio-Buttons auf 'ja' gesetzt")
    logger.debug("=" * 80)

    # Automatische Wertkopie: MSAT_MSNR → DRV_Kopf_PAF_Reha_MSAT_MSNR
    fields_by_name = {f.field_name: f for f in fields}

    def _copy_if_value(source_name: str, target_name: str):
        source = fields_by_name.get(source_name)
        target = fields_by_name.get(target_name)
        if source and target and source.value:
            target.value = source.value
            target.status = FieldStatus.MANUAL

    # MSAT/MSNR -> Kopfzeile
    _copy_if_value("MSAT_MSNR", "DRV_Kopf_PAF_Reha_MSAT_MSNR")

    # Legacy-Feldnamen / UI-Hilfsfelder -> echte PDF-Felder
    _copy_if_value("VERS_VNR", "PAF_VSNR_trim")
    _copy_if_value("KENNZEICHEN", "PAF_AIGR")
    _copy_if_value("PAT_STRASSE_HNR", "VERS_STRASSE_HNR")
    _copy_if_value("PAT_PLZ", "VERS_PLZ")
    _copy_if_value("PAT_WOHNORT", "VERS_WOHNORT")

    # Legacy kombiniertes Feld "PLZ, Wohnort" aufteilen
    legacy_plz_ort = fields_by_name.get("PAT_PLZ_WOHNORT")
    if legacy_plz_ort and legacy_plz_ort.value:
        raw = legacy_plz_ort.value.strip()
        if raw:
            parts = raw.split(maxsplit=1)
            if parts and parts[0].isdigit() and len(parts[0]) >= 4:
                plz_target = fields_by_name.get("VERS_PLZ")
                if plz_target and not (plz_target.value or "").strip():
                    plz_target.value = parts[0]
                    plz_target.status = FieldStatus.MANUAL
                if len(parts) > 1:
                    ort_target = fields_by_name.get("VERS_WOHNORT")
                    if ort_target and not (ort_target.value or "").strip():
                        ort_target.value = parts[1]
                        ort_target.status = FieldStatus.MANUAL
            else:
                ort_target = fields_by_name.get("VERS_WOHNORT")
                if ort_target and not (ort_target.value or "").strip():
                    ort_target.value = raw
                    ort_target.status = FieldStatus.MANUAL

    # PDF erzeugen
    template_path = settings.FORM_TEMPLATE_DIR / f"{form_id}.pdf"
    output_path = settings.OUTPUT_DIR / f"{form_id}_{session_id}.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf_filler.fill_pdf(template_path, output_path, fields)

    # Zusaetzliche stabile Debug-/Ablage-Datei ohne Session-ID
    # (hilft bei manueller Pruefung im Output-Ordner)
    try:
        stable_output_path = settings.OUTPUT_DIR / f"{form_id}_ausgefuellt.pdf"
        shutil.copy2(output_path, stable_output_path)
        logger.debug(f"Stabile Output-Datei aktualisiert: {stable_output_path}")
    except Exception as e:
        logger.warning(f"Konnte stabile Output-Datei nicht aktualisieren: {e}")

    return redirect(url_for("forms.index", form=form_id, session=session_id))


@forms_bp.route("/form/<form_id>/download/<session_id>")
def download_page(form_id, session_id):
    """Download-Seite."""
    registry = _get_form_registry()
    output_path = settings.OUTPUT_DIR / f"{form_id}_{session_id}.pdf"
    if not output_path.exists():
        abort(404, "PDF nicht gefunden")

    return render_template(
        "download.html",
        form=registry[form_id],
        session_id=session_id,
        download_url=url_for("forms.download_file", form_id=form_id, session_id=session_id),
    )


@forms_bp.route("/form/<form_id>/file/<session_id>")
def download_file(form_id, session_id):
    """PDF-Datei ausliefern."""
    output_path = settings.OUTPUT_DIR / f"{form_id}_{session_id}.pdf"
    if not output_path.exists():
        abort(404, "PDF nicht gefunden")

    return send_file(
        str(output_path),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{form_id}_ausgefuellt.pdf",
    )


@forms_bp.route("/api/warmup", methods=["POST"])
def warmup_ollama():
    """API-Endpoint zum Aufwärmen des Ollama-Modells."""
    from app.services import ollama_client
    import threading

    def do_warmup():
        try:
            ollama_client.warmup_model(settings.OLLAMA_MODEL)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Warmup fehlgeschlagen: {e}")

    # Warmup in separatem Thread ausführen, um Request nicht zu blockieren
    thread = threading.Thread(target=do_warmup, daemon=True)
    thread.start()

    return {"status": "warmup_started"}, 202


# Pfad zur Absender-Daten-Datei
SENDER_DATA_FILE = settings.FORM_TEMPLATE_DIR / "sender_data.json"


@forms_bp.route("/api/sender-data", methods=["GET"])
def get_sender_data():
    """Absender-Daten abrufen."""
    try:
        if SENDER_DATA_FILE.exists():
            with open(SENDER_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify(data), 200
        else:
            return jsonify({}), 200
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Fehler beim Laden der Absender-Daten: {e}")
        return jsonify({"error": "Fehler beim Laden der Absender-Daten"}), 500


@forms_bp.route("/api/sender-data", methods=["POST"])
def save_sender_data():
    """Absender-Daten speichern."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Keine Daten empfangen"}), 400

        # Stelle sicher, dass das Verzeichnis existiert
        SENDER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Speichere die Daten
        with open(SENDER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "success", "message": "Absender-Daten gespeichert"}), 200
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Fehler beim Speichern der Absender-Daten: {e}")
        return jsonify({"error": "Fehler beim Speichern der Absender-Daten"}), 500
