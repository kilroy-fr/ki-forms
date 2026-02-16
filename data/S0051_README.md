# S0051 Formulardefinitionen

## Aktuelle Dateien (Stand: 2026-02-14)

### Korrekte Feldstruktur:
- **`S0051_Checkboxes.txt`** - Vollständige und korrekte Liste aller Checkbox- und Radiobutton-Felder mit ihren tatsächlichen PDF-Feldnamen
- **`app/form_definitions/s0051.py`** - Python-Formulardefinition (aktualisiert)

### Veraltete Dateien (NICHT MEHR VERWENDEN):
- **`VERALTET_S0051_Felder.csv`** - Enthält falsche Feldnamen und falsche Feldtypen
- **`VERALTET_S0051_Feldliste.txt`** - Enthält veraltete Feldliste

## Wichtige Änderungen

### Risikofaktoren (Sektion 10):
Die Feldnummern wurden korrigiert:
- **AW_13** = Bewegungsmangel (Checkbox)
- **AW_14** = Über-/Untergewicht (Radiogruppe mit 2 Optionen)
  - AW_14#0 = "Übergewicht"
  - AW_14#1 = "Untergewicht"
- **AW_15** = Alkohol (Checkbox)
- **AW_16** = Drogen (Checkbox)
- **AW_17** = Medikamente (Checkbox)
- **AW_18** = Nikotin (Checkbox)
- **AW_19** = Sonstiges (Checkbox)

### Arbeitsunfähigkeit/Prognose (Sektion 11):
Die Feldnummern wurden korrigiert:
- **AW_20** = Arbeitsunfähigkeit (ja/nein)
- **AW_21** = Befundänderung in den letzten 12 Monaten (ja/nein)
- **AW_22** = Besserung/Verschlechterung (nur wenn AW_21=ja)
  - AW_22#0 = "Besserung"
  - AW_22#1 = "Verschlechterung"
- **AW_23** = Verständigung in deutscher Sprache (ja/nein)
- **AW_24** = Reisefähigkeit (ja/nein)
- **AW_25** = Besserung der Leistungsfähigkeit (ja/nein/kann ich nicht beurteilen)
- **AW_26** = Belastbarkeit für Rehabilitation (ja/nein)

## PDF On-State Namen

Die tatsächlichen On-State-Namen im PDF (ermittelt mit `extract_radio_states.py`):

| Feld | States |
|------|--------|
| AW_1 | "Leistungen zur medizinischen Rehabilitation", "Leistungen zur onkologischen Rehabilitation", "Leistungen zur Teilhabe am Arbeitsleben (LTA) ", "Erwerbsminderungsrente", "Sonstiges" |
| AW_2 | "wöchentlich", "14-tägig", "monatlich", "seltener" |
| AW_3 | "nein", "ja" |
| AW_4-AW_12 | "keine Beeinträchtigungen", "Einschränkungen", "Personelle Hilfe nötig", "nicht durchführbar", "Keine Angabe möglich" |
| AW_14 | "Übergewicht", "Untergewicht" |
| AW_20-AW_26 | "nein", "ja" (AW_25 zusätzlich: "kann ich nicht beurteilen") |
| AW_22 | "Besserung", "Verschlechterung" |

## Modellvergleich (A/B-Test)

Fuer einen objektiven Vergleich der Extraktionsmodelle:

1. Beispiel-Quelldaten: `data/benchmark_s0051_source.txt`
2. Gold-Referenz: `data/benchmark_s0051_gold.json`
3. Benchmark-Skript: `benchmark_models.py`

Beispielaufruf:

```bash
python benchmark_models.py --models qwen2.5:14b qwen3:14b llama3.1:8b --runs 3
```

Ergebnis:
- Konsolenausgabe mit Ranking (Score + Laufzeit)
- Detail-JSON in `output/model_benchmark_s0051.json`
