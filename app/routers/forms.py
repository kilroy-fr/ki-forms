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
    from app.form_definitions.s0050 import S0050_DEFINITION
    from app.form_definitions.s0051 import S0051_DEFINITION
    return {
        "S0050": S0050_DEFINITION,
        "S0051": S0051_DEFINITION,
    }


@forms_bp.route("/")
def index():
    """Hauptseite: Formularauswahl, Upload, Download."""
    session_id = request.args.get("session")
    form_id = request.args.get("form")
    download_url = None
    pdf_filename = None
    s0050_download_url = None
    s0050_pdf_filename = None

    if session_id and form_id:
        output_path = settings.OUTPUT_DIR / f"{form_id}_{session_id}.pdf"
        if output_path.exists():
            download_url = url_for("forms.download_file", form_id=form_id, session_id=session_id)
            pdf_filename = f"{form_id}_ausgefuellt.pdf"

            # Prüfe, ob S0050 auch existiert (bei S0051-Generierung)
            if form_id == "S0051":
                s0050_output_path = settings.OUTPUT_DIR / f"S0050_{session_id}.pdf"
                if s0050_output_path.exists():
                    s0050_download_url = url_for("forms.download_file", form_id="S0050", session_id=session_id)
                    s0050_pdf_filename = "S0050_ausgefuellt.pdf"

    return render_template("index.html", forms=_get_form_registry(),
                           download_url=download_url, pdf_filename=pdf_filename,
                           completed_form=form_id if download_url else None,
                           s0050_download_url=s0050_download_url, s0050_pdf_filename=s0050_pdf_filename)


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

    # Automatische Wertkopie: PAT_* -> VERS_* (für Review-Anzeige)
    fields_by_name = {f.field_name: f for f in fields}

    # Name kopieren
    pat_name = fields_by_name.get("PAT_NAME")
    vers_name = fields_by_name.get("VERS_NAME")
    if pat_name and vers_name and pat_name.value and not vers_name.value:
        vers_name.value = pat_name.value
        vers_name.status = FieldStatus.FILLED
        vers_name.ai_confidence = pat_name.ai_confidence

    # Adresse kopieren
    for pat_field, vers_field in [
        ("PAT_STRASSE_HNR", "VERS_STRASSE_HNR"),
        ("PAT_PLZ", "VERS_PLZ"),
        ("PAT_WOHNORT", "VERS_WOHNORT"),
    ]:
        pat = fields_by_name.get(pat_field)
        vers = fields_by_name.get(vers_field)
        if pat and vers and pat.value and not vers.value:
            vers.value = pat.value
            vers.status = FieldStatus.FILLED
            vers.ai_confidence = pat.ai_confidence

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

    # Formular-spezifische Sektionsnamen
    if form_id == "S0050":
        section_titles = {
            0: "Kopfdaten / Antragsart",
            1: "Personalien",
            2: "Zahlungsempfänger / Bankdaten",
        }
    else:
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
    _copy_if_value("PAT_NAME", "VERS_NAME")
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

    # Wenn S0051 generiert wird, auch S0050 automatisch befüllen
    if form_id == "S0051":
        try:
            _generate_s0050_from_s0051(session_id, fields_by_name)
            logger.info(f"S0050 automatisch generiert für Session {session_id}")
        except Exception as e:
            logger.error(f"Fehler beim automatischen Generieren von S0050: {e}")

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


