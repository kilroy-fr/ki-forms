# KI-Forms Projekt - Claude Code Dokumentation

## Projektübersicht

**KI-Forms** ist eine Flask-basierte Webanwendung zur automatisierten Verarbeitung und Ausfüllung von PDF-Formularen mit Hilfe von KI (Ollama). Das System extrahiert Informationen aus gescannten oder digitalen Dokumenten, interpretiert sie mit einem LLM und füllt strukturierte PDF-Formulare aus.

### Hauptfunktionen
- Upload von PDF-Dokumenten
- OCR-basierte Textextraktion mit Tesseract
- KI-gestützte Feldextraktion mittels Ollama (Qwen2.5:14b)
- Automatisches Ausfüllen von PDF-Formularen
- Session-basierter Workflow mit Review-Möglichkeit
- Download ausgefüllter Formulare

## Technologie-Stack

### Backend
- **Framework**: Flask 3.1.0
- **PDF-Verarbeitung**: pikepdf 9.4.2, pypdf 5.1.0
- **OCR**: pytesseract 0.3.13, pdf2image 1.17.0
- **LLM**: Ollama (über HTTP API)
- **Server**: Gunicorn 23.0.0

### Frontend
- HTML Templates (Jinja2)
- JavaScript (vanilla)
- CSS

### Python Version
- Python 3.12

## Projektstruktur

```
ki-forms/
├── app/
│   ├── main.py                    # Flask App-Initialisierung
│   ├── config.py                  # Konfiguration & Umgebungsvariablen
│   ├── form_registry.py           # Zentrale Formular-Registry
│   ├── routers/
│   │   └── forms.py               # Haupt-Router für Formular-Workflow
│   ├── services/
│   │   ├── pdf_reader.py          # PDF-Parsing & OCR
│   │   └── field_extractor.py     # Ollama-basierte KI-Extraktion
│   ├── models/
│   │   └── form_schema.py         # Datenmodelle für Formulare
│   ├── form_handlers/             # Formular-spezifische Handler (NEU)
│   │   ├── base_handler.py        # Abstrakte Basis-Klasse
│   │   ├── s0050_handler.py       # S0050-Handler
│   │   └── s0051_handler.py       # S0051-Handler
│   ├── form_definitions/          # Formular-Feld-Definitionen
│   │   ├── s0051.py               # S0051 Formular-Felder
│   │   └── s0050.py               # S0050 Formular-Felder
│   ├── templates/                 # HTML Templates
│   │   ├── index.html
│   │   ├── review.html
│   │   └── download.html
│   └── static/                    # CSS & JavaScript
│       ├── css/style.css
│       └── js/upload.js
├── data/                          # Formular-Templates & Konfiguration
├── output/                        # Ausgabe-Verzeichnis für gefüllte PDFs
├── requirements.txt               # Python Dependencies
├── VERSION                        # Versionsnummer (automatisch aktualisiert)
└── CLAUDE.md                      # Diese Datei
```

## Wichtige Konventionen

### Code-Stil
- **Deutsche Kommentare**: Code-Kommentare sind auf Deutsch
- **Encoding**: UTF-8 überall
- **Line Endings**: LF (Unix-Style) bevorzugt
- **Indentation**: 4 Spaces

### Formular-Definitionen
- Jedes Formular hat eine eigene Datei in `app/form_definitions/`
- Namenskonvention: `s####.py` (z.B. `s0051.py`)
- Enthält Feld-Mappings und formularspezifische Logik

### Session-Management
- In-Memory Sessions (nicht persistent)
- Session-ID: UUID4
- Speichert hochgeladene Dateien, extrahierte Daten und Formularzustand

### Datumsformate
- Standard-Eingabeformat: DD.MM.YYYY
- Flexible Parsing für verschiedene Formate

### Encoding-Probleme
- Aktive Normalisierung für Umlaute (ä, ö, ü, ß)
- Siehe `_normalize_radio_text()` in forms.py
- Bekannte Probleme mit PDF-Encoding werden automatisch behandelt

## Umgebungsvariablen

Konfiguration über `.env` oder Umgebungsvariablen:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:14b
OLLAMA_TIMEOUT=300
MAX_OLLAMA_PASSES=3

# Directories
UPLOAD_DIR=/app/uploads
OUTPUT_DIR=/app/output
FORM_TEMPLATE_DIR=/app/data

# Limits
MAX_UPLOAD_SIZE_MB=50
MAX_UPLOAD_FILES=10

