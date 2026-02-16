import argparse
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.form_definitions.s0051 import S0051_DEFINITION
from app.services.field_extractor import extract_fields


def _normalize(value: str) -> str:
    return " ".join((value or "").strip().casefold().split())


@dataclass
class FieldRule:
    expected: str
    match: str = "exact"  # exact | contains | regex
    optional: bool = False


def _load_gold(gold_path: Path) -> dict[str, FieldRule]:
    raw = json.loads(gold_path.read_text(encoding="utf-8"))
    fields = raw.get("fields", {})
    out: dict[str, FieldRule] = {}
    for field_name, cfg in fields.items():
        if isinstance(cfg, str):
            out[field_name] = FieldRule(expected=cfg)
            continue
        out[field_name] = FieldRule(
            expected=str(cfg.get("expected", "")),
            match=str(cfg.get("match", "exact")),
            optional=bool(cfg.get("optional", False)),
        )
    return out


def _is_match(actual: str, rule: FieldRule) -> bool:
    actual_n = _normalize(actual)
    expected_n = _normalize(rule.expected)
    if rule.match == "exact":
        return actual_n == expected_n
    if rule.match == "contains":
        return expected_n in actual_n
    if rule.match == "regex":
        import re

        return re.search(rule.expected, actual or "", re.IGNORECASE) is not None
    raise ValueError(f"Unbekannte Match-Art: {rule.match}")


def _results_to_map(results) -> dict[str, str]:
    # Falls ein Feld mehrfach kommt, gewinnt der letzte Eintrag.
    out: dict[str, str] = {}
    for r in results:
        out[r.field_name] = r.value
    return out


def _score(pred: dict[str, str], gold: dict[str, FieldRule]) -> dict:
    required = {k: v for k, v in gold.items() if not v.optional}
    optional = {k: v for k, v in gold.items() if v.optional}

    matches = 0
    misses = 0
    wrong = 0
    details = []

    for field_name, rule in required.items():
        actual = pred.get(field_name)
        if actual is None:
            misses += 1
            details.append({"field": field_name, "status": "missing"})
            continue
        if _is_match(actual, rule):
            matches += 1
            details.append({"field": field_name, "status": "ok", "value": actual})
        else:
            wrong += 1
            details.append(
                {
                    "field": field_name,
                    "status": "mismatch",
                    "expected": rule.expected,
                    "actual": actual,
                    "match_mode": rule.match,
                }
            )

    optional_hit = 0
    optional_total = len(optional)
    for field_name, rule in optional.items():
        actual = pred.get(field_name)
        if actual is not None and _is_match(actual, rule):
            optional_hit += 1

    hallucinated = sorted(k for k in pred.keys() if k not in gold.keys())
    total_required = len(required)
    score = matches / total_required if total_required else 0.0

    return {
        "required_total": total_required,
        "required_match": matches,
        "required_missing": misses,
        "required_mismatch": wrong,
        "required_score": score,
        "optional_total": optional_total,
        "optional_match": optional_hit,
        "hallucinated_fields": hallucinated,
        "details": details,
    }


def run_benchmark(
    source_text: str,
    gold: dict[str, FieldRule],
    models: list[str],
    runs: int,
) -> dict:
    fields = [f.model_copy() for f in S0051_DEFINITION.fields]
    original_model = settings.OLLAMA_MODEL
    summary = {"models": []}

    try:
        for model in models:
            model_runs = []
            for run_idx in range(runs):
                settings.OLLAMA_MODEL = model
                start = time.perf_counter()
                results = extract_fields(fields, source_text)
                elapsed = time.perf_counter() - start

                pred = _results_to_map(results)
                scored = _score(pred, gold)
                scored["elapsed_sec"] = round(elapsed, 3)
                scored["run"] = run_idx + 1
                model_runs.append(scored)

            required_scores = [r["required_score"] for r in model_runs]
            elapsed_all = [r["elapsed_sec"] for r in model_runs]
            summary["models"].append(
                {
                    "model": model,
                    "runs": model_runs,
                    "avg_required_score": round(statistics.mean(required_scores), 4),
                    "min_required_score": round(min(required_scores), 4),
                    "max_required_score": round(max(required_scores), 4),
                    "avg_elapsed_sec": round(statistics.mean(elapsed_all), 3),
                }
            )
    finally:
        settings.OLLAMA_MODEL = original_model

    summary["ranking"] = sorted(
        (
            {
                "model": m["model"],
                "avg_required_score": m["avg_required_score"],
                "avg_elapsed_sec": m["avg_elapsed_sec"],
            }
            for m in summary["models"]
        ),
        key=lambda x: (-x["avg_required_score"], x["avg_elapsed_sec"]),
    )
    return summary


def _print_console(summary: dict) -> None:
    print("=" * 80)
    print("MODELL-BENCHMARK S0051")
    print("=" * 80)
    for row in summary["ranking"]:
        print(
            f"{row['model']}: score={row['avg_required_score']:.4f}, "
            f"avg_time={row['avg_elapsed_sec']:.3f}s"
        )
    print("-" * 80)
    for m in summary["models"]:
        print(f"\n{m['model']}")
        for run in m["runs"]:
            print(
                f"  Run {run['run']}: score={run['required_score']:.4f}, "
                f"match={run['required_match']}/{run['required_total']}, "
                f"missing={run['required_missing']}, mismatch={run['required_mismatch']}, "
                f"time={run['elapsed_sec']:.3f}s, hallucinations={len(run['hallucinated_fields'])}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vergleicht mehrere Ollama-Modelle für S0051-Feldextraktion."
    )
    parser.add_argument(
        "--source",
        default="data/benchmark_s0051_source.txt",
        help="Pfad zur Quelldatei mit extrahierbarem Text.",
    )
    parser.add_argument(
        "--gold",
        default="data/benchmark_s0051_gold.json",
        help="Pfad zur Gold-JSON-Datei (erwartete Felder).",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["qwen2.5:14b", "qwen3:14b", "llama3.1:8b"],
        help="Liste der zu vergleichenden Modelle.",
    )
    parser.add_argument("--runs", type=int, default=3, help="Runs pro Modell.")
    parser.add_argument(
        "--out",
        default="output/model_benchmark_s0051.json",
        help="Output-JSON mit Detailergebnissen.",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    gold_path = Path(args.gold)
    out_path = Path(args.out)

    source_text = source_path.read_text(encoding="utf-8")
    gold = _load_gold(gold_path)

    summary = run_benchmark(
        source_text=source_text,
        gold=gold,
        models=args.models,
        runs=args.runs,
    )
    _print_console(summary)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nErgebnis gespeichert: {out_path}")


if __name__ == "__main__":
    main()