def _generate_s0050_from_s0051(session_id: str, s0051_fields: dict):
    """Generiert S0050 automatisch aus S0051-Daten und sender_data.json."""
    from app.services import pdf_filler
    from app.models.form_schema import FieldStatus
    from app.form_definitions.s0050 import S0050_DEFINITION
    from datetime import datetime
    import logging
    logger = logging.getLogger(__name__)

    # S0050 Felder erstellen
    s0050_fields = [f.model_copy() for f in S0050_DEFINITION.fields]
    s0050_fields_by_name = {f.field_name: f for f in s0050_fields}

    # Sender-Daten laden
    sender_data = {}
    if SENDER_DATA_FILE.exists():
        try:
            with open(SENDER_DATA_FILE, "r", encoding="utf-8") as f:
                sender_data = json.load(f)
        except Exception as e:
            logger.warning(f"Fehler beim Laden der Sender-Daten: {e}")

    # Versicherungsnummer und Kennzeichen von S0051 übernehmen
    vsnr = s0051_fields.get("PAF_VSNR_trim")
    kennz = s0051_fields.get("PAF_AIGR")

    if vsnr and vsnr.value:
        s0050_fields_by_name["PAF_VSNR_trim"].value = vsnr.value
        s0050_fields_by_name["PAF_VSNR_trim"].status = FieldStatus.MANUAL

    if kennz and kennz.value:
        s0050_fields_by_name["PAF_AIGR"].value = kennz.value
        s0050_fields_by_name["PAF_AIGR"].status = FieldStatus.MANUAL

    # Antragsart von S0051 übernehmen (AW_1)
    for s0051_field_name in ["AW_1_med_reha", "AW_1_onko_reha", "AW_1_lta", "AW_1_emr"]:
        s0051_field = s0051_fields.get(s0051_field_name)
        if s0051_field and s0051_field.value == "ja":
            # Gleicher Feldname in S0050
            s0050_field = s0050_fields_by_name.get(s0051_field_name)
            if s0050_field:
                s0050_field.value = "ja"
                s0050_field.status = FieldStatus.MANUAL
            break

    # Vergütung für S0051 aktivieren
    s0050_fields_by_name["AW_Verguetung_BB"].value = "ja"
    s0050_fields_by_name["AW_Verguetung_BB"].status = FieldStatus.MANUAL

    # Patientendaten von S0051 übernehmen
    pat_name = s0051_fields.get("PAT_NAME")
    pat_gebdat = s0051_fields.get("PAT_Geburtsdatum")

    if pat_name and pat_name.value:
        s0050_fields_by_name["PAT_NAME"].value = pat_name.value
        s0050_fields_by_name["PAT_NAME"].status = FieldStatus.MANUAL

    if pat_gebdat and pat_gebdat.value:
        s0050_fields_by_name["PAT_Geburtsdatum"].value = pat_gebdat.value
        s0050_fields_by_name["PAT_Geburtsdatum"].status = FieldStatus.MANUAL

    # Versicherte/r Daten (normalerweise identisch mit Patientin/Patient)
    vers_name = s0051_fields.get("VERS_NAME")
    vers_gebdat = s0051_fields.get("VERS_GEBDAT")

    if vers_name and vers_name.value and vers_name.value != pat_name.value if pat_name else True:
        s0050_fields_by_name["VERS_NAME"].value = vers_name.value
        s0050_fields_by_name["VERS_NAME"].status = FieldStatus.MANUAL

    if vers_gebdat and vers_gebdat.value and vers_gebdat.value != pat_gebdat.value if pat_gebdat else True:
        s0050_fields_by_name["VERS_GEBDAT"].value = vers_gebdat.value
        s0050_fields_by_name["VERS_GEBDAT"].status = FieldStatus.MANUAL

    # Absender-Daten befüllen
    if sender_data:
        # IBAN
        if sender_data.get("iban"):
            s0050_fields_by_name["KONTOINH_IBAN"].value = sender_data["iban"]
            s0050_fields_by_name["KONTOINH_IBAN"].status = FieldStatus.MANUAL

        # Geldinstitut
        if sender_data.get("kreditinstitut"):
            s0050_fields_by_name["KONTOINH_BANK_1"].value = sender_data["kreditinstitut"]
            s0050_fields_by_name["KONTOINH_BANK_1"].status = FieldStatus.MANUAL

        # Kontoinhaber: Vorname + Name
        kontoinhaber_parts = []
        if sender_data.get("vorname"):
            kontoinhaber_parts.append(sender_data["vorname"])
        if sender_data.get("name"):
            kontoinhaber_parts.append(sender_data["name"])
        if kontoinhaber_parts:
            s0050_fields_by_name["KONTOINH_NAME_1"].value = " ".join(kontoinhaber_parts)
            s0050_fields_by_name["KONTOINH_NAME_1"].status = FieldStatus.MANUAL

        # Adresse: Strasse + PLZ + Ort
        adresse_parts = []
        if sender_data.get("strasse"):
            strasse = sender_data["strasse"]
            if sender_data.get("hausnummer"):
                strasse += " " + sender_data["hausnummer"]
            adresse_parts.append(strasse)
        if sender_data.get("plz") and sender_data.get("ort"):
            adresse_parts.append(f"{sender_data['plz']} {sender_data['ort']}")
        if adresse_parts:
            s0050_fields_by_name["KONTOINH_ORT_1"].value = ", ".join(adresse_parts)
            s0050_fields_by_name["KONTOINH_ORT_1"].status = FieldStatus.MANUAL

    # Aktuelles Datum
    current_date = datetime.now().strftime("%d.%m.%Y")

    # Rechnungsdatum
    s0050_fields_by_name["RECHNUNG_VOM"].value = current_date
    s0050_fields_by_name["RECHNUNG_VOM"].status = FieldStatus.MANUAL

    # Ort, Datum (für ARZT_ORT): [aktuelles Datum] + Ort
    ort_datum = current_date
    if sender_data.get("ort"):
        ort_datum = f"{sender_data['ort']}, {current_date}"
    s0050_fields_by_name["ARZT_ORT"].value = ort_datum
    s0050_fields_by_name["ARZT_ORT"].status = FieldStatus.MANUAL

    # Unterschrift (ARZT_UNTERS): Vorname + Name
    arzt_unters_parts = []
    if sender_data.get("vorname"):
        arzt_unters_parts.append(sender_data["vorname"])
    if sender_data.get("name"):
        arzt_unters_parts.append(sender_data["name"])
    if arzt_unters_parts:
        s0050_fields_by_name["ARZT_UNTERS"].value = " ".join(arzt_unters_parts)
        s0050_fields_by_name["ARZT_UNTERS"].status = FieldStatus.MANUAL

    # S0050 PDF generieren
    s0050_template_path = settings.FORM_TEMPLATE_DIR / "S0050.pdf"
    s0050_output_path = settings.OUTPUT_DIR / f"S0050_{session_id}.pdf"

    pdf_filler.fill_pdf(s0050_template_path, s0050_output_path, s0050_fields)

    # Stabile Output-Datei
    try:
        stable_output_path = settings.OUTPUT_DIR / "S0050_ausgefuellt.pdf"
        shutil.copy2(s0050_output_path, stable_output_path)
        logger.debug(f"S0050 stabile Output-Datei aktualisiert: {stable_output_path}")
    except Exception as e:
        logger.warning(f"Konnte S0050 stabile Output-Datei nicht aktualisieren: {e}")


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