# OCR
OCR_LANGUAGE=deu
OCR_DPI=300
```

## Workflow

1. **Upload** (`/` → index.html)
   - Benutzer lädt ein oder mehrere PDFs hoch
   - Session wird erstellt

2. **Verarbeitung** (`POST /upload`)
   - OCR-Extraktion des Textes
   - Ollama-basierte Feldextraktion
   - Mehrere Pässe für große Textfelder

3. **Review** (`/review/<session_id>`)
   - Benutzer überprüft/korrigiert extrahierte Daten
   - Interaktive Formular-UI

4. **Download** (`POST /finalize/<session_id>`)
   - PDF wird ausgefüllt
   - Download-Link wird bereitgestellt

## Bekannte Besonderheiten

### PDF-Feldtypen
- **Checkboxen**: Komplexe Widget-States, verschiedene "On"-Werte
- **Radio-Buttons**: Gruppierung und Normalisierung erforderlich
- **Textfelder**: Automatisches Line-Wrapping
- **Datumsfelder**: Flexible Parsing-Logik

### Ollama-Integration
- Multi-Pass-Strategie für komplexe Felder
- Timeout-Handling (300s Standard)
- Fehlerbehandlung bei Verbindungsabbrüchen

### Encoding-Herausforderungen
- PDF-interne Encoding-Probleme (besonders bei Umlauten)
- Automatische Normalisierung und Fallback-Logik

## Entwicklungs-Befehle

```bash
# Virtual Environment aktivieren
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Dependencies installieren
pip install -r requirements.txt

# App starten (Development)
python -m flask --app app.main run --debug

# Mit Gunicorn (Production)
gunicorn "app.main:app" --bind 0.0.0.0:8000
```

## Testing & Debugging

Das Projekt enthält verschiedene Test- und Debug-Skripte im Root:
- `test_pdf_filling.py` - PDF-Füll-Tests
- `verify_field_mapping.py` - Feld-Mapping-Validierung
- `debug_fields.py` - Field-Debugging
- `benchmark_models.py` - Modell-Benchmarking

## Git-Workflow

- **Main Branch**: `master`
- Commit-Messages auf Deutsch
- Auto-Versionierung über `VERSION` Datei

## Architektur: Form Handler Pattern

**Seit 2026-02-18**: Das Projekt nutzt ein Handler-basiertes Pattern für bessere Skalierbarkeit.

### Handler-Konzept

Jedes Formular hat drei Komponenten:

1. **FormDefinition** (`app/form_definitions/s####.py`)
   - Liste aller Felder mit Typen, Labels, Sektionen
   - Reine Datenstruktur, keine Logik
   - Beispiel: `S0051_DEFINITION`

2. **FormHandler** (`app/form_handlers/s####_handler.py`)
   - Erbt von `BaseFormHandler`
   - Enthält formular-spezifische Logik:
     - Sektionsnamen (`get_section_titles()`)
     - Long-Text-Felder (`get_long_text_fields()`)
     - Preprocessing Hook (vor KI-Extraktion)
     - Postprocessing Hook (nach KI-Extraktion, z.B. Sender-Daten einfügen)
     - Finalization Hook (z.B. S0050 aus S0051 generieren)

3. **Registry-Eintrag** (`app/form_registry.py`)
   - Verbindet Definition und Handler
   - Metadaten (Template-Dateiname, abhängige Formulare)

### Lifecycle Hooks

Handler bieten vier Hooks für formular-spezifische Logik:

```python
class MyFormHandler(BaseFormHandler):
    def preprocess_fields(self, fields, source_text, session_data):
        """Hook VOR KI-Extraktion - z.B. Felder hinzufügen"""
        return fields

    def postprocess_fields(self, fields, extracted_results, session_data):
        """Hook NACH KI-Extraktion - z.B. Sender-Daten einfügen, Feldkopien"""
        return fields

    def on_generate_pdf(self, fields, session_id, output_path):
        """Hook beim PDF-Generieren - z.B. Logging"""
        pass

    def on_finalize(self, fields_by_name, session_id):
        """Hook nach Finalisierung - z.B. abhängige PDFs generieren"""
        pass
```

## Typische Aufgaben

### Neues Formular hinzufügen

**Nur 3 Dateien erforderlich:**

1. **PDF-Template** in `data/` ablegen (z.B. `S0099.pdf`)

