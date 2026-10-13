from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import copy


class FieldType(str, Enum):
    TEXT = "text"
    CHECKBOX = "checkbox"
    RADIO = "radio"


class FieldStatus(str, Enum):
    FILLED = "filled"
    UNFILLED = "unfilled"
    MANUAL = "manual"


@dataclass
class FormField:
    field_name: str
    field_type: FieldType
    label_de: str
    section: int
    description: str
    value: Optional[str] = None
    status: FieldStatus = FieldStatus.UNFILLED
    ai_confidence: Optional[str] = None
    radio_group: Optional[str] = None  # Gruppe für Radio-Buttons (= PDF-Feldname der Gruppe)
    radio_group_title: Optional[str] = None  # Titel für die Radio-Button-Gruppe (nur beim ersten Element)
    pdf_state: Optional[str] = None  # Für Radio: PDF-Appearance-State bei Auswahl
    extract_from_ai: bool = True  # Ob das Feld von KI extrahiert werden soll
    conditional_on: Optional[str] = None  # Feldname, von dem dieses Feld abhängt
    conditional_value: Optional[str] = None  # Wert, der erfüllt sein muss, um dieses Feld anzuzeigen
    # Maximale Zeichenzahl, die im PDF-Feld sichtbar Platz hat (None = kein Limit).
    # Wird der Wert überschritten, schneidet _set_text_widget_appearance() in
    # pdf_filler.py die überstehenden Zeilen kommentarlos ab.
    max_chars: Optional[int] = None

    def model_copy(self) -> "FormField":
        return copy.deepcopy(self)


@dataclass
class FormDefinition:
    form_id: str
    form_title: str
    fields: list[FormField]


@dataclass
class ExtractionResult:
    field_name: str
    value: str
    confidence: str
    # Woertliches Quelltextzitat, mit dem das Modell den Wert belegt.
    # Nur bei den narrativen Feldern gefordert; wird in field_extractor
    # gegen den Quelltext geprueft und danach nicht weiter verwendet.
    beleg: Optional[str] = None
