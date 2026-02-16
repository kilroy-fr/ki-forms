# Textfeld-Vergleichstool für S0051

Dieses Tool vergleicht die Extraktion der sechs großen Textfelder aus dem S0051-Formular zwischen verschiedenen LLM-Modellen.

## Die sechs verglichenen Felder

1. **Antragsrelevante Anamnese**
2. **Funktionseinschränkungen**
3. **Bisherige und aktuelle Therapie**
4. **Untersuchungsbefunde**
5. **Medizinisch-technische Befunde**
6. **Lebensumstände / Kontextfaktoren**

## Voraussetzungen

- Python 3.11+
- Ollama mit den zu vergleichenden Modellen installiert
- Alle Modelle müssen heruntergeladen sein:
  ```bash
  ollama pull qwen2.5:14b
  ollama pull qwen3:14b
  ollama pull gpt-oss:20b
  ```

## Verwendung

### 1. Grundlegende Verwendung

```bash
python compare_text_fields.py
```

Dies verwendet:
- **Quelle:** `uploads/dein_arztbrief.pdf`
- **Modelle:** qwen2.5:14b, qwen3:14b, gpt-oss:20b
- **Ausgabe:** `output/textfield_comparison.html` und `output/textfield_comparison.json`

### 2. Benutzerdefinierte Optionen

```bash
python compare_text_fields.py \
  --pdf "pfad/zu/deinem/arztbrief.pdf" \
  --models qwen2.5:14b qwen3:14b llama3.1:8b \
  --output-html output/mein_vergleich.html \
  --output-json output/mein_vergleich.json
```

### 3. Nur bestimmte Modelle vergleichen

```bash
python compare_text_fields.py --models qwen2.5:14b qwen3:14b
```

## Ausgabeformate

### HTML-Ausgabe

Die HTML-Datei enthält:
- Side-by-Side-Vergleich aller sechs Felder
- Farbcodierung für bessere Lesbarkeit
- Zeichenzahl für jedes extrahierte Feld
- Responsive Design (auch mobil lesbar)
- Druckoptimiert

**Öffnen:** Einfach die HTML-Datei im Browser öffnen

### JSON-Ausgabe

Die JSON-Datei enthält:
- Strukturierte Daten für weitere Analysen
- Metadaten (Zeitstempel, Modelle, etc.)
- Ausführungszeiten pro Modell
- Alle extrahierten Werte mit Zeichenzahlen

## HTML zu PDF konvertieren (optional)

Falls du ein PDF-Dokument benötigst:

### Installation von WeasyPrint

```bash
pip install weasyprint
```

### Konvertierung

```bash
python html_to_pdf.py
```

Oder mit benutzerdefinierten Pfaden:

```bash
python html_to_pdf.py \
  --html output/textfield_comparison.html \
  --pdf output/textfield_comparison.pdf
```

## Beispielausgabe

Nach der Ausführung erhältst du eine Konsolenausgabe wie:

```
================================================================================
VERGLEICH ABGESCHLOSSEN
================================================================================
Quelldokument: uploads/dein_arztbrief.pdf
Modelle: qwen2.5:14b, qwen3:14b, gpt-oss:20b

Ausführungszeiten:
  qwen2.5:14b: 45.2s
  qwen3:14b: 38.7s
  gpt-oss:20b: 52.1s

Extraktionsrate:
  qwen2.5:14b: 6/6 Felder extrahiert
  qwen3:14b: 5/6 Felder extrahiert
  gpt-oss:20b: 6/6 Felder extrahiert

Ausgabedateien:
  HTML: output/textfield_comparison.html
  JSON: output/textfield_comparison.json
================================================================================
```

## Tipps

1. **Lange Laufzeit:** Die Extraktion kann 2-5 Minuten pro Modell dauern. Bei drei Modellen rechne mit 10-15 Minuten Gesamtlaufzeit.

2. **Speicher:** Stelle sicher, dass genug RAM verfügbar ist (mindestens 8GB frei für 14B-Modelle).

3. **Vergleich:** Öffne die HTML-Datei in einem modernen Browser (Chrome, Firefox, Edge) für die beste Darstellung.

4. **Weitere Analysen:** Nutze die JSON-Datei für eigene Auswertungen oder Visualisierungen.

## Fehlerbehebung

### "Modell nicht gefunden"

```bash
# Überprüfe installierte Modelle
ollama list

# Lade fehlendes Modell herunter
ollama pull qwen3:14b
```

### "PDF nicht gefunden"

Stelle sicher, dass der PDF-Pfad korrekt ist:

```bash
python compare_text_fields.py --pdf "uploads/dein_arztbrief.pdf"
```

### "Timeout" oder langsame Ausführung

- Erhöhe das Timeout in `app/config.py` (OLLAMA_TIMEOUT)
- Reduziere die Anzahl der Modelle
- Nutze kleinere Modelle für Tests

## Erweiterte Nutzung

### Nur JSON-Ausgabe analysieren

```python
import json

with open('output/textfield_comparison.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Zeige Zeichenzahlen an
for field_name, field_data in data['comparisons'].items():
    print(f"\n{field_data['label']}:")
    for model, result in field_data['results'].items():
        print(f"  {model}: {result['char_count']} Zeichen")
```

### Eigene Modellkombinationen

Du kannst beliebige Ollama-Modelle vergleichen:

```bash
python compare_text_fields.py --models \
  llama3.1:8b \
  llama3.1:70b \
  mistral:7b \
  gemma2:9b
```
