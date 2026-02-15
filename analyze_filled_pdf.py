#!/usr/bin/env python3
"""
Analysiert ein ausgefülltes PDF und zeigt alle gesetzten Felder
"""
import sys
import pikepdf
from pathlib import Path

def analyze_pdf(pdf_path):
    """Analysiere alle Felder im PDF"""
    pdf = pikepdf.open(pdf_path)

    print("=" * 80)
    print(f"PDF ANALYSE: {pdf_path}")
    print("=" * 80)

    # Text-Felder aus Page Annotations
    print("\n" + "=" * 80)
    print("TEXT-FELDER")
    print("=" * 80)

    text_fields = {}
    for page_num, page in enumerate(pdf.pages, 1):
        if "/Annots" not in page:
            continue
        for annot in page["/Annots"]:
            annot_obj = annot.resolve() if hasattr(annot, "resolve") else annot
            field_name_obj = annot_obj.get("/T")
            if field_name_obj:
                try:
                    field_name = str(field_name_obj)
                except:
                    try:
                        field_name = bytes(field_name_obj).decode('latin-1')
                    except:
                        continue

                # Hole den Wert
                value = annot_obj.get("/V")
                if value:
                    try:
                        value_str = str(value)
                    except:
                        value_str = "???"
                    text_fields[field_name] = value_str

    if text_fields:
        for field, value in sorted(text_fields.items()):
            print(f"  {field}: {value}")
    else:
        print("  (keine Text-Felder ausgefuellt)")

    # Button-Felder aus AcroForm
    print("\n" + "=" * 80)
    print("RADIO-BUTTON-FELDER")
    print("=" * 80)

    radio_fields = {}

    def collect_button_values(field_ref, parent_name=None):
        field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref
        if not isinstance(field_obj, pikepdf.Dictionary):
            return

        t = field_obj.get("/T")
        if t:
            try:
                name = str(t)
            except:
                try:
                    name = bytes(t).decode('latin-1')
                except:
                    name = parent_name
        else:
            name = parent_name

        ft = field_obj.get("/FT")
        kids = field_obj.get("/Kids")

        if name and ft and str(ft) == "/Btn" and kids:
            # Das ist ein Button-Feld
            value = field_obj.get("/V")
            if value:
                try:
                    value_str = str(value).lstrip("/")
                except:
                    try:
                        if isinstance(value, bytes):
                            value_str = value.decode('latin-1')
                        else:
                            value_str = "???"
                    except:
                        value_str = "???"

                # Prüfe, ob es ein Radio (mehrere Kids) oder Checkbox ist
                is_radio = len(kids) > 1
                field_type = "Radio" if is_radio else "Checkbox"
                radio_fields[name] = {"type": field_type, "value": value_str}

        if kids:
            for kid_ref in kids:
                collect_button_values(kid_ref, name)

    if pdf.Root.get("/AcroForm") and "/Fields" in pdf.Root["/AcroForm"]:
        for field_ref in pdf.Root["/AcroForm"]["/Fields"]:
            collect_button_values(field_ref)

    if radio_fields:
        # Gruppiere nach Typ
        radios = {k: v for k, v in radio_fields.items() if v["type"] == "Radio"}
        checkboxes = {k: v for k, v in radio_fields.items() if v["type"] == "Checkbox"}

        if radios:
            print("\nRadio-Buttons:")
            for field, data in sorted(radios.items()):
                print(f"  {field}: {data['value']}")

        if checkboxes:
            print("\nCheckboxen:")
            for field, data in sorted(checkboxes.items()):
                print(f"  {field}: {data['value']}")
    else:
        print("  (keine Button-Felder ausgefuellt)")

    pdf.close()

    print("\n" + "=" * 80)
    print("ZUSAMMENFASSUNG")
    print("=" * 80)
    print(f"Text-Felder ausgefuellt: {len(text_fields)}")
    print(f"Button-Felder ausgefuellt: {len(radio_fields)}")

    # Zähle Aktivitäten
    aktivitaeten_gesetzt = [k for k in radio_fields.keys() if k.startswith("AW_") and 4 <= int(k.split("_")[1]) <= 12]
    print(f"Aktivitaeten (AW_4-AW_12) gesetzt: {len(aktivitaeten_gesetzt)}")
    if aktivitaeten_gesetzt:
        for aw in sorted(aktivitaeten_gesetzt):
            print(f"  - {aw}: {radio_fields[aw]['value']}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        # Verwende das zuletzt erstellte Test-PDF
        pdf_path = Path("data/S0051_aktivitaeten_test.pdf")

    if not pdf_path.exists():
        print(f"FEHLER: PDF nicht gefunden: {pdf_path}")
        print("\nVerwendung: python analyze_filled_pdf.py <pfad_zum_pdf>")
        sys.exit(1)

    analyze_pdf(pdf_path)
