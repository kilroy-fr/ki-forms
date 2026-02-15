#!/usr/bin/env python3
"""
Vergleicht die Feldnamen in s0051.py mit den tatsächlichen PDF-Feldnamen
"""
import pikepdf
from pathlib import Path
from app.form_definitions.s0051 import S0051_FIELDS

# Extrahiere tatsächliche PDF-Feldnamen
pdf = pikepdf.open("data/S0051.pdf")
pdf_text_fields = set()
pdf_button_fields = set()

# Text-Felder aus Page Annotations
for page in pdf.pages:
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
            pdf_text_fields.add(field_name)

# Button-Felder aus AcroForm
def collect_fields(field_ref, parent_name=None):
    field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref
    if not isinstance(field_obj, pikepdf.Dictionary):
        return

    t = field_obj.get("/T")
    if t is not None:
        try:
            name = str(t)
        except:
            try:
                name = bytes(t).decode('latin-1')
            except:
                name = parent_name
    else:
        name = parent_name

    if name:
        ft = field_obj.get("/FT")
        if ft and str(ft) == "/Btn":
            pdf_button_fields.add(name)

    kids = field_obj.get("/Kids")
    if kids:
        for kid_ref in kids:
            collect_fields(kid_ref, name)

if pdf.Root.get("/AcroForm") and "/Fields" in pdf.Root["/AcroForm"]:
    for field_ref in pdf.Root["/AcroForm"]["/Fields"]:
        collect_fields(field_ref)

pdf.close()

# Vergleiche mit Formulardefinition
print("=" * 80)
print("FELDMAPPING-ÜBERPRÜFUNG")
print("=" * 80)

all_pdf_fields = pdf_text_fields | pdf_button_fields
form_text_fields = set()
form_radio_groups = set()

for field in S0051_FIELDS:
    if field.field_type.value == "text":
        form_text_fields.add(field.field_name)
    elif field.field_type.value == "radio":
        if field.radio_group:
            form_radio_groups.add(field.radio_group)

print(f"\n✓ PDF hat {len(all_pdf_fields)} Felder total")
print(f"✓ Formulardefinition hat {len(form_text_fields)} Text-Felder und {len(form_radio_groups)} Radio-Gruppen")

# Felder in Formulardefinition, die NICHT im PDF sind
missing_in_pdf = form_text_fields - all_pdf_fields
if missing_in_pdf:
    print(f"\n⚠ {len(missing_in_pdf)} Felder in s0051.py existieren NICHT im PDF:")
    for field in sorted(missing_in_pdf):
        print(f"  - {field}")

# Radio-Gruppen in Formulardefinition, die NICHT im PDF sind
missing_radio = form_radio_groups - pdf_button_fields
if missing_radio:
    print(f"\n⚠ {len(missing_radio)} Radio-Gruppen in s0051.py existieren NICHT im PDF:")
    for field in sorted(missing_radio):
        print(f"  - {field}")

# Felder im PDF, die NICHT in Formulardefinition sind
missing_in_def = (all_pdf_fields - form_text_fields) - form_radio_groups
if missing_in_def:
    print(f"\n⚠ {len(missing_in_def)} Felder im PDF sind NICHT in s0051.py definiert:")
    for field in sorted(missing_in_def):
        print(f"  - {field}")

# Erfolgsrate berechnen
text_match_rate = len(form_text_fields - missing_in_pdf) / len(form_text_fields) * 100 if form_text_fields else 0
radio_match_rate = len(form_radio_groups - missing_radio) / len(form_radio_groups) * 100 if form_radio_groups else 0

print(f"\n" + "=" * 80)
print(f"ERFOLGSRATE:")
print(f"  Text-Felder: {text_match_rate:.1f}% ({len(form_text_fields - missing_in_pdf)}/{len(form_text_fields)})")
print(f"  Radio-Gruppen: {radio_match_rate:.1f}% ({len(form_radio_groups - missing_radio)}/{len(form_radio_groups)})")
print("=" * 80)