@forms_bp.route("/form/S0050/generate-standalone", methods=["POST"])
def generate_s0050_standalone():
    """S0050 separat generieren (nur mit sender_data.json, ohne Upload)."""
    from app.services import pdf_filler
    from app.models.form_schema import FieldStatus
    from app.form_definitions.s0050 import S0050_DEFINITION
    from datetime import datetime
    import logging
    logger = logging.getLogger(__name__)

    # Neue Session-ID generieren
    session_id = str(uuid.uuid4())

    # S0050 Felder erstellen
    s0050_fields = [f.model_copy() for f in S0050_DEFINITION.fields]
    s0050_fields_by_name = {f.field_name: f for f in s0050_fields}

    # Sender-Daten laden
    sender_data = {}
    if SENDER_DATA_FILE.exists():
        try:
            with open(SENDER_DATA_FILE, "r", encoding="utf-8") as f:
                sender_data = json.load(f)
        except Exception as e:
            logger.warning(f"Fehler beim Laden der Sender-Daten: {e}")
            return jsonify({"error": "Fehler beim Laden der Absender-Daten"}), 500

    # Absender-Daten befüllen
    if sender_data:
        # IBAN
        if sender_data.get("iban"):
            s0050_fields_by_name["KONTOINH_IBAN"].value = sender_data["iban"]
            s0050_fields_by_name["KONTOINH_IBAN"].status = FieldStatus.MANUAL

        # Geldinstitut
        if sender_data.get("kreditinstitut"):
            s0050_fields_by_name["KONTOINH_BANK_1"].value = sender_data["kreditinstitut"]
            s0050_fields_by_name["KONTOINH_BANK_1"].status = FieldStatus.MANUAL

        # Kontoinhaber: Vorname + Name
        kontoinhaber_parts = []
        if sender_data.get("vorname"):
            kontoinhaber_parts.append(sender_data["vorname"])
        if sender_data.get("name"):
            kontoinhaber_parts.append(sender_data["name"])
        if kontoinhaber_parts:
            s0050_fields_by_name["KONTOINH_NAME_1"].value = " ".join(kontoinhaber_parts)
            s0050_fields_by_name["KONTOINH_NAME_1"].status = FieldStatus.MANUAL

        # Adresse: Strasse + PLZ + Ort
        adresse_parts = []
        if sender_data.get("strasse"):
            strasse = sender_data["strasse"]
            if sender_data.get("hausnummer"):
                strasse += " " + sender_data["hausnummer"]
            adresse_parts.append(strasse)
        if sender_data.get("plz") and sender_data.get("ort"):
            adresse_parts.append(f"{sender_data['plz']} {sender_data['ort']}")
        if adresse_parts:
            s0050_fields_by_name["KONTOINH_ORT_1"].value = ", ".join(adresse_parts)
            s0050_fields_by_name["KONTOINH_ORT_1"].status = FieldStatus.MANUAL

    # Aktuelles Datum
    current_date = datetime.now().strftime("%d.%m.%Y")

    # Rechnungsdatum
    s0050_fields_by_name["RECHNUNG_VOM"].value = current_date
    s0050_fields_by_name["RECHNUNG_VOM"].status = FieldStatus.MANUAL

    # Ort, Datum (für ARZT_ORT): [aktuelles Datum] + Ort
    ort_datum = current_date
    if sender_data.get("ort"):
        ort_datum = f"{sender_data['ort']}, {current_date}"
    s0050_fields_by_name["ARZT_ORT"].value = ort_datum
    s0050_fields_by_name["ARZT_ORT"].status = FieldStatus.MANUAL

    # Unterschrift (ARZT_UNTERS): Vorname + Name
    arzt_unters_parts = []
    if sender_data.get("vorname"):
        arzt_unters_parts.append(sender_data["vorname"])
    if sender_data.get("name"):
        arzt_unters_parts.append(sender_data["name"])
    if arzt_unters_parts:
        s0050_fields_by_name["ARZT_UNTERS"].value = " ".join(arzt_unters_parts)
        s0050_fields_by_name["ARZT_UNTERS"].status = FieldStatus.MANUAL

    # Vergütung für S0051 aktivieren (Standard)
    s0050_fields_by_name["AW_Verguetung_BB"].value = "ja"
    s0050_fields_by_name["AW_Verguetung_BB"].status = FieldStatus.MANUAL

    # Session speichern für Review
    sessions[session_id] = {
        "form_id": "S0050",
        "fields": s0050_fields,
        "source_text": "",
    }

    # Zur Review-Seite weiterleiten
    return redirect(url_for("forms.review_page", form_id="S0050", session_id=session_id))
