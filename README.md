# KI-Forms

Automatisierte Verarbeitung und Ausfüllung von PDF-Formularen mit Hilfe von KI. Das System extrahiert Informationen aus gescannten oder digitalen PDF-Dokumenten per OCR, interpretiert sie mit einem lokalen LLM (Ollama) und füllt strukturierte PDF-Formulare aus.

## Features

- **PDF-Upload** - Hochladen von gescannten oder digitalen PDF-Dokumenten
- **OCR-Texterkennung** - Automatische Textextraktion mit Tesseract (deutsch)
- **KI-Feldextraktion** - Lokale LLM-basierte Interpretation mit Ollama (Qwen2.5)
- **Review-Workflow** - Extrahierte Daten prüfen und korrigieren vor dem Ausfüllen
- **PDF-Ausfüllung** - Automatisches Befüllen von PDF-Formularen
- **Multi-Formular** - Erweiterbare Architektur für verschiedene Formulartypen

## Voraussetzungen

- **Docker** und **Docker Compose**
- **Ollama** mit dem Modell `qwen2.5:14b` (oder einem anderen kompatiblen Modell)
- Mindestens 4 GB RAM, 8+ GB empfohlen

## Schnellstart

### 1. Repository klonen

```bash
git clone https://github.com/kilroy-fr/ki-forms.git
cd ki-forms
```

### 2. Konfiguration

```bash
cp .env.example .env
# .env nach Bedarf anpassen (Ollama-URL, Modell, etc.)
```

Absenderdaten konfigurieren:
```bash
cp data/sender_data.example.json data/sender_data.json
# data/sender_data.json mit eigenen Praxis-/Absenderdaten befüllen
```

### 3. Docker-Netzwerke erstellen

```bash
docker network create caddy-proxy-network
docker network create ollama-net
```

> **Hinweis:** Ollama muss separat laufen und im `ollama-net` erreichbar sein.

### 4. Starten

```bash
docker-compose up -d --build
```

Die App ist dann unter `http://localhost:8000` erreichbar.

### Lokale Entwicklung (ohne Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
python -m flask --app app.main run --debug
```

Voraussetzungen für lokale Entwicklung:
- Python 3.12+
- Tesseract OCR mit deutschem Sprachpaket (`tesseract-ocr-deu`)
- Poppler-utils (für `pdf2image`)

## Architektur

```
ki-forms/
├── app/
│   ├── main.py                  # Flask-App
│   ├── config.py                # Konfiguration
│   ├── form_registry.py         # Formular-Registry
│   ├── routers/forms.py         # HTTP-Routen
│   ├── services/
│   │   ├── pdf_reader.py        # PDF-Parsing & OCR
│   │   ├── pdf_filler.py        # PDF ausfüllen
│   │   ├── field_extractor.py   # KI-Feldextraktion
│   │   └── ollama_client.py     # Ollama-API-Client
│   ├── models/form_schema.py    # Datenmodelle
│   ├── form_handlers/           # Formular-spezifische Handler
│   └── form_definitions/        # Feld-Definitionen pro Formular
├── data/                        # PDF-Templates & Konfiguration
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### Workflow

1. **Upload** - PDF-Dokumente hochladen
2. **OCR** - Texterkennung aus gescannten PDFs
3. **KI-Extraktion** - LLM extrahiert strukturierte Daten aus dem Text
4. **Review** - Benutzer prüft und korrigiert die extrahierten Werte
5. **PDF-Ausfüllung** - Formular wird automatisch ausgefüllt und steht zum Download bereit

### Neues Formular hinzufügen

Das Projekt nutzt ein Handler-Pattern. Für ein neues Formular sind nur 3 Dateien nötig:

1. **PDF-Template** in `data/` ablegen
2. **Feld-Definition** in `app/form_definitions/` erstellen
3. **Handler** in `app/form_handlers/` erstellen
4. In `app/form_registry.py` registrieren

Details siehe [CLAUDE.md](CLAUDE.md).

## Konfiguration

Alle Einstellungen über Umgebungsvariablen (siehe [.env.example](.env.example)):

| Variable | Standard | Beschreibung |
|----------|----------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama-Server URL |
| `OLLAMA_MODEL` | `qwen2.5:14b` | LLM-Modell für Extraktion |
| `OLLAMA_TIMEOUT` | `300` | Timeout in Sekunden |
| `MAX_UPLOAD_SIZE_MB` | `50` | Max. Upload-Größe |
| `OCR_LANGUAGE` | `deu` | Tesseract-Sprache |

## Technologie-Stack

- **Backend**: Flask, Gunicorn
- **PDF**: pikepdf, pypdf
- **OCR**: Tesseract, pdf2image
- **KI**: Ollama (lokal, kein Cloud-API nötig)
- **Containerisierung**: Docker

## Lizenz

Dieses Projekt steht unter keiner expliziten Lizenz. Alle Rechte vorbehalten.
