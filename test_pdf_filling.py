#!/usr/bin/env python3
"""
Test-Skript um zu prüfen, ob die korrigierten Feldnamen ins PDF geschrieben werden
"""
from pathlib import Path
from app.models.form_schema import FormField, FieldType
from app.services.pdf_filler import fill_pdf

# Testdaten mit den neuen Feldnamen
test_fields = [
    # Textfelder
    FormField(field_name="VERS_PLZ", field_type=FieldType.TEXT, label_de="Test", section=0, description="Test", value="12345 Teststadt"),
    FormField(field_name="VERS_BEHANDLUNG", field_type=FieldType.TEXT, label_de="Test", section=1, description="Test", value="01.01.2024"),
    FormField(field_name="VERS_KONTAKT_AM", field_type=FieldType.TEXT, label_de="Test", section=1, description="Test", value="15.02.2024"),
    FormField(field_name="TELEFONNUMMER_FÜR_RÜCKFRAGEN", field_type=FieldType.TEXT, label_de="Test", section=1, description="Test", value="01234567890"),
    FormField(field_name="VERS_DIAGNOSE_1", field_type=FieldType.TEXT, label_de="Test", section=2, description="Test", value="Testdiagnose 1"),
    FormField(field_name="VERS_DIAGNOSESCH_1", field_type=FieldType.TEXT, label_de="Test", section=2, description="Test", value="M54.5"),
    FormField(field_name="VERS_KOERPERLAENGE", field_type=FieldType.TEXT, label_de="Test", section=7, description="Test", value="180"),
    FormField(field_name="VERS_GEWICHT", field_type=FieldType.TEXT, label_de="Test", section=7, description="Test", value="75"),
    FormField(field_name="MED_TECHN_BEFUNDE", field_type=FieldType.TEXT, label_de="Test", section=8, description="Test", value="Testbefund"),

    # Radio-Button-Test
    FormField(
        field_name="AW_16_ja",
        field_type=FieldType.RADIO,
        label_de="Test",
        section=11,
        description="Test",
        radio_group="AW_16",
        pdf_state="ja",
        value="ja"
    ),
    FormField(
        field_name="AW_17_ja",
        field_type=FieldType.RADIO,
        label_de="Test",
        section=10,
        description="Test",
        radio_group="AW_17",
        pdf_state="ja",
        value="ja"
    ),
]

template_path = Path("data/S0051.pdf")
output_path = Path("data/S0051_test_ausgefuellt.pdf")

print("Starte PDF-Füllung...")
print(f"Template: {template_path}")
print(f"Output: {output_path}")
print(f"Anzahl Felder: {len(test_fields)}")
print()

try:
    result = fill_pdf(template_path, output_path, test_fields)
    print(f"✓ PDF erfolgreich erstellt: {result}")
    print("\nBitte prüfen Sie die Datei data/S0051_test_ausgefuellt.pdf")
except Exception as e:
    print(f"✗ Fehler beim Füllen des PDFs: {e}")
    import traceback
    traceback.print_exc()