2. **Formular-Definition** erstellen: `app/form_definitions/s0099.py`
   ```python
   from app.models.form_schema import FormField, FieldType, FormDefinition

   S0099_FIELDS = [
       FormField(field_name="PATIENT_NAME", field_type=FieldType.TEXT, ...),
       # ... weitere Felder
   ]

   S0099_DEFINITION = FormDefinition(
       form_id="S0099",
       form_title="Mein neues Formular",
       fields=S0099_FIELDS,
   )
   ```

3. **Handler** erstellen: `app/form_handlers/s0099_handler.py`
   ```python
   from .base_handler import BaseFormHandler

   class S0099FormHandler(BaseFormHandler):
       def get_section_titles(self):
           return {
               0: "Kopfdaten",
               1: "Patienteninformationen",
               # ...
           }

       def get_long_text_fields(self):
           return {"ANAMNESE", "BEMERKUNGEN"}

       # Optional: Hooks überschreiben für spezifische Logik
   ```

4. **Registrieren** in `app/form_registry.py`
   ```python
   # Import hinzufügen
   from app.form_definitions.s0099 import S0099_DEFINITION
   from app.form_handlers.s0099_handler import S0099FormHandler

   # In _initialize_registry():
   registry.register(FormRegistryEntry(
       form_id="S0099",
       definition=S0099_DEFINITION,
       handler_class=S0099FormHandler,
       template_filename="S0099.pdf",
       description="Mein neues Formular",
       enabled=True,
   ))
   ```

**Das war's!** Keine Änderungen an `forms.py` nötig.

### Feld-Extraktion verbessern
- `app/services/field_extractor.py` anpassen
- Ollama-Prompts optimieren
- Multi-Pass-Strategie erweitern

### UI/UX Änderungen
- Templates in `app/templates/`
- Styles in `app/static/css/style.css`
- JavaScript in `app/static/js/`

## Wichtige Hinweise für Claude Code

1. **Encoding**: Immer UTF-8 verwenden, besonders bei deutschen Umlauten
2. **Pfade**: Windows-Pfade beachten (Backslashes in Strings escapen)
3. **Testing**: Vor größeren Änderungen bestehende Test-Skripte nutzen
4. **PDF-Manipulation**: pikepdf ist das primäre Tool, pypdf als Fallback
5. **Sessions**: In-Memory, nicht persistent - bei Restart verloren
6. **Ollama**: Externe Abhängigkeit - Verfügbarkeit prüfen

## Deployment

### Docker Setup

Das Projekt ist vollständig containerisiert und nutzt Docker für Deployment.

#### Dockerfile
- **Base Image**: `python:3.12-slim`
- **System-Dependencies**: Tesseract OCR (mit deutschem Sprachpaket), Poppler-utils
- **Port**: 8000
- **Workers**: 2 Gunicorn-Worker
- **Timeout**: 600 Sekunden (für lange OCR/KI-Operationen)

#### Docker Compose

```bash
# Build und Start
docker-compose up -d --build

# Logs anzeigen
docker-compose logs -f app

# Container neu starten
docker-compose restart app

# Herunterfahren
docker-compose down
```

**Wichtige Netzwerke**:
- `caddy-proxy-network`: Externe Verbindung zum Reverse-Proxy (Caddy)
- `ollama-net`: Externe Verbindung zum Ollama-Service

**Volumes**:
- `uploads`: Persistente Speicherung hochgeladener Dateien
- `output`: Persistente Speicherung generierter PDFs

#### Produktions-Deployment

```bash
# 1. Repository klonen
git clone <repo-url>
cd ki-forms

# 2. Umgebungsvariablen konfigurieren
cp .env.example .env
# .env bearbeiten mit korrekten Werten

# 3. Netzwerke erstellen (falls noch nicht vorhanden)
docker network create caddy-proxy-network
docker network create ollama-net

# 4. Ollama-Service sicherstellen
# Muss separat laufen und im ollama-net sein

# 5. Container starten
docker-compose up -d

# 6. Health-Check
curl http://localhost:8000/
```

### Systemanforderungen

**Minimum**:
- 2 CPU Cores
- 4 GB RAM
- 10 GB Speicherplatz

**Empfohlen** (für Multi-User-Betrieb):
- 4+ CPU Cores
- 8+ GB RAM
- 50+ GB Speicherplatz (für Uploads/Outputs)

**Externe Dependencies**:
- Ollama-Server mit Qwen2.5:14b Modell (ca. 8 GB VRAM)
- Reverse-Proxy (Caddy empfohlen)

## API-Dokumentation

### Endpunkte

#### `GET /`
**Beschreibung**: Hauptseite mit Formularauswahl und Download-Übersicht
**Parameter**:
- `session` (optional): Session-ID für Download-Anzeige
- `form` (optional): Formular-ID für Download-Anzeige
**Response**: HTML (index.html)

