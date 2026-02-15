#!/usr/bin/env python3
"""
Script to extract all field names from the S0051 PDF template
"""
import pikepdf
from pathlib import Path

pdf_path = Path("data/S0051.pdf")
pdf = pikepdf.open(pdf_path)

print("=" * 80)
print("TEXT-FELDER (aus Page Annotations)")
print("=" * 80)
text_fields = {}
for page_num, page in enumerate(pdf.pages, 1):
    if "/Annots" not in page:
        continue

    for annot in page["/Annots"]:
        annot_obj = annot.resolve() if hasattr(annot, "resolve") else annot

        field_name_obj = annot_obj.get("/T")
        if field_name_obj is None:
            continue

        try:
            field_name = str(field_name_obj)
        except UnicodeDecodeError:
            try:
                field_name = bytes(field_name_obj).decode('latin-1')
            except:
                field_name = "???"

        ft = annot_obj.get("/FT")
        field_type = str(ft) if ft else "Unknown"

        text_fields[field_name] = {
            "page": page_num,
            "type": field_type
        }

for field_name in sorted(text_fields.keys()):
    info = text_fields[field_name]
    print(f"  {field_name:40s} | Page {info['page']} | {info['type']}")

print("\n" + "=" * 80)
print("BUTTON-FELDER (Radio/Checkbox aus AcroForm)")
print("=" * 80)

button_fields = {}

def collect_acroform_fields(field_ref, parent_name=None, depth=0):
    field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref

    if not isinstance(field_obj, pikepdf.Dictionary):
        return

    t = field_obj.get("/T")
    if t is not None:
        try:
            name = str(t)
        except UnicodeDecodeError:
            try:
                name = bytes(t).decode('latin-1')
            except:
                name = parent_name
    else:
        name = parent_name

    ft = field_obj.get("/FT")
    field_type = str(ft) if ft else None

    kids = field_obj.get("/Kids")

    if name and field_type == "/Btn":
        # Count kids to distinguish radio from checkbox
        num_kids = len(kids) if kids else 0
        btn_type = "Radio" if num_kids > 1 else "Checkbox"

        if name not in button_fields:
            button_fields[name] = {
                "type": btn_type,
                "num_options": num_kids
            }

    if kids:
        for kid_ref in kids:
            collect_acroform_fields(kid_ref, name, depth + 1)

if pdf.Root.get("/AcroForm") and "/Fields" in pdf.Root["/AcroForm"]:
    for field_ref in pdf.Root["/AcroForm"]["/Fields"]:
        collect_acroform_fields(field_ref)

for field_name in sorted(button_fields.keys()):
    info = button_fields[field_name]
    print(f"  {field_name:40s} | {info['type']:10s} | {info['num_options']} options")

pdf.close()

print("\n" + "=" * 80)
print(f"SUMMARY: {len(text_fields)} Text-Felder, {len(button_fields)} Button-Felder")
print("=" * 80)
