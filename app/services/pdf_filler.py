import logging
from pathlib import Path

import pikepdf

from app.models.form_schema import FormField, FieldType

logger = logging.getLogger(__name__)


def fill_pdf(
    template_path: Path,
    output_path: Path,
    fields: list[FormField],
) -> Path:
    """
    Oeffnet die PDF-Vorlage und schreibt die Feldwerte hinein.
    Gibt den Pfad zur generierten Ausgabe-PDF zurueck.
    """
    pdf = pikepdf.open(str(template_path))

    # Feld-Lookup erstellen
    field_map = {f.field_name: f for f in fields if f.value}

    filled_count = 0
    for page in pdf.pages:
        if "/Annots" not in page:
            continue

        for annot in page["/Annots"]:
            annot_obj = annot.resolve() if hasattr(annot, "resolve") else annot

            field_name_obj = annot_obj.get("/T")
            if field_name_obj is None:
                continue

            field_name = str(field_name_obj)
            matching = field_map.get(field_name)
            if matching is None:
                continue

            try:
                if matching.field_type == FieldType.TEXT:
                    _set_text_field(annot_obj, matching.value)
                    filled_count += 1
                elif matching.field_type == FieldType.CHECKBOX:
                    _set_checkbox_field(annot_obj, matching.value)
                    filled_count += 1
                elif matching.field_type == FieldType.RADIO:
                    _set_radio_field(annot_obj, matching.value, field_name)
                    filled_count += 1
            except Exception as e:
                logger.warning(f"Fehler beim Fuellen von '{field_name}': {e}")

    # NeedAppearances setzen, damit PDF-Viewer die Feldwerte anzeigt
    if "/AcroForm" in pdf.Root:
        pdf.Root["/AcroForm"][pikepdf.Name("/NeedAppearances")] = True
    else:
        logger.warning("Kein AcroForm im PDF gefunden")

    pdf.save(str(output_path))
    pdf.close()
    logger.info(f"PDF gespeichert: {output_path} ({filled_count} Felder ausgefuellt)")
    return output_path


def _set_text_field(annot: pikepdf.Dictionary, value: str):
    """Textfeld-Wert in die PDF-Annotation schreiben."""
    annot[pikepdf.Name("/V")] = pikepdf.String(value)
    # Appearance Stream entfernen, damit der Viewer ihn neu generiert
    if "/AP" in annot:
        del annot["/AP"]


def _set_checkbox_field(annot: pikepdf.Dictionary, value: str):
    """Checkbox setzen. Wert 'ja' = angekreuzt, sonst nicht."""
    if value.lower() in ("ja", "yes", "true", "1", "on"):
        on_state = _get_checkbox_on_state(annot)
        annot[pikepdf.Name("/V")] = pikepdf.Name(f"/{on_state}")
        annot[pikepdf.Name("/AS")] = pikepdf.Name(f"/{on_state}")
    else:
        annot[pikepdf.Name("/V")] = pikepdf.Name("/Off")
        annot[pikepdf.Name("/AS")] = pikepdf.Name("/Off")


def _get_checkbox_on_state(annot: pikepdf.Dictionary) -> str:
    """
    Den 'On'-State-Namen einer Checkbox ermitteln.
    PDF-Checkboxen koennen /Yes, /On, /1 etc. verwenden.
    """
    ap = annot.get("/AP")
    if ap is not None:
        normal = ap.get("/N")
        if normal is not None:
            for key in normal.keys():
                name = str(key)
                if name.lstrip("/") != "Off":
                    return name.lstrip("/")
    return "Yes"


def _set_radio_field(annot: pikepdf.Dictionary, value: str, field_name: str):
    """
    Radio-Button setzen.
    Radio-Buttons werden im PDF mit dem Feldnamen des ausgewählten Buttons markiert.
    """
    # Prüfen ob dieser Radio-Button ausgewählt ist
    if value == field_name:
        # Diesen Button aktivieren
        on_state = _get_radio_on_state(annot, field_name)
        annot[pikepdf.Name("/V")] = pikepdf.Name(f"/{on_state}")
        annot[pikepdf.Name("/AS")] = pikepdf.Name(f"/{on_state}")
    else:
        # Diesen Button deaktivieren
        annot[pikepdf.Name("/AS")] = pikepdf.Name("/Off")


def _get_radio_on_state(annot: pikepdf.Dictionary, field_name: str) -> str:
    """
    Den 'On'-State-Namen eines Radio-Buttons ermitteln.
    Radio-Buttons verwenden oft den Feldnamen als On-State.
    """
    ap = annot.get("/AP")
    if ap is not None:
        normal = ap.get("/N")
        if normal is not None:
            for key in normal.keys():
                name = str(key)
                if name.lstrip("/") != "Off":
                    return name.lstrip("/")
    # Fallback: Feldname verwenden
    return field_name
