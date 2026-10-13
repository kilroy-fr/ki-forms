"""
ICD-10-Katalog: Validierung und Nachschlagen von Diagnoseschluesseln.

Hintergrund: Das Modell rat ICD-Codes aus dem Gedaechtnis und liegt dabei
regelmaessig daneben - im Test an einem echten Arztbrief waren alle drei
gelieferten Codes falsch, einer davon (Q81.3) existiert im Katalog gar nicht.
Ein falscher Code mit "medium" confidence in einem DRV-Formular ist deutlich
schlechter als ein leeres Feld, das die Aerztin im Review ausfuellt.

Datenquelle: data/icd10_codes_2025.json (16.818 Eintraege, Code + Krankheit).
"""

import json
import logging
import math
import re
from functools import lru_cache
from typing import NamedTuple, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Mindest-Uebereinstimmung, ab der ein Katalogeintrag als Treffer fuer einen
# Diagnosetext gilt. Bewusst hoch: der Katalog soll nur bei nahezu woertlicher
# Uebereinstimmung antworten ("Ehlers-Danlos Syndrom" -> Q79.6), nicht raten.
_LOOKUP_THRESHOLD = 0.75
# Abstand zum zweitbesten Treffer, sonst gilt das Ergebnis als mehrdeutig
_AMBIGUITY_MARGIN = 0.15
# Uebereinstimmung, ab der ein vom Modell gelieferter Code als durch den
# Katalogtext gedeckt gilt
_AGREEMENT_THRESHOLD = 0.30

_UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


class IcdMatch(NamedTuple):
    code: str
    term: str
    score: float


def _tokenize(text: str) -> frozenset[str]:
    """Text in vergleichbare Tokens zerlegen (Umlaute normalisiert, Kurzwoerter raus)."""
    normalized = (text or "").lower().translate(_UMLAUT_MAP)
    return frozenset(t for t in re.findall(r"\w+", normalized) if len(t) > 2)


def normalize_code(raw: str) -> str:
    """
    Schreibweise eines ICD-Codes vereinheitlichen.

    Das Modell liefert mal "m54.5", mal "M54.5 " oder "M54.5.". Kreuz-Stern-
    Notation (M99.0*) wird ebenfalls entfernt, der Katalog fuehrt die Codes ohne.
    """
    return (raw or "").strip().upper().rstrip(".*+!").replace(" ", "")


class _Catalog:
    """Geladener Katalog mit IDF-Gewichten fuer den Textabgleich."""

    def __init__(self, entries: list[dict]):
        self.by_code: dict[str, str] = {}
        self.terms: list[tuple[str, str, frozenset[str]]] = []
        document_freq: dict[str, int] = {}

        for entry in entries:
            code = normalize_code(entry.get("Code", ""))
            term = (entry.get("Krankheit") or "").strip()
            if not code or code == "UNDEF" or not term:
                continue
            self.by_code[code] = term
            tokens = _tokenize(term)
            if tokens:
                self.terms.append((code, term, tokens))
                for token in tokens:
                    document_freq[token] = document_freq.get(token, 0) + 1

        # IDF: seltene Woerter wie "danlos" wiegen schwer, Allerweltswoerter wie
        # "syndrom" oder "sonstige" fast nichts. Ohne diese Gewichtung matcht
        # "Ehlers-Danlos Syndrom" genauso gut auf "CR(E)ST-Syndrom", weil beide
        # Eintraege nur das gemeinsame Token "syndrom" beitragen.
        total = len(self.terms) or 1
        self.idf: dict[str, float] = {
            token: math.log(total / freq) for token, freq in document_freq.items()
        }

    def weight(self, tokens: frozenset[str]) -> float:
        """Summiertes IDF-Gewicht einer Tokenmenge. Unbekannte Tokens wiegen maximal."""
        default = math.log(len(self.terms) or 1)
        return sum(self.idf.get(t, default) for t in tokens)

    def similarity(self, a: frozenset[str], b: frozenset[str]) -> float:
        """IDF-gewichtete Jaccard-Aehnlichkeit zweier Tokenmengen."""
        union = self.weight(a | b)
        if not union:
            return 0.0
        return self.weight(a & b) / union


