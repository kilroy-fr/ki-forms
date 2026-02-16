"""
Vergleichstool für große Textfelder aus dem S0051-Formular.
Extrahiert die sechs wichtigen Textfelder mit verschiedenen Modellen
und erstellt einen übersichtlichen HTML/PDF-Vergleich.
"""
import argparse
import json
import logging
import time
from pathlib import Path
from typing import Dict, List

from app.config import settings
from app.form_definitions.s0051 import S0051_DEFINITION
from app.services.field_extractor import extract_fields
from app.services.pdf_reader import extract_text_from_pdf

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Die sechs großen Textfelder, die verglichen werden sollen
TARGET_FIELDS = [
    "ANAMNESE",
    "FUNKTIONSEINSCHRAENKUNGEN",
    "THERAPIE",
    "UNTERSUCHUNGSBEFUNDE",
    "MED_TECHN_BEFUNDE",
    "LEBENSUMSTAENDE",
]

FIELD_LABELS = {
    "ANAMNESE": "Antragsrelevante Anamnese",
    "FUNKTIONSEINSCHRAENKUNGEN": "Funktionseinschränkungen",
    "THERAPIE": "Bisherige und aktuelle Therapie",
    "UNTERSUCHUNGSBEFUNDE": "Untersuchungsbefunde",
    "MED_TECHN_BEFUNDE": "Medizinisch-technische Befunde",
    "LEBENSUMSTAENDE": "Lebensumstände / Kontextfaktoren",
}


def extract_with_model(model_name: str, source_text: str) -> Dict[str, str]:
    """
    Extrahiert Felder mit einem bestimmten Modell.

    Returns:
        Dict mit field_name -> extrahierter Wert
    """
    logger.info(f"=== Starte Extraktion mit Modell: {model_name} ===")

    # Modell temporär setzen
    original_model = settings.OLLAMA_MODEL
    settings.OLLAMA_MODEL = model_name

    start_time = time.perf_counter()
    try:
        # Feldextraktion durchführen
        fields = [f.model_copy() for f in S0051_DEFINITION.fields]
        results = extract_fields(fields, source_text)

        # In Dict umwandeln
        result_dict = {}
        for result in results:
            if result.field_name in TARGET_FIELDS:
                result_dict[result.field_name] = result.value

        elapsed = time.perf_counter() - start_time
        logger.info(
            f"Modell {model_name}: {len(result_dict)}/{len(TARGET_FIELDS)} "
            f"Felder extrahiert in {elapsed:.1f}s"
        )

        return result_dict

    finally:
        settings.OLLAMA_MODEL = original_model


