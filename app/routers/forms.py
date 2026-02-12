import io
import uuid
import shutil

from flask import Blueprint, render_template, request, redirect, url_for, abort, send_file

from app.config import settings

forms_bp = Blueprint("forms", __name__)

# In-Memory Session-Speicher
sessions: dict = {}


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

    template_path = settings.FORM_TEMPLATE_DIR / f"{form_id}.pdf"
    if not template_path.exists():
        abort(404, "PDF-Vorlage nicht gefunden")

    images = convert_from_path(str(template_path), first_page=1, last_page=1, dpi=72)
    img = images[0]
    # Auf 50px Hoehe skalieren
    ratio = 50 / img.height
    new_width = int(img.width * ratio)
    img = img.resize((new_width, 50))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
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
        4: "Funktionseinschraenkungen",
        5: "Aktivitaeten und Teilhabe",
        6: "Therapie",
        7: "Untersuchungsbefunde",
        8: "Medizinisch-technische Befunde",
        9: "Lebensumstaende",
        10: "Risikofaktoren",
        11: "Arbeitsunfaehigkeit / Prognose",
        12: "Bemerkungen",
    }

    long_text_fields = {
        "ANAMNESE", "FUNKTIONSEINSCHRAENKUNGEN", "THERAPIE",
        "UNTERSUCHUNGSBEFUNDE", "MED_TECHN_BEFUNDE", "LEBENSUMSTAENDE",
        "BEMERKUNGEN", "SONSTIGES",
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
    for field in fields:
        if field.field_type == FieldType.CHECKBOX:
            field.value = "ja" if field.field_name in request.form else "nein"
        else:
            submitted_value = request.form.get(field.field_name)
            if submitted_value is not None:
                field.value = submitted_value
        if field.value and field.value not in ("", "nein"):
            field.status = FieldStatus.MANUAL

    # PDF erzeugen
    template_path = settings.FORM_TEMPLATE_DIR / f"{form_id}.pdf"
    output_path = settings.OUTPUT_DIR / f"{form_id}_{session_id}.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf_filler.fill_pdf(template_path, output_path, fields)

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
