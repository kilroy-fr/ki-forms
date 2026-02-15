#!/usr/bin/env python3
"""
Prüft, welche Felder in einer Session vorhanden sind
"""
import sys
from app.form_definitions.s0051 import S0051_FIELDS
from app.models.form_schema import FieldStatus

# Simuliere eine Session-Initialisierung
fields = []
for f in S0051_FIELDS:
    field_copy = f.model_copy()
    # Keine KI-Extraktion, also bleiben alle Felder leer
    fields.append(field_copy)

print("=" * 80)
print("SESSION-FELDER NACH INITIALISIERUNG")
print("=" * 80)

# Gruppiere nach Sektion
from collections import defaultdict
sections = defaultdict(list)
for f in fields:
    sections[f.section].append(f)

print(f"\nGesamt: {len(fields)} Felder")
print(f"Sektionen: {len(sections)}")

for section_num in sorted(sections.keys()):
    section_fields = sections[section_num]
    print(f"\nSektion {section_num}: {len(section_fields)} Felder")

    # Zähle Typen
    from collections import Counter
    types = Counter(f.field_type.value for f in section_fields)
    for field_type, count in types.items():
        print(f"  - {field_type}: {count}")

    # Zeige Aktivitäten (Sektion 5)
    if section_num == 5:
        radio_groups = defaultdict(list)
        for f in section_fields:
            if f.radio_group:
                radio_groups[f.radio_group].append(f.field_name)

        print(f"\n  Radio-Gruppen in Sektion 5:")
        for group in sorted(radio_groups.keys()):
            print(f"    {group}: {len(radio_groups[group])} Optionen")

print("\n" + "=" * 80)
print("PRÜFUNG: WERDEN AKTIVITÄTEN IM TEMPLATE GEFUNDEN?")
print("=" * 80)

# Simuliere Template-Logik
section_5_fields = sections[5]
print(f"\nSection 5 hat {len(section_5_fields)} Felder")

# Prüfe, ob die Radio-Gruppen gefunden werden
aktivitaeten = [
    ('AW_4', 'Lernen und Wissensanwendung'),
    ('AW_5', 'Allgemeine Aufgaben und Anforderungen'),
    ('AW_6', 'Kommunikation'),
    ('AW_7', 'Mobilität'),
    ('AW_8', 'Arbeit und Beschäftigung'),
    ('AW_9', 'Erziehung / Bildung'),
    ('AW_10', 'Interpersonelle Aktivitäten'),
    ('AW_11', 'Häusl. Leben / Haushaltsführung'),
    ('AW_12', 'Selbstversorgung')
]

print("\nTemplate-Logik für jede Aktivität:")
for radio_group, label in aktivitaeten:
    # Simuliere: {% set group_fields = section_fields | selectattr("radio_group", "equalto", radio_group) | list %}
    group_fields = [f for f in section_5_fields if f.radio_group == radio_group]
    print(f"  {radio_group} ({label}): {len(group_fields)} Felder gefunden")
    if len(group_fields) != 5:
        print(f"    ⚠ WARNUNG: Erwartet 5, gefunden {len(group_fields)}!")
