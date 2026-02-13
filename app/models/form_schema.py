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
    radio_group: Optional[str] = None  # Gruppe für Radio-Buttons
    extract_from_ai: bool = True  # Ob das Feld von KI extrahiert werden soll
    conditional_on: Optional[str] = None  # Feldname, von dem dieses Feld abhängt
    conditional_value: Optional[str] = None  # Wert, der erfüllt sein muss, um dieses Feld anzuzeigen

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
