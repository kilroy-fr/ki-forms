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
    - Textfelder und Checkboxen werden ueber Page-Annotations gefuellt.
    - Radio-Buttons werden ueber den AcroForm-Feldbaum gefuellt,
      da Radio-Widgets kein eigenes /T haben (erben es vom Parent).
    """
    pdf = pikepdf.open(str(template_path))

    # Lookup-Maps erstellen
    text_map: dict[str, str] = {}
    checkbox_map: dict[str, str] = {}
    radio_map: dict[str, str] = {}  # radio_group (= PDF-Feldname) -> pdf_state

    for f in fields:
        if f.field_type == FieldType.TEXT:
            if f.value:
                text_map[f.field_name] = f.value
        elif f.field_type == FieldType.CHECKBOX:
            if f.value:
                checkbox_map[f.field_name] = f.value
        elif f.field_type == FieldType.RADIO:
            if f.value == "ja" and f.pdf_state and f.radio_group:
                radio_map[f.radio_group] = f.pdf_state

    filled_count = 0

    # --- Text- und Checkbox-Felder ueber Page-Annotations fuellen ---
    for page in pdf.pages:
        if "/Annots" not in page:
            continue

        for annot in page["/Annots"]:
            annot_obj = annot.resolve() if hasattr(annot, "resolve") else annot

            field_name_obj = annot_obj.get("/T")
            if field_name_obj is None:
                continue

            field_name = str(field_name_obj)

            if field_name in text_map:
                _set_text_field(annot_obj, text_map[field_name])
                filled_count += 1
            elif field_name in checkbox_map:
                _set_checkbox_field(annot_obj, checkbox_map[field_name])
                filled_count += 1

    # --- Radio-Buttons ueber AcroForm-Feldbaum fuellen ---
    if radio_map:
        acroform = pdf.Root.get("/AcroForm")
        if acroform and "/Fields" in acroform:
            for field_ref in acroform["/Fields"]:
                filled_count += _fill_radio_in_tree(field_ref, radio_map)

    # NeedAppearances setzen, damit PDF-Viewer die Feldwerte anzeigt
    if "/AcroForm" in pdf.Root:
        pdf.Root["/AcroForm"][pikepdf.Name("/NeedAppearances")] = True
    else:
        logger.warning("Kein AcroForm im PDF gefunden")

    pdf.save(str(output_path))
    pdf.close()
    logger.info(f"PDF gespeichert: {output_path} ({filled_count} Felder ausgefuellt)")
    return output_path


# ---------------------------------------------------------------------------
# Radio-Buttons: AcroForm-Feldbaum durchlaufen
# ---------------------------------------------------------------------------

def _fill_radio_in_tree(field_ref, radio_map: dict[str, str], parent_name: str = None) -> int:
    """AcroForm-Feldbaum rekursiv durchlaufen und Radio-Gruppen fuellen."""
    field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref

    if not isinstance(field_obj, pikepdf.Dictionary):
        return 0

    t = field_obj.get("/T")
    name = str(t) if t is not None else parent_name

    kids = field_obj.get("/Kids")

    if name and name in radio_map and kids:
        # Dieses Feld ist eine Radio-Gruppe die gefuellt werden soll
        selected_state = radio_map[name]
        return _activate_radio_option(field_obj, kids, selected_state, name)

    if kids:
        # Zwischenknoten - weiter in die Tiefe
        count = 0
        for kid_ref in kids:
            count += _fill_radio_in_tree(kid_ref, radio_map, name)
        return count

    return 0


def _activate_radio_option(
    field_obj: pikepdf.Dictionary,
    kids,
    selected_state: str,
    field_name: str,
) -> int:
    """Die passende Radio-Option in einer Gruppe aktivieren."""
    matched = False
    selected_lower = selected_state.strip().lower()

    for kid_ref in kids:
        kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
        if not isinstance(kid, pikepdf.Dictionary):
            continue

        on_state = _get_widget_on_state(kid)
        on_lower = on_state.strip().lower()

        if on_lower == selected_lower:
            # Dieses Widget aktivieren
            kid[pikepdf.Name("/AS")] = pikepdf.Name(f"/{on_state}")
            if not matched:
                # /V auf dem Eltern-Feld setzen (nur einmal)
                field_obj[pikepdf.Name("/V")] = pikepdf.Name(f"/{on_state}")
                matched = True
        else:
            # Dieses Widget deaktivieren
            kid[pikepdf.Name("/AS")] = pikepdf.Name("/Off")

    if not matched:
        logger.warning(
            f"Radio-State '{selected_state}' nicht gefunden in Feld '{field_name}'. "
            f"Verfuegbare States: {_collect_kid_states(kids)}"
        )

    return 1 if matched else 0


def _collect_kid_states(kids) -> list[str]:
    """Alle On-States der Kids sammeln (fuer Debug-Logging)."""
    states = []
    for kid_ref in kids:
        kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
        if isinstance(kid, pikepdf.Dictionary):
            states.append(_get_widget_on_state(kid))
    return states


# ---------------------------------------------------------------------------
# Text- und Checkbox-Felder
# ---------------------------------------------------------------------------

def _set_text_field(annot: pikepdf.Dictionary, value: str):
    """Textfeld-Wert in die PDF-Annotation schreiben."""
    annot[pikepdf.Name("/V")] = pikepdf.String(value)
    # Appearance Stream entfernen, damit der Viewer ihn neu generiert
    if "/AP" in annot:
        del annot["/AP"]


def _set_checkbox_field(annot: pikepdf.Dictionary, value: str):
    """Checkbox setzen. Wert 'ja' = angekreuzt, sonst nicht."""
    if value.lower() in ("ja", "yes", "true", "1", "on"):
        on_state = _get_widget_on_state(annot)
        annot[pikepdf.Name("/V")] = pikepdf.Name(f"/{on_state}")
        annot[pikepdf.Name("/AS")] = pikepdf.Name(f"/{on_state}")
    else:
        annot[pikepdf.Name("/V")] = pikepdf.Name("/Off")
        annot[pikepdf.Name("/AS")] = pikepdf.Name("/Off")


def _get_widget_on_state(annot: pikepdf.Dictionary) -> str:
    """
    Den 'On'-State-Namen eines Widgets ermitteln.
    Checkboxen/Radio-Buttons verwenden /Yes, /On, /1 oder beschreibende Namen.
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
