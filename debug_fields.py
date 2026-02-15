#!/usr/bin/env python3
"""
Debug-Script um zu prüfen, welche Felder in der Session gespeichert sind
"""
from app.form_definitions.s0051 import S0051_FIELDS

print("=" * 80)
print("SEKTION 5: AKTIVITÄTEN UND TEILHABE")
print("=" * 80)

aktivitaeten_felder = [f for f in S0051_FIELDS if f.section == 5]

print(f"\nAnzahl Felder in Sektion 5: {len(aktivitaeten_felder)}")
print()

# Gruppiere nach radio_group
from collections import defaultdict
groups = defaultdict(list)
for f in aktivitaeten_felder:
    if f.radio_group:
        groups[f.radio_group].append(f)

print("Radio-Gruppen:")
for group_name in sorted(groups.keys()):
    fields = groups[group_name]
    print(f"\n{group_name}: {len(fields)} Optionen")
    for f in fields:
        print(f"  - {f.field_name}: {f.label_de} (pdf_state={f.pdf_state})")

print("\n" + "=" * 80)
print("SEKTION 10: RISIKOFAKTOREN")
print("=" * 80)

risiko_felder = [f for f in S0051_FIELDS if f.section == 10]
print(f"\nAnzahl Felder in Sektion 10: {len(risiko_felder)}")
print()

print("Checkboxen:")
checkboxen = [f for f in risiko_felder if f.field_type.value == "checkbox"]
for f in checkboxen:
    print(f"  - {f.field_name}: {f.label_de}")

print("\nRadiogruppen:")
radio_groups = defaultdict(list)
for f in risiko_felder:
    if f.radio_group:
        radio_groups[f.radio_group].append(f)

for group_name in sorted(radio_groups.keys()):
    fields = radio_groups[group_name]
    print(f"\n{group_name}: {len(fields)} Optionen")
    for f in fields:
        print(f"  - {f.field_name}: {f.label_de} (pdf_state={f.pdf_state})")