#### `GET /form/<form_id>/thumbnail`
**Beschreibung**: Generiert Thumbnail der ersten Seite eines Formulars
**Parameter**:
- `form_id`: ID des Formulars (z.B. "S0051")
**Response**: JPEG-Bild (200px Höhe)

#### `GET /form/<form_id>/upload`
**Beschreibung**: Upload-Seite für ein spezifisches Formular
**Parameter**:
- `form_id`: ID des Formulars
**Response**: HTML (upload.html)

#### `POST /form/<form_id>/process`
**Beschreibung**: Verarbeitet hochgeladene PDFs mit OCR und KI-Extraktion
**Parameter**:
- `form_id`: ID des Zielformulars
**Body**: `multipart/form-data` mit PDF-Dateien
**Response**: Redirect zu `/review/<session_id>`
**Verarbeitung**:
1. PDF-Upload validieren
2. OCR-Texterkennung durchführen
3. Ollama-basierte Feldextraktion
4. Session anlegen mit extrahierten Daten

#### `GET /review/<session_id>`
**Beschreibung**: Review-Seite für extrahierte Formulardaten
**Parameter**:
- `session_id`: UUID der Session
**Response**: HTML (review.html) mit Formularfeldern

#### `POST /update/<session_id>`
**Beschreibung**: Aktualisiert Formulardaten während Review
**Parameter**:
- `session_id`: UUID der Session
**Body**: JSON mit Feldwerten
**Response**: JSON `{"status": "ok"}`

#### `POST /finalize/<session_id>`
**Beschreibung**: Finalisiert Formular und generiert ausgefülltes PDF
**Parameter**:
- `session_id`: UUID der Session
**Response**: Redirect zu `/?session=<id>&form=<form_id>`
**Prozess**:
1. Formular-Template laden
2. Felder ausfüllen (pikepdf)
3. PDF speichern in `output/`
4. Bei S0051: Auch S0050 generieren

#### `GET /download/<form_id>/<session_id>`
**Beschreibung**: Download des ausgefüllten PDFs
**Parameter**:
- `form_id`: ID des Formulars
- `session_id`: UUID der Session
**Response**: PDF-Datei als Download

### Formular-Registry

Verfügbare Formulare werden dynamisch über `_get_form_registry()` geladen:

```python
{
    "S0050": S0050_DEFINITION,
    "S0051": S0051_DEFINITION,
}
```

Jede Definition enthält:
- `id`: Formular-ID
- `name`: Anzeigename
- `description`: Beschreibung
- `template_path`: Pfad zur PDF-Vorlage
- `fields`: Liste von FormField-Objekten

## Code-Review-Richtlinien

### Sicherheit

**KRITISCH - Immer prüfen**:
- ❌ **Keine User-Inputs direkt in Shell-Commands** (Command Injection)
- ❌ **Keine unsicheren File-Operations** (Path Traversal)
  - Immer `Path.resolve()` nutzen und gegen parent-directory checken
- ❌ **Keine SQL-Injections** (aktuell nicht relevant, da keine DB)
- ✅ **File-Upload-Validierung**: Nur PDFs erlaubt, Größen-Limits beachten
- ✅ **Session-IDs**: Nur UUIDs verwenden, keine sequential IDs

**Ollama-Prompts**:
- User-Input darf nie direkt als System-Prompt verwendet werden
- Immer klare Trennung zwischen System- und User-Content
- Keine dynamischen Prompt-Injections

### Performance

**Best Practices**:
- OCR nur wenn nötig (nicht bei digitalen PDFs)
- Caching nutzen (z.B. ICD-10-Codes)
- Ollama-Timeouts angemessen setzen
- Große Textfelder in separaten Pässen verarbeiten (siehe `LARGE_TEXT_FIELDS`)
- Thumbnail-Generierung nur on-demand

### Code-Qualität

**Stil**:
- Type Hints verwenden: `def func(param: str) -> dict:`
- Docstrings für komplexe Funktionen (Deutsch)
- Logging statt Print-Statements
- Sinnvolle Variablennamen (Deutsch für domain-spezifisch, Englisch für generisch)

**Error Handling**:
- Spezifische Exceptions catchen, nicht `except Exception`
- User-freundliche Fehlermeldungen (Deutsch)
- Kritische Fehler loggen mit `logger.error()`

**Testing**:
- Bestehende Test-Skripte nach Änderungen ausführen
- Manuelle Tests mit echten PDFs vor Deployment