@lru_cache(maxsize=1)
def _catalog() -> Optional[_Catalog]:
    """Katalog einmalig laden. Fehlt die Datei, wird die Validierung uebersprungen."""
    path = settings.FORM_TEMPLATE_DIR / "icd10_codes_2025.json"
    try:
        with open(path, encoding="utf-8") as fh:
            entries = json.load(fh)
    except FileNotFoundError:
        logger.warning(f"ICD-Katalog nicht gefunden ({path}) - Validierung deaktiviert")
        return None
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"ICD-Katalog nicht lesbar ({path}): {e} - Validierung deaktiviert")
        return None

    catalog = _Catalog(entries)
    logger.info(f"ICD-Katalog geladen: {len(catalog.by_code)} Codes aus {path.name}")
    return catalog


def is_available() -> bool:
    """Ob der Katalog nutzbar ist."""
    return _catalog() is not None


def official_term(code: str) -> Optional[str]:
    """Offizielle Katalogbezeichnung zu einem Code, oder None wenn unbekannt."""
    catalog = _catalog()
    if catalog is None:
        return None
    return catalog.by_code.get(normalize_code(code))


def is_valid_code(code: str) -> bool:
    """Ob der Code im Katalog existiert. Ohne Katalog gilt jeder Code als gueltig."""
    catalog = _catalog()
    if catalog is None:
        return True
    return normalize_code(code) in catalog.by_code


def lookup_code(diagnosis_text: str) -> Optional[IcdMatch]:
    """
    Passenden ICD-Code zu einem Diagnosetext im Katalog suchen.

    Antwortet nur bei nahezu woertlicher Uebereinstimmung und nur, wenn der beste
    Treffer deutlich vor dem zweitbesten liegt. Synonyme findet der Katalog nicht
    ("Lumbalgie" steht dort als "Kreuzschmerz") - dann ist None die richtige
    Antwort, nicht der naechstbeste Eintrag.
    """
    catalog = _catalog()
    if catalog is None:
        return None

    query = _tokenize(diagnosis_text)
    if not query:
        return None

    best: Optional[IcdMatch] = None
    runner_up = 0.0
    for code, term, tokens in catalog.terms:
        if not (query & tokens):
            continue
        score = catalog.similarity(query, tokens)
        if best is None or score > best.score:
            if best is not None:
                runner_up = best.score
            best = IcdMatch(code, term, score)
        elif score > runner_up:
            runner_up = score

    if best is None or best.score < _LOOKUP_THRESHOLD:
        return None
    if best.score - runner_up < _AMBIGUITY_MARGIN:
        logger.debug(
            f"ICD-Nachschlag '{diagnosis_text[:40]}': mehrdeutig "
            f"(bester {best.code} {best.score:.2f}, zweitbester {runner_up:.2f})"
        )
        return None
    return best


def agreement(diagnosis_text: str, code: str) -> float:
    """
    Wie gut die Katalogbezeichnung eines Codes zum Diagnosetext passt (0.0-1.0).

    Niedrige Werte sind KEIN Beweis fuer einen falschen Code: der korrekte
    T84.5 heisst "Infektion und entzuendliche Reaktion durch eine
    Gelenkendoprothese" und teilt mit "Fruehinfekt der Hueft-TEP" kaum ein Wort.
    Der Wert taugt deshalb nur als Warnsignal, nicht als Ausschlusskriterium.
    """
    catalog = _catalog()
    if catalog is None:
        return 0.0
    term = catalog.by_code.get(normalize_code(code))
    if not term:
        return 0.0
    return catalog.similarity(_tokenize(diagnosis_text), _tokenize(term))


def is_corroborated(diagnosis_text: str, code: str) -> bool:
    """Ob die Katalogbezeichnung den Diagnosetext stuetzt."""
    return agreement(diagnosis_text, code) >= _AGREEMENT_THRESHOLD
