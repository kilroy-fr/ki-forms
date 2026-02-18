"""
Form Registry

Zentrale Registry fuer alle verfuegbaren Formulare.
Mappt Formular-IDs auf Definitionen, Handler und Metadaten.
"""

from typing import Dict, Type, Optional, List
from dataclasses import dataclass

from app.models.form_schema import FormDefinition
from app.form_handlers.base_handler import BaseFormHandler


@dataclass
class FormRegistryEntry:
    """
    Ein Eintrag in der Formular-Registry.

    Attributes:
        form_id: Eindeutige ID des Formulars (z.B. "S0051")
        definition: FormDefinition-Objekt mit Feldern
        handler_class: Klasse des Form-Handlers
        template_filename: Dateiname der PDF-Vorlage (z.B. "S0051.pdf")
        generates: Liste von Formular-IDs, die automatisch generiert werden
        description: Optionale Beschreibung des Formulars
        enabled: Ob das Formular aktiv/verfuegbar ist
    """
    form_id: str
    definition: FormDefinition
    handler_class: Type[BaseFormHandler]
    template_filename: str
    generates: List[str] = None
    description: str = ""
    enabled: bool = True

    def __post_init__(self):
        """Initialisiert Default-Werte."""
        if self.generates is None:
            self.generates = []


class FormRegistry:
    """
    Zentrale Registry fuer alle Formulare.

    Verwendung:
        registry = get_form_registry()
        entry = registry.get("S0051")
        handler = entry.create_handler()
    """

    def __init__(self):
        self._entries: Dict[str, FormRegistryEntry] = {}

    def register(self, entry: FormRegistryEntry) -> None:
        """
        Registriert ein Formular.

        Args:
            entry: FormRegistryEntry mit allen Metadaten
        """
        self._entries[entry.form_id] = entry

    def get(self, form_id: str) -> Optional[FormRegistryEntry]:
        """
        Holt einen Registry-Eintrag.

        Args:
            form_id: Die Formular-ID

        Returns:
            FormRegistryEntry oder None
        """
        return self._entries.get(form_id)

    def get_all(self, enabled_only: bool = True) -> Dict[str, FormRegistryEntry]:
        """
        Holt alle Registry-Eintraege.

        Args:
            enabled_only: Nur aktive Formulare zurueckgeben

        Returns:
            Dictionary mit form_id als Key
        """
        if enabled_only:
            return {
                k: v for k, v in self._entries.items()
                if v.enabled
            }
        return self._entries.copy()

    def get_all_definitions(self, enabled_only: bool = True) -> Dict[str, FormDefinition]:
        """
        Holt alle FormDefinitions (kompatibel mit alter API).

        Args:
            enabled_only: Nur aktive Formulare zurueckgeben

        Returns:
            Dictionary mit form_id als Key und FormDefinition als Value
        """
        entries = self.get_all(enabled_only=enabled_only)
        return {k: v.definition for k, v in entries.items()}

    def create_handler(self, form_id: str) -> Optional[BaseFormHandler]:
        """
        Erstellt einen Handler fuer ein Formular.

        Args:
            form_id: Die Formular-ID

        Returns:
            BaseFormHandler-Instanz oder None
        """
        entry = self.get(form_id)
        if not entry:
            return None
        return entry.handler_class(entry.definition)


# Singleton-Instanz
_registry_instance: Optional[FormRegistry] = None


def get_form_registry() -> FormRegistry:
    """
    Liefert die globale Form-Registry (Singleton).

    Returns:
        FormRegistry-Instanz
    """
    global _registry_instance

    if _registry_instance is None:
        _registry_instance = _initialize_registry()

    return _registry_instance


def _initialize_registry() -> FormRegistry:
    """
    Initialisiert die Form-Registry mit allen verfuegbaren Formularen.

    Returns:
        FormRegistry-Instanz
    """
    from app.form_definitions.s0050 import S0050_DEFINITION
    from app.form_definitions.s0051 import S0051_DEFINITION
    from app.form_handlers.s0050_handler import S0050FormHandler
    from app.form_handlers.s0051_handler import S0051FormHandler

    registry = FormRegistry()

    # S0050: Honorarabrechnung
    registry.register(FormRegistryEntry(
        form_id="S0050",
        definition=S0050_DEFINITION,
        handler_class=S0050FormHandler,
        template_filename="S0050.pdf",
        description="Honorarabrechnung für die Deutsche Rentenversicherung",
        enabled=True,
    ))

    # S0051: Befundbericht
    registry.register(FormRegistryEntry(
        form_id="S0051",
        definition=S0051_DEFINITION,
        handler_class=S0051FormHandler,
        template_filename="S0051.pdf",
        generates=["S0050"],  # S0051 generiert automatisch S0050
        description="Befundbericht für die Deutsche Rentenversicherung",
        enabled=True,
    ))

    return registry


# Backwards-Compatibility-Funktion fuer alte API
def get_form_definitions() -> Dict[str, FormDefinition]:
    """
    Legacy-Funktion: Liefert alle FormDefinitions.

    DEPRECATED: Nutze get_form_registry() stattdessen.

    Returns:
        Dictionary mit form_id als Key und FormDefinition als Value
    """
    return get_form_registry().get_all_definitions()
