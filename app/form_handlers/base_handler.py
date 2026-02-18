"""
Base Form Handler

Abstrakte Basisklasse fuer alle Formular-Handler.
Definiert die Standard-Schnittstelle und Hooks fuer formular-spezifische Logik.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Set, Optional
from pathlib import Path

from app.models.form_schema import FormDefinition, FormField


class BaseFormHandler(ABC):
    """
    Abstrakte Basisklasse fuer Formular-Handler.

    Jedes Formular kann einen eigenen Handler implementieren, um
    formular-spezifisches Verhalten zu definieren:
    - Sektionsnamen
    - Lange Textfelder (Textareas)
    - Preprocessing (vor KI-Extraktion)
    - Postprocessing (nach KI-Extraktion)
    - Finalisierung (beim PDF-Generieren)
    """

    def __init__(self, form_definition: FormDefinition):
        """
        Initialisiert den Handler mit einer Formular-Definition.

        Args:
            form_definition: Die FormDefinition fuer dieses Formular
        """
        self.definition = form_definition
        self.form_id = form_definition.form_id

    # ===================================================================
    # Metadaten und Konfiguration
    # ===================================================================

    def get_section_titles(self) -> Dict[int, str]:
        """
        Liefert die Titel fuer alle Sektionen des Formulars.

        Returns:
            Dictionary mit Sektion-Nummer als Key und Titel als Value
        """
        # Default: Generische Titel
        return {i: f"Abschnitt {i}" for i in range(20)}

    def get_long_text_fields(self) -> Set[str]:
        """
        Liefert die Menge der Felder, die als Textarea gerendert werden sollen.

        Returns:
            Set von Feldnamen (field_name), die als mehrzeilige Textfelder
            dargestellt werden sollen
        """
        return set()

    def get_template_filename(self) -> str:
        """
        Liefert den Dateinamen der PDF-Vorlage.

        Returns:
            Dateiname (z.B. "S0051.pdf")
        """
        return f"{self.form_id}.pdf"

    # ===================================================================
    # Lifecycle Hooks
    # ===================================================================

    def preprocess_fields(
        self,
        fields: List[FormField],
        source_text: str,
        session_data: Optional[dict] = None
    ) -> List[FormField]:
        """
        Hook VOR der KI-Extraktion.

        Kann genutzt werden, um:
        - Felder hinzuzufuegen/entfernen
        - Default-Werte zu setzen
        - Source-Text zu analysieren

        Args:
            fields: Liste der FormField-Objekte
            source_text: Extrahierter Text aus hochgeladenen PDFs
            session_data: Optionale Session-Daten

        Returns:
            Modifizierte Liste von FormField-Objekten
        """
        return fields

    def postprocess_fields(
        self,
        fields: List[FormField],
        extracted_results: dict,
        session_data: Optional[dict] = None
    ) -> List[FormField]:
        """
        Hook NACH der KI-Extraktion.

        Kann genutzt werden, um:
        - Felder zu kopieren (z.B. PAT_* -> VERS_*)
        - Sender-Daten einzufuegen
        - Berechnete Felder zu fuellen

        Args:
            fields: Liste der FormField-Objekte (bereits mit KI-Daten gefuellt)
            extracted_results: Dictionary mit Extraktionsergebnissen
            session_data: Optionale Session-Daten

        Returns:
            Modifizierte Liste von FormField-Objekten
        """
        return fields

    def on_generate_pdf(
        self,
        fields: List[FormField],
        session_id: str,
        output_path: Path
    ) -> None:
        """
        Hook beim PDF-Generieren (nach dem Fuellen, vor dem Speichern).

        Kann genutzt werden, um:
        - Zusaetzliche PDFs zu generieren (z.B. S0050 aus S0051)
        - Logs zu schreiben
        - Benachrichtigungen zu senden

        Args:
            fields: Liste der finalen FormField-Objekte
            session_id: Session-ID
            output_path: Pfad zum generierten PDF
        """
        pass

    def on_finalize(
        self,
        fields_by_name: Dict[str, FormField],
        session_id: str
    ) -> None:
        """
        Hook nach dem Finalisieren des Formulars.

        Kann genutzt werden, um:
        - Abhaengige Formulare zu generieren (z.B. S0050 aus S0051)
        - Cleanup durchzufuehren

        Args:
            fields_by_name: Dictionary mit field_name als Key
            session_id: Session-ID
        """
        pass

    # ===================================================================
    # Hilfsmethoden
    # ===================================================================

    def _get_field_value(
        self,
        fields_by_name: Dict[str, FormField],
        field_name: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Hilfsmethode: Holt den Wert eines Feldes.

        Args:
            fields_by_name: Dictionary mit field_name als Key
            field_name: Name des Feldes
            default: Default-Wert falls Feld nicht existiert oder leer

        Returns:
            Feldwert oder default
        """
        field = fields_by_name.get(field_name)
        if field and field.value:
            return field.value
        return default

    def _copy_field_value(
        self,
        fields_by_name: Dict[str, FormField],
        source_name: str,
        target_name: str,
        overwrite: bool = False
    ) -> bool:
        """
        Hilfsmethode: Kopiert den Wert von einem Feld zu einem anderen.

        Args:
            fields_by_name: Dictionary mit field_name als Key
            source_name: Quell-Feldname
            target_name: Ziel-Feldname
            overwrite: Ob bestehendes Ziel ueberschrieben werden soll

        Returns:
            True wenn kopiert wurde, False sonst
        """
        from app.models.form_schema import FieldStatus

        source = fields_by_name.get(source_name)
        target = fields_by_name.get(target_name)

        if not source or not target:
            return False

        if not source.value:
            return False

        # Nur kopieren wenn Ziel leer ist (oder overwrite=True)
        if target.value and not overwrite:
            return False

        target.value = source.value
        target.status = FieldStatus.FILLED
        target.ai_confidence = source.ai_confidence

        return True
