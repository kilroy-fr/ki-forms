#!/usr/bin/env python3
"""
Test-Script für die korrigierten Checkbox/Radiobutton-Felder (AW_13-AW_26)
"""
from pathlib import Path
from app.models.form_schema import FormField, FieldType
from app.services.pdf_filler import fill_pdf

# Test-Felder für die korrigierten Risikofaktoren und Prognose-Felder
test_fields = [
    # Text-Felder zum Testen
    FormField(field_name="PAT_NAME", field_type=FieldType.TEXT, label_de="Test", section=0, description="Test", value="Mustermann, Max"),
    FormField(field_name="PAT_Geburtsdatum", field_type=FieldType.TEXT, label_de="Test", section=0, description="Test", value="01.01.1970"),

    # === RISIKOFAKTOREN (AW_13-AW_19) ===
    # AW_13: Bewegungsmangel (Checkbox)
    FormField(field_name="AW_13", field_type=FieldType.CHECKBOX, label_de="Bewegungsmangel", section=10, description="Test", value="ja"),

    # AW_14: Übergewicht/Untergewicht (Radiogruppe)
    FormField(
        field_name="AW_14_uebergewicht",
        field_type=FieldType.RADIO,
        label_de="Übergewicht",
        section=10,
        description="Test",
        radio_group="AW_14",
        pdf_state="Übergewicht",
        value="ja"
    ),

    # AW_15: Alkohol (Checkbox)
    FormField(field_name="AW_15", field_type=FieldType.CHECKBOX, label_de="Alkohol", section=10, description="Test", value="ja"),

    # AW_16: Drogen (Checkbox)
    FormField(field_name="AW_16", field_type=FieldType.CHECKBOX, label_de="Drogen", section=10, description="Test", value="nein"),

    # AW_17: Medikamente (Checkbox)
    FormField(field_name="AW_17", field_type=FieldType.CHECKBOX, label_de="Medikamente", section=10, description="Test", value="ja"),

    # AW_18: Nikotin (Checkbox)
    FormField(field_name="AW_18", field_type=FieldType.CHECKBOX, label_de="Nikotin", section=10, description="Test", value="ja"),

    # AW_19: Sonstiges (Checkbox)
    FormField(field_name="AW_19", field_type=FieldType.CHECKBOX, label_de="Sonstiges", section=10, description="Test", value="nein"),

    # === ARBEITSUNFÄHIGKEIT / PROGNOSE (AW_20-AW_26) ===
    # AW_20: Arbeitsunfähigkeit (Radiogruppe)
    FormField(
        field_name="AW_20_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Test",
        radio_group="AW_20",
        pdf_state="ja",
        value="ja"
    ),
    FormField(field_name="VERS_BESSERUNG_DATUM_1", field_type=FieldType.TEXT, label_de="AU seit", section=11, description="Test", value="01.01.2024"),
    FormField(field_name="VERS_AU_GRUND", field_type=FieldType.TEXT, label_de="AU wegen", section=11, description="Test", value="Rückenschmerzen"),

    # AW_21: Befundänderung (Radiogruppe)
    FormField(
        field_name="AW_21_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Test",
        radio_group="AW_21",
        pdf_state="ja",
        value="ja"
    ),

    # AW_22: Besserung/Verschlechterung (Radiogruppe, nur wenn AW_21=ja)
    FormField(
        field_name="AW_22_besserung",
        field_type=FieldType.RADIO,
        label_de="Besserung seit",
        section=11,
        description="Test",
        radio_group="AW_22",
        pdf_state="Besserung",
        value="ja"
    ),
    FormField(field_name="VERS_BESSERUNG_DATUM_2", field_type=FieldType.TEXT, label_de="Datum", section=11, description="Test", value="15.01.2024"),

    # AW_23: Deutsche Sprache (Radiogruppe)
    FormField(
        field_name="AW_23_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Test",
        radio_group="AW_23",
        pdf_state="ja",
        value="ja"
    ),

    # AW_24: Reisefähigkeit (Radiogruppe)
    FormField(
        field_name="AW_24_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Test",
        radio_group="AW_24",
        pdf_state="ja",
        value="ja"
    ),
    FormField(field_name="AW_24_1", field_type=FieldType.CHECKBOX, label_de="mit Begleitung", section=11, description="Test", value="ja"),

    # AW_25: Besserung der Leistungsfähigkeit (Radiogruppe)
    FormField(
        field_name="AW_25_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Test",
        radio_group="AW_25",
        pdf_state="ja",
        value="ja"
    ),

    # AW_26: Belastbarkeit für Rehabilitation (Radiogruppe)
    FormField(
        field_name="AW_26_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Test",
        radio_group="AW_26",
        pdf_state="ja",
        value="ja"
    ),
]

template_path = Path("data/S0051.pdf")
output_path = Path("data/S0051_checkbox_test.pdf")

print("=" * 80)
print("TEST: Korrigierte Checkbox/Radiobutton-Felder (AW_13-AW_26)")
print("=" * 80)
print(f"Template: {template_path}")
print(f"Output: {output_path}")
print(f"Anzahl Test-Felder: {len(test_fields)}")
print()

print("Test-Felder:")
print("  Risikofaktoren (AW_13-AW_19):")
print("    - AW_13 (Bewegungsmangel): Checkbox = ja")
print("    - AW_14 (Übergewicht): Radio = Übergewicht")
print("    - AW_15 (Alkohol): Checkbox = ja")
print("    - AW_16 (Drogen): Checkbox = nein")
print("    - AW_17 (Medikamente): Checkbox = ja")
print("    - AW_18 (Nikotin): Checkbox = ja")
print("    - AW_19 (Sonstiges): Checkbox = nein")
print()
print("  Arbeitsunfähigkeit/Prognose (AW_20-AW_26):")
print("    - AW_20 (Arbeitsunfähigkeit): Radio = ja")
print("    - AW_21 (Befundänderung): Radio = ja")
print("    - AW_22 (Besserung): Radio = Besserung")
print("    - AW_23 (Deutsche Sprache): Radio = ja")
print("    - AW_24 (Reisefähigkeit): Radio = ja + Checkbox (mit Begleitung)")
print("    - AW_25 (Besserung Leistungsfähigkeit): Radio = ja")
print("    - AW_26 (Belastbarkeit): Radio = ja")
print()

try:
    result = fill_pdf(template_path, output_path, test_fields)
    print("=" * 80)
    print("OK: TEST ERFOLGREICH!")
    print(f"  PDF erstellt: {result}")
    print("=" * 80)
    print("\nBitte pruefen Sie die Datei:", output_path)
    print("\nErwartetes Ergebnis:")
    print("  - Alle Risikofaktor-Checkboxen sollten korrekt gesetzt sein")
    print("  - Alle Radio-Buttons sollten auf den richtigen Optionen stehen")
    print("  - Text-Felder sollten ausgefuellt sein")
except Exception as e:
    print("=" * 80)
    print("FEHLER: TEST FEHLGESCHLAGEN!")
    print(f"  Fehler: {e}")
    print("=" * 80)
    import traceback
    traceback.print_exc()
