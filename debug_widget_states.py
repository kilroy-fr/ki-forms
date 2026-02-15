#!/usr/bin/env python3
"""
Debug: Vergleicht direkte State-Extraktion mit _get_widget_on_state
"""
import pikepdf
from pathlib import Path
from app.services.pdf_filler import _get_widget_on_state

pdf_path = Path("data/S0051.pdf")
pdf = pikepdf.open(pdf_path)

def find_radio_field(field_name):
    """Finde ein Radio-Feld und seine Kids"""
    def search(field_ref, parent_name=None):
        field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref
        if not isinstance(field_obj, pikepdf.Dictionary):
            return None

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

        if name == field_name:
            return field_obj

        kids = field_obj.get("/Kids")
        if kids:
            for kid_ref in kids:
                result = search(kid_ref, name)
                if result is not None:
                    return result

        return None

    if pdf.Root.get("/AcroForm") and "/Fields" in pdf.Root["/AcroForm"]:
        for field_ref in pdf.Root["/AcroForm"]["/Fields"]:
            result = search(field_ref)
            if result is not None:
                return result
    return None

# Teste AW_4
print("=" * 80)
print("DEBUG: AW_4 Widget-States")
print("=" * 80)

aw4_field = find_radio_field("AW_4")
if aw4_field:
    kids = aw4_field.get("/Kids")
    if kids:
        print(f"\nAW_4 hat {len(kids)} Widgets\n")

        for i, kid_ref in enumerate(kids, 1):
            kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref

            print(f"Widget {i}:")

            # Methode 1: Direkte Extraktion (wie im inspect-Script)
            ap = kid.get("/AP")
            if ap and "/N" in ap:
                n_dict = ap["/N"]
                if isinstance(n_dict, pikepdf.Dictionary):
                    direct_states = []
                    for key in n_dict.keys():
                        state_name = str(key).lstrip("/")
                        if state_name != "Off":
                            direct_states.append(state_name)
                    print(f"  Direkt: {direct_states}")

            # Methode 2: _get_widget_on_state (wie im pdf_filler)
            on_state = _get_widget_on_state(kid)
            print(f"  _get_widget_on_state: {on_state}")
            print()
else:
    print("FEHLER: AW_4 nicht gefunden!")

pdf.close()