### Nicht tun

❌ Keine Breaking Changes ohne explizite Anfrage
❌ Keine dependency-Updates ohne Testing
❌ Keine Änderungen am PDF-Template-Format
❌ Keine Session-Persistierung (bewusst in-memory)
❌ Keine automatischen Migrations oder DB-Schemen

## Troubleshooting

### Häufige Probleme

#### 1. OCR funktioniert nicht

**Symptome**: Leere Textextraktion, Fehler bei pdf2image

**Lösungen**:
```bash
# Tesseract installiert?
tesseract --version

# Deutsche Sprachdaten vorhanden?
tesseract --list-langs | grep deu

# Poppler installiert?
pdftoppm -v

# In Docker: Image neu bauen
docker-compose build --no-cache
```

#### 2. Ollama-Verbindung schlägt fehl

**Symptome**: Timeout-Fehler, "Connection refused"

**Lösungen**:
```bash
# Ollama-Service läuft?
docker ps | grep ollama

# Netzwerk korrekt?
docker network inspect ollama-net

# Modell verfügbar?
docker exec -it <ollama-container> ollama list

# Modell laden
docker exec -it <ollama-container> ollama pull qwen2.5:14b

# OLLAMA_BASE_URL korrekt?
echo $OLLAMA_BASE_URL
```

#### 3. PDF-Felder werden nicht gefüllt

**Symptome**: Leeres PDF, Felder nicht ausgefüllt

**Debug-Schritte**:
```python
# Feld-Namen überprüfen
python check_pdf_fields.py data/S0051.pdf

# Session-Daten inspizieren
# In forms.py logging hinzufügen:
logger.info(f"Session data: {sessions[session_id]}")

# Feld-Mapping verifizieren
python verify_field_mapping.py
```

**Häufige Ursachen**:
- Feld-Namen in PDF geändert
- Encoding-Probleme bei Umlauten
- Checkbox-States nicht korrekt
- Radio-Button-Gruppierung falsch

#### 4. Umlaute werden falsch dargestellt

**Symptome**: "Ã¤" statt "ä", "鋍" statt "ä"

**Lösung**:
- Bereits implementiert in `_normalize_radio_text()`
- Bei neuen Fällen: Mapping erweitern
- UTF-8 Encoding überprüfen

#### 5. Session verloren nach Server-Restart

**Erwartetes Verhalten**: Sessions sind bewusst nicht persistent!

**Workaround**:
- Benutzer informieren vor Restart
- Evtl. File-basierte Session-Speicherung implementieren (falls erforderlich)

#### 6. Upload schlägt fehl

**Symptome**: 413 Request Entity Too Large

**Lösungen**:
```python
# MAX_UPLOAD_SIZE_MB erhöhen
# In .env:
MAX_UPLOAD_SIZE_MB=100

# Gunicorn-Timeout erhöhen (Dockerfile):
CMD ["gunicorn", "app.main:app", "--timeout", "900"]
```

#### 7. Speicherplatz-Probleme

**Symptome**: "No space left on device"

**Cleanup**:
```bash
# Alte Uploads löschen
rm -rf uploads/*

# Alte Outputs löschen
rm -rf output/*

# Docker-Volumes bereinigen (Achtung: Datenverlust!)
docker-compose down -v
docker volume prune
```

### Logs und Debugging

```bash
# Flask Development Logs
python -m flask --app app.main run --debug

# Docker Logs
docker-compose logs -f app

# Ollama Logs
docker-compose logs -f ollama  # falls im selben compose

# Python Logging Level erhöhen
# In app/main.py:
logging.basicConfig(level=logging.DEBUG)
```

### Performance-Optimierung

**Langsame OCR**:
- DPI reduzieren in pdf2image (aktuell: 200)
- Nur relevante Seiten scannen
- Parallel-Processing erwägen

**Langsame Ollama-Requests**:
- Kleineres Modell testen (z.B. qwen2.5:7b)
- GPU-Beschleunigung sicherstellen
- Ollama auf dedizierter Hardware

**Hoher RAM-Verbrauch**:
- Session-Cleanup implementieren (TTL)
- Gunicorn-Workers reduzieren
- File-basierte statt in-memory Sessions

## Version Management

Die Version wird automatisch in der `VERSION`-Datei verwaltet. Aktualisierungen erfolgen bei relevanten Änderungen manuell oder automatisiert.

---

**Letzte Aktualisierung**: 2026-02-17
**Claude Code**: Nutze diese Datei als Referenz für alle Projektarbeiten