def generate_html_comparison(
    comparisons: Dict[str, Dict[str, str]],
    output_path: Path,
    pdf_path: Path,
) -> None:
    """
    Generiert ein HTML-Dokument mit Side-by-Side-Vergleich.

    Args:
        comparisons: Dict mit model_name -> {field_name -> value}
        output_path: Pfad für die HTML-Datei
        pdf_path: Pfad zum Original-PDF
    """
    models = list(comparisons.keys())

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Modellvergleich: Textfeld-Extraktion S0051</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 28px;
        }}

        .metadata {{
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 14px;
        }}

        .field-comparison {{
            margin-bottom: 40px;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            overflow: hidden;
        }}

        .field-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            font-size: 18px;
            font-weight: 600;
        }}

        .model-results {{
            display: grid;
            grid-template-columns: repeat({len(models)}, 1fr);
            gap: 0;
        }}

        .model-column {{
            border-right: 1px solid #e0e0e0;
            padding: 20px;
            background: #fafafa;
        }}

        .model-column:last-child {{
            border-right: none;
        }}

        .model-name {{
            font-weight: 600;
            color: #667eea;
            margin-bottom: 12px;
            font-size: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #667eea;
        }}

        .field-value {{
            background: white;
            padding: 15px;
            border-radius: 4px;
            border: 1px solid #e0e0e0;
            min-height: 100px;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 14px;
            color: #2c3e50;
            line-height: 1.8;
        }}

        .field-value.empty {{
            color: #95a5a6;
            font-style: italic;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .stats {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-top: 1px solid #e0e0e0;
            font-size: 13px;
            color: #6c757d;
            text-align: center;
        }}

        .char-count {{
            display: inline-block;
            margin: 0 15px;
        }}

        @media print {{
            body {{
                background: white;
                padding: 0;
            }}

            .container {{
                box-shadow: none;
                padding: 20px;
            }}

            .field-comparison {{
                page-break-inside: avoid;
                margin-bottom: 20px;
            }}
        }}

        @media (max-width: 1200px) {{
            .model-results {{
                grid-template-columns: 1fr;
            }}

            .model-column {{
                border-right: none;
                border-bottom: 1px solid #e0e0e0;
            }}

            .model-column:last-child {{
                border-bottom: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔬 Modellvergleich: Textfeld-Extraktion S0051</h1>
        <div class="metadata">
            <strong>Quelldokument:</strong> {pdf_path.name}<br>
            <strong>Verglichene Modelle:</strong> {", ".join(models)}<br>
            <strong>Anzahl Felder:</strong> {len(TARGET_FIELDS)}<br>
            <strong>Generiert:</strong> {time.strftime("%Y-%m-%d %H:%M:%S")}
        </div>
"""

    # Für jedes Feld eine Vergleichssektion erstellen
    for field_name in TARGET_FIELDS:
        field_label = FIELD_LABELS.get(field_name, field_name)

        html += f"""
        <div class="field-comparison">
            <div class="field-header">
                📋 {field_label}
            </div>
            <div class="model-results">
"""

        # Spalten für jedes Modell
        for model_name in models:
            value = comparisons[model_name].get(field_name, "")
            char_count = len(value) if value else 0

            if value:
                value_html = f'<div class="field-value">{_escape_html(value)}</div>'
            else:
                value_html = '<div class="field-value empty">Nicht extrahiert</div>'

            html += f"""
                <div class="model-column">
                    <div class="model-name">{model_name}</div>
                    {value_html}
                </div>
"""

        html += """
            </div>
            <div class="stats">
"""

        # Zeichenzahlen anzeigen
        for model_name in models:
            value = comparisons[model_name].get(field_name, "")
            char_count = len(value) if value else 0
            html += f'<span class="char-count"><strong>{model_name}:</strong> {char_count} Zeichen</span>'

        html += """
            </div>
        </div>
"""

    html += """
    </div>
</body>
</html>
"""

    # HTML speichern
    output_path.write_text(html, encoding='utf-8')
    logger.info(f"HTML-Vergleich gespeichert: {output_path}")


def _escape_html(text: str) -> str:
    """HTML-Escaping für sicheren Text."""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def generate_json_comparison(
    comparisons: Dict[str, Dict[str, str]],
    output_path: Path,
    pdf_path: Path,
    execution_times: Dict[str, float],
) -> None:
    """
    Generiert eine JSON-Datei mit den Vergleichsergebnissen.
    """
    result = {
        "metadata": {
            "source_pdf": str(pdf_path),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "models": list(comparisons.keys()),
            "fields": TARGET_FIELDS,
        },
        "execution_times": execution_times,
        "comparisons": {},
    }

    # Vergleiche strukturieren
    for field_name in TARGET_FIELDS:
        field_label = FIELD_LABELS.get(field_name, field_name)
        result["comparisons"][field_name] = {
            "label": field_label,
            "results": {}
        }

        for model_name in comparisons.keys():
            value = comparisons[model_name].get(field_name, "")
            result["comparisons"][field_name]["results"][model_name] = {
                "value": value,
                "char_count": len(value) if value else 0,
                "extracted": bool(value),
            }

    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    logger.info(f"JSON-Vergleich gespeichert: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Vergleicht die Extraktion großer Textfelder zwischen verschiedenen Modellen."
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("uploads/dein_arztbrief.pdf"),
        help="Pfad zum Arztbrief-PDF",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["qwen2.5:14b", "qwen3:14b", "llama3.1:8b"],
        help="Liste der zu vergleichenden Modelle",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        default=Path("output/textfield_comparison.html"),
        help="Pfad für die HTML-Ausgabe",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("output/textfield_comparison.json"),
        help="Pfad für die JSON-Ausgabe",
    )

    args = parser.parse_args()

    # PDF validieren
    if not args.pdf.exists():
        logger.error(f"PDF nicht gefunden: {args.pdf}")
        return

    # Output-Verzeichnis erstellen
    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)

    # PDF in Text konvertieren
    logger.info(f"Extrahiere Text aus PDF: {args.pdf}")
    extraction_info = extract_text_from_pdf(args.pdf)
    source_text = extraction_info.text

    logger.info(
        f"Text extrahiert: {extraction_info.char_count} Zeichen, "
        f"{extraction_info.page_count} Seiten, "
        f"Methode: {extraction_info.method}"
    )

    # Mit jedem Modell extrahieren
    comparisons = {}
    execution_times = {}

    for model_name in args.models:
        start_time = time.perf_counter()
        try:
            result = extract_with_model(model_name, source_text)
            comparisons[model_name] = result
            execution_times[model_name] = round(time.perf_counter() - start_time, 2)
        except Exception as e:
            logger.error(f"Fehler bei Modell {model_name}: {e}")
            comparisons[model_name] = {}
            execution_times[model_name] = -1

    # Vergleichsdokumente erstellen
    generate_html_comparison(comparisons, args.output_html, args.pdf)
    generate_json_comparison(comparisons, args.output_json, args.pdf, execution_times)

    # Zusammenfassung ausgeben
    print("\n" + "=" * 80)
    print("VERGLEICH ABGESCHLOSSEN")
    print("=" * 80)
    print(f"Quelldokument: {args.pdf}")
    print(f"Modelle: {', '.join(args.models)}")
    print(f"\nAusführungszeiten:")
    for model, exec_time in execution_times.items():
        print(f"  {model}: {exec_time}s")

    print(f"\nExtraktionsrate:")
    for model in args.models:
        extracted = sum(1 for field in TARGET_FIELDS if comparisons[model].get(field))
        print(f"  {model}: {extracted}/{len(TARGET_FIELDS)} Felder extrahiert")

    print(f"\nAusgabedateien:")
    print(f"  HTML: {args.output_html}")
    print(f"  JSON: {args.output_json}")
    print("=" * 80)


if __name__ == "__main__":
    main()
