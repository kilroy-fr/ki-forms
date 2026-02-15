#!/usr/bin/env python3
"""
Inspiziert die tatsächlichen On-States der Aktivitäten-Felder (AW_4-AW_12)
"""
import pikepdf
from pathlib import Path

def get_radio_states(field_name, pdf_path):
    """Extrahiere alle On-States eines Radio-Button-Feldes"""
    pdf = pikepdf.open(pdf_path)

    if not pdf.Root.get("/AcroForm") or "/Fields" not in pdf.Root["/AcroForm"]:
        return None

    def find_field(field_ref, target_name, parent_name=None):
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

        if name == target_name:
            # Gefunden! Hole die Kids (Widget-Annotationen)
            kids = field_obj.get("/Kids")
            if not kids:
                return None

            states = []
            for kid_ref in kids:
                kid_obj = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
                if not isinstance(kid_obj, pikepdf.Dictionary):
                    continue

                # Hole Appearance-States
                ap = kid_obj.get("/AP")
                if ap and "/N" in ap:
                    n_dict = ap["/N"]
                    if isinstance(n_dict, pikepdf.Dictionary):
                        for key in n_dict.keys():
                            state_name = str(key).lstrip("/")
                            if state_name and state_name != "Off":
                                # Versuche Latin-1 Dekodierung für Umlaute
                                try:
                                    if any(0xdc00 <= ord(c) <= 0xdcff for c in state_name):
                                        fixed_bytes = bytearray()
                                        for char in state_name:
                                            if 0xdc00 <= ord(char) <= 0xdcff:
                                                fixed_bytes.append(ord(char) - 0xdc00)
                                            else:
                                                fixed_bytes.append(ord(char))
                                        state_name = fixed_bytes.decode('latin-1')
                                except:
                                    pass
                                states.append(state_name)
            return states

        # Suche in Kids
        kids = field_obj.get("/Kids")
        if kids:
            for kid_ref in kids:
                result = find_field(kid_ref, target_name, name)
                if result is not None:
                    return result

        return None

    for field_ref in pdf.Root["/AcroForm"]["/Fields"]:
        result = find_field(field_ref, field_name)
        if result is not None:
            pdf.close()
            return result

    pdf.close()
    return None

# PDF-Pfad
pdf_path = Path("data/S0051.pdf")

print("=" * 80)
print("AKTIVITÄTEN-FELDER: ON-STATES")
print("=" * 80)

aktivitaeten = [
    ("AW_4", "Lernen und Wissensanwendung"),
    ("AW_5", "Allgemeine Aufgaben und Anforderungen"),
    ("AW_6", "Kommunikation"),
    ("AW_7", "Mobilität"),
    ("AW_8", "Arbeit und Beschäftigung"),
    ("AW_9", "Erziehung / Bildung"),
    ("AW_10", "Interpersonelle Aktivitäten"),
    ("AW_11", "Häusl. Leben / Haushaltsführung"),
    ("AW_12", "Selbstversorgung")
]

for field_name, label in aktivitaeten:
    states = get_radio_states(field_name, pdf_path)
    print(f"\n{field_name} ({label}):")
    if states:
        for i, state in enumerate(states, 1):
            print(f"  {i}. {state}")
    else:
        print("  [FEHLER: Keine States gefunden]")

print("\n" + "=" * 80)
