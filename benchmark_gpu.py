"""
GPU-Diagnose und Benchmark für Ollama-Integration.

Misst:
- GPU-Auslastung des geladenen Modells (VRAM vs. CPU)
- Token-Generierungsgeschwindigkeit bei verschiedenen num_ctx-Einstellungen
- Empfehlung für optimale num_ctx-Einstellung

Verwendung:
    python benchmark_gpu.py
"""
import json
import time

import requests

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL = "qwen2.5:14b"

TEST_PROMPT = """Extrahiere folgende Informationen aus diesem Arztbrief:

ARZTBRIEF:
Patient Mustermann, Max, geb. 15.03.1965.
Diagnose: Lumbalgie bei Bandscheibenvorfall L4/L5 (M51.1).
Behandlung: Physiotherapie 2x/Woche seit Januar 2025.
Medikation: Ibuprofen 600mg bei Bedarf.

Gib die Informationen als JSON zurück mit:
- Patientenname
- Geburtsdatum
- Diagnose
- ICD-10-Code
- Behandlung

Antwort NUR als JSON ohne weiteren Text."""

SYSTEM_PROMPT = "Du bist ein medizinischer Dokumentationsassistent. Antworte ausschließlich im JSON-Format."


def get_model_status() -> dict:
    """Modellstatus von Ollama abfragen."""
    resp = requests.get(f"{OLLAMA_BASE_URL}/api/ps", timeout=5)
    resp.raise_for_status()
    return resp.json()


def format_bytes(b: int) -> str:
    return f"{b / 1024**3:.2f} GB"


def print_gpu_status():
    """GPU-Auslastung ausgeben."""
    print("\n=== GPU-Status ===")
    try:
        data = get_model_status()
        models = data.get("models", [])
        if not models:
            print("Kein Modell geladen.")
            return

        for m in models:
            name = m.get("name", "unbekannt")
            size_total = m.get("size", 0)
            size_vram = m.get("size_vram", 0)
            size_cpu = size_total - size_vram
            pct_gpu = size_vram / size_total * 100 if size_total > 0 else 0

            print(f"Modell:      {name}")
            print(f"Gesamt:      {format_bytes(size_total)}")
            print(f"VRAM (GPU):  {format_bytes(size_vram)} ({pct_gpu:.0f}%)")
            print(f"RAM (CPU):   {format_bytes(size_cpu)} ({100 - pct_gpu:.0f}%)")
            print(f"Context:     {m.get('details', {}).get('parameter_size', 'unbekannt')}")

            if size_cpu > 500 * 1024**2:  # > 500 MB auf CPU
                print(f"\n[!] WARNUNG: {format_bytes(size_cpu)} laufen auf CPU!")
                print("   -> OLLAMA_NUM_CTX reduzieren (aktuell zu grosser KV-Cache)")
            else:
                print("\n[OK] Modell vollstaendig auf GPU")
    except Exception as e:
        print(f"Fehler: {e}")


def benchmark_inference(num_ctx: int, label: str) -> dict:
    """Einzelner Benchmark-Lauf mit gegebenem num_ctx."""
    print(f"\n--- Benchmark: {label} (num_ctx={num_ctx}) ---")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": TEST_PROMPT},
        ],
        "stream": True,
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
            "num_ctx": num_ctx,
            "num_gpu": -1,
        },
    }

    start = time.time()
    token_count = 0
    full_response = ""

    try:
        with requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            stream=True,
            timeout=120,
        ) as resp:
            resp.raise_for_status()
            eval_count = 0
            eval_duration_ns = 0

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if "message" in chunk:
                    content = chunk["message"].get("content", "")
                    full_response += content
                    if content:
                        token_count += 1

                if chunk.get("done"):
                    eval_count = chunk.get("eval_count", 0)
                    eval_duration_ns = chunk.get("eval_duration", 0)
                    break

        elapsed = time.time() - start

        # Ollama gibt eval_count (Tokens) und eval_duration (ns) zurück
        if eval_count > 0 and eval_duration_ns > 0:
            tokens_per_sec = eval_count / (eval_duration_ns / 1e9)
            print(f"  Zeit gesamt:    {elapsed:.1f}s")
            print(f"  Output-Tokens:  {eval_count}")
            print(f"  Token/s (GPU):  {tokens_per_sec:.1f}")
            print(f"  Antwort:        {full_response[:100]}...")
            return {
                "num_ctx": num_ctx,
                "label": label,
                "elapsed": elapsed,
                "tokens": eval_count,
                "tokens_per_sec": tokens_per_sec,
            }
        else:
            print(f"  Zeit gesamt: {elapsed:.1f}s")
            print(f"  Antwort: {full_response[:100]}...")
            return {"num_ctx": num_ctx, "label": label, "elapsed": elapsed}

    except Exception as e:
        print(f"  Fehler: {e}")
        return {"num_ctx": num_ctx, "label": label, "error": str(e)}


def run_benchmark():
    print("=" * 50)
    print("KI-Forms GPU Benchmark")
    print("=" * 50)

    # Aktuellen Status zeigen
    print_gpu_status()

    print("\n=== Benchmark-Läufe ===")
    print("(Ersten Lauf ignorieren – Modell wird ggf. neu geladen)")

    results = []

    # Test 1: Aktuell konfiguriert (32768 – war der alte Wert)
    results.append(benchmark_inference(32768, "ALT: num_ctx=32768"))

    # Kurze Pause
    time.sleep(2)

    # Status nach erstem Lauf
    print_gpu_status()

    # Test 2: Neuer optimierter Wert
    results.append(benchmark_inference(8192, "NEU: num_ctx=8192"))

    time.sleep(2)

    # Status nach zweitem Lauf
    print_gpu_status()

    # Test 3: Noch kleinerer Wert
    results.append(benchmark_inference(4096, "MINIMAL: num_ctx=4096"))

    print("\n=== Zusammenfassung ===")
    for r in results:
        if "error" in r:
            print(f"  {r['label']}: FEHLER – {r['error']}")
        elif "tokens_per_sec" in r:
            print(f"  {r['label']}: {r['tokens_per_sec']:.1f} Token/s ({r['elapsed']:.1f}s)")
        else:
            print(f"  {r['label']}: {r['elapsed']:.1f}s")

    print("\nEmpfehlung:")
    print("  Setze OLLAMA_NUM_CTX=8192 in der .env für optimale GPU-Nutzung")
    print("  (Medizinische Dokumente selten > 6000 Tokens)")


if __name__ == "__main__":
    run_benchmark()
