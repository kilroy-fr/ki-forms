#!/usr/bin/env python3
"""
Test-Script für Aktivitäten-Felder (AW_4-AW_12)
"""
from pathlib import Path
from app.models.form_schema import FormField, FieldType
from app.services.pdf_filler import fill_pdf

# Test-Felder für die Aktivitäten
test_fields = [
    # Text-Feld zum Testen
    FormField(field_name="PAT_NAME", field_type=FieldType.TEXT, label_de="Test", section=0, description="Test", value="Mustermann, Max"),

    # === AKTIVITÄTEN (AW_4-AW_12) ===
    # AW_4: Lernen und Wissensanwendung - Einschränkungen
    FormField(
        field_name="AW_4_einschr",
        field_type=FieldType.RADIO,
        label_de="Einschränkungen",
        section=5,
        description="Test",
        radio_group="AW_4",
        pdf_state="Einschränkungen",
        value="ja"
    ),

    # AW_5: Allgemeine Aufgaben - keine Beeinträchtigungen
    FormField(
        field_name="AW_5_keine",
        field_type=FieldType.RADIO,
        label_de="keine Beeinträchtigungen",
        section=5,
        description="Test",
        radio_group="AW_5",
        pdf_state="keine Beeinträchtigungen",
        value="ja"
    ),

    # AW_6: Kommunikation - Personelle Hilfe nötig
    FormField(
        field_name="AW_6_hilfe",
        field_type=FieldType.RADIO,
        label_de="Personelle Hilfe nötig",
        section=5,
        description="Test",
        radio_group="AW_6",
        pdf_state="Personelle Hilfe nötig",
        value="ja"
    ),

    # AW_7: Mobilität - Einschränkungen
    FormField(
        field_name="AW_7_einschr",
        field_type=FieldType.RADIO,
        label_de="Einschränkungen",
        section=5,
        description="Test",
        radio_group="AW_7",
        pdf_state="Einschränkungen",
        value="ja"
    ),

    # AW_8: Arbeit und Beschäftigung - nicht durchführbar
    FormField(
        field_name="AW_8_nicht",
        field_type=FieldType.RADIO,
        label_de="nicht durchführbar",
        section=5,
        description="Test",
        radio_group="AW_8",
        pdf_state="nicht durchführbar",
        value="ja"
    ),

    # AW_9: Erziehung / Bildung - Keine Angabe möglich
    FormField(
        field_name="AW_9_ka",
        field_type=FieldType.RADIO,
        label_de="Keine Angabe möglich",
        section=5,
        description="Test",
        radio_group="AW_9",
        pdf_state="Keine Angabe möglich",
        value="ja"
    ),

    # AW_10: Interpersonelle Aktivitäten - Einschränkungen
    FormField(
        field_name="AW_10_einschr",
        field_type=FieldType.RADIO,
        label_de="Einschränkungen",
        section=5,
        description="Test",
        radio_group="AW_10",
        pdf_state="Einschränkungen",
        value="ja"
    ),

    # AW_11: Häusliches Leben - keine Beeinträchtigungen
    FormField(
        field_name="AW_11_keine",
        field_type=FieldType.RADIO,
        label_de="keine Beeinträchtigungen",
        section=5,
        description="Test",
        radio_group="AW_11",
        pdf_state="keine Beeinträchtigungen",
        value="ja"
    ),

    # AW_12: Selbstversorgung - Personelle Hilfe nötig
    FormField(
        field_name="AW_12_hilfe",
        field_type=FieldType.RADIO,
        label_de="Personelle Hilfe nötig",
        section=5,
        description="Test",
        radio_group="AW_12",
        pdf_state="Personelle Hilfe nötig",
        value="ja"
    ),
]

template_path = Path("data/S0051.pdf")
output_path = Path("data/S0051_aktivitaeten_test.pdf")

print("=" * 80)
print("TEST: Aktivitaeten-Felder (AW_4-AW_12)")
print("=" * 80)
print(f"Template: {template_path}")
print(f"Output: {output_path}")
print(f"Anzahl Test-Felder: {len(test_fields)}")
print()

print("Test-Felder:")
print("  AW_4 (Lernen): Einschraenkungen")
print("  AW_5 (Aufgaben): keine Beeintraechtigungen")
print("  AW_6 (Kommunikation): Personelle Hilfe noetig")
print("  AW_7 (Mobilitaet): Einschraenkungen")
print("  AW_8 (Arbeit): nicht durchfuehrbar")
print("  AW_9 (Bildung): Keine Angabe moeglich")
print("  AW_10 (Interpersonell): Einschraenkungen")
print("  AW_11 (Haeuslich): keine Beeintraechtigungen")
print("  AW_12 (Selbstversorgung): Personelle Hilfe noetig")
print()

try:
    result = fill_pdf(template_path, output_path, test_fields)
    print("=" * 80)
    print("OK: TEST ERFOLGREICH!")
    print(f"  PDF erstellt: {result}")
    print("=" * 80)
    print("\nBitte pruefen Sie die Datei:", output_path)
    print("\nErwartetes Ergebnis:")
    print("  - Alle 9 Aktivitaeten sollten mit den richtigen Optionen gesetzt sein")
except Exception as e:
    print("=" * 80)
    print("FEHLER: TEST FEHLGESCHLAGEN!")
    print(f"  Fehler: {e}")
    print("=" * 80)
    import traceback
    traceback.print_exc()
