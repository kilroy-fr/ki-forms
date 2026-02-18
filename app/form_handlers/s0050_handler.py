"""
S0050 Form Handler

Handler fuer das Formular S0050 - Honorarabrechnung fuer die Deutsche Rentenversicherung.
Enthaelt formular-spezifische Logik (minimal, da S0050 meist von S0051 generiert wird).
"""

from typing import Dict, List, Set, Optional

from app.models.form_schema import FormField
from .base_handler import BaseFormHandler


class S0050FormHandler(BaseFormHandler):
    """
    Handler fuer S0050 - Honorarabrechnung.

    S0050 wird in der Regel automatisch aus S0051 generiert,
    kann aber auch eigenstaendig ausgefuellt werden.
    """

    def get_section_titles(self) -> Dict[int, str]:
        """Liefert die Sektionsnamen fuer S0050."""
        return {
            0: "Kopfdaten / Antragsart",
            1: "Personalien",
            2: "Zahlungsempfänger / Bankdaten",
        }

    def get_long_text_fields(self) -> Set[str]:
        """S0050 hat keine langen Textfelder."""
        return set()

    def postprocess_fields(
        self,
        fields: List[FormField],
        extracted_results: dict,
        session_data: Optional[dict] = None
    ) -> List[FormField]:
        """
        S0050 benoetigt keine spezielle Postprocessing-Logik,
        da es meist programmatisch generiert wird.
        """
        return fields
