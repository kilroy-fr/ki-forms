#!/usr/bin/env python3
"""
Extrahiert die On-State-Namen aller Radio-Button-Felder aus dem PDF
"""
import pikepdf
from pathlib import Path

def get_widget_on_state(widget):
    """Ermittle den On-State-Namen eines Widgets"""
    ap = widget.get("/AP")
    if ap is not None:
        normal = ap.get("/N")
        if normal is not None:
            for key in normal.keys():
                try:
                    name = str(key).lstrip("/")
                except:
                    try:
                        if hasattr(key, 'name'):
                            name = key.name
                        elif isinstance(key, bytes):
                            name = key.decode('latin-1')
                        else:
                            name = repr(key).strip("'\"").lstrip("/")
                    except:
                        continue
                if name != "Off":
                    return name
    return "Yes"

def collect_radio_states(field_ref, parent_name=None, depth=0):
    """Sammle alle Radio-Button-Felder mit ihren On-States"""
    field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref

    if not isinstance(field_obj, pikepdf.Dictionary):
        return []

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

    ft = field_obj.get("/FT")
    kids = field_obj.get("/Kids")

    results = []

    if name and ft and str(ft) == "/Btn" and kids and len(kids) > 1:
        # Das ist eine Radio-Gruppe
        states = []
        for kid_ref in kids:
            kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
            if isinstance(kid, pikepdf.Dictionary):
                state = get_widget_on_state(kid)
                states.append(state)
        results.append({
            "name": name,
            "type": "Radio",
            "states": states
        })

    if kids:
        for kid_ref in kids:
            results.extend(collect_radio_states(kid_ref, name, depth + 1))

    return results

# PDF öffnen
pdf = pikepdf.open("data/S0051.pdf")

print("=" * 80)
print("RADIO-BUTTON FELDER UND IHRE ON-STATES")
print("=" * 80)

if pdf.Root.get("/AcroForm") and "/Fields" in pdf.Root["/AcroForm"]:
    all_radios = []
    for field_ref in pdf.Root["/AcroForm"]["/Fields"]:
        all_radios.extend(collect_radio_states(field_ref))

    # Filtere und sortiere nach Feldname
    aw_radios = [r for r in all_radios if r["name"].startswith("AW_")]
    aw_radios.sort(key=lambda x: x["name"])

    for radio in aw_radios:
        print(f"\n{radio['name']}:")
        for i, state in enumerate(radio['states']):
            print(f"  #{i} = {state}")

pdf.close()
