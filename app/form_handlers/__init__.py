"""
Form Handler Package

Dieses Paket enthaelt formular-spezifische Handler-Klassen,
die das Verhalten und die Logik fuer individuelle Formulare kapseln.
"""

from .base_handler import BaseFormHandler
from .s0050_handler import S0050FormHandler
from .s0051_handler import S0051FormHandler

__all__ = [
    "BaseFormHandler",
    "S0050FormHandler",
    "S0051FormHandler",
]
