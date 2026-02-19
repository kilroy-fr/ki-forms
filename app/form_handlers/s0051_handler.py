"""
S0051 Form Handler

Handler fuer das Formular S0051 - Befundbericht fuer die Deutsche Rentenversicherung.
Enthaelt alle formular-spezifische Logik:
- Sektionsnamen
- Sender-Daten-Befuellung
- Feldkopien (PAT_* -> VERS_*)
- S0050-Generierung
"""

import json
import logging
import shutil
from typing import Dict, List, Set, Optional
from pathlib import Path
from datetime import datetime

from app.models.form_schema import FormField, FieldStatus, FieldType
from app.config import settings
from .base_handler import BaseFormHandler

logger = logging.getLogger(__name__)


class S0051FormHandler(BaseFormHandler):
    """
    Handler fuer S0051 - Befundbericht.
    """

    # Pfad zur Absender-Daten-Datei
    SENDER_DATA_FILE = settings.FORM_TEMPLATE_DIR / "sender_data.json"

    def get_section_titles(self) -> Dict[int, str]:
        """Liefert die Sektionsnamen fuer S0051."""
        return {
            0: "Kopfdaten / Identifikation",
            1: "Behandlung",
            2: "Diagnosen",
            3: "Anamnese",
            4: "Funktionseinschränkungen",
            5: "Aktivitäten und Teilhabe",
            6: "Therapie",
            7: "Untersuchungsbefunde",
            8: "Medizinisch-technische Befunde",
            9: "Lebensumstände",
            10: "Risikofaktoren",
            11: "Arbeitsunfähigkeit / Prognose",
            12: "Bemerkungen",
        }

    def get_long_text_fields(self) -> Set[str]:
        """Liefert die Felder, die als Textarea gerendert werden."""
        return {
            "ANAMNESE",
            "FUNKTIONSEINSCHRAENKUNGEN",
            "THERAPIE",
            "UNTERSUCHUNGSBEFUNDE",
            "MED_TECHN_BEFUNDE",
            "LEBENSUMSTAENDE",
            "BEMERKUNGEN",
        }

    def postprocess_fields(
        self,
        fields: List[FormField],
        extracted_results: dict,
        session_data: Optional[dict] = None
    ) -> List[FormField]:
        """
        Hook nach KI-Extraktion:
        1. Sender-Daten einfuegen
        2. PAT_* -> VERS_* Kopie
        """
        fields_by_name = {f.field_name: f for f in fields}

        # 1. Sender-Daten laden und Behandlungsfelder befuellen
        self._fill_sender_data(fields_by_name)

        # 2. Automatische Wertkopie: PAT_* -> VERS_*
        self._copy_patient_to_versicherte(fields_by_name)

        return fields

    def on_finalize(
        self,
        fields_by_name: Dict[str, FormField],
        session_id: str
    ) -> None:
        """
        Hook beim Finalisieren:
        Generiert S0050 automatisch aus S0051-Daten.
        """
        try:
            self._generate_s0050_from_s0051(session_id, fields_by_name)
            logger.info(f"S0050 automatisch generiert für Session {session_id}")
        except Exception as e:
            logger.error(f"Fehler beim automatischen Generieren von S0050: {e}")

    # ===================================================================
    # Private Hilfsmethoden
    # ===================================================================

    def _load_sender_data(self) -> list:
        """
        Laedt Absender-Daten aus sender_data.json.
        Unterstuetzt sowohl neues Format (Array) als auch altes Format (Objekt).

        Returns:
            Liste von Arzt-Objekten
        """
        if not self.SENDER_DATA_FILE.exists():
            return []

        try:
            with open(self.SENDER_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Neues Format: {"doctors": [...]}
            if isinstance(data, dict) and "doctors" in data:
                return data["doctors"]

            # Altes Format: direktes Objekt mit Feldern
            if isinstance(data, dict) and any(
                key in data for key in ["anrede", "titel", "vorname", "name", "praxis"]
            ):
                # Konvertiere zu neuem Format und speichere
                new_data = {"active_doctor_index": 0, "doctors": [data]}
                with open(self.SENDER_DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
                return [data]

            return []
        except Exception as e:
            logger.warning(f"Fehler beim Laden der Sender-Daten: {e}")
            return []

    def _get_active_doctor_index(self) -> int:
        """Liest den Index des aktiven Arztes aus sender_data.json."""
        if not self.SENDER_DATA_FILE.exists():
            return 0
        try:
            with open(self.SENDER_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                idx = data.get("active_doctor_index", 0)
                return int(idx) if isinstance(idx, (int, float)) else 0
        except Exception:
            pass
        return 0

    def _get_active_sender_data(self) -> dict:
        """Gibt den aktiven Arzt zurück."""
        doctors = self._load_sender_data()
        if not doctors:
            return {}
        active_index = self._get_active_doctor_index()
        if 0 <= active_index < len(doctors):
            return doctors[active_index]
        return doctors[0]

    def _fill_sender_data(self, fields_by_name: Dict[str, FormField]) -> None:
        """
        Befuellt Behandlungsfelder mit Sender-Daten.

        Args:
            fields_by_name: Dictionary mit field_name als Key
        """
        sender_data = self._get_active_sender_data()
        if not sender_data:
            return

        try:

            # Name der Ärztin/des Arztes zusammensetzen: Titel + Vorname + Name
            arzt_name_parts = []
            if sender_data.get("titel"):
                arzt_name_parts.append(sender_data["titel"])
            if sender_data.get("vorname"):
                arzt_name_parts.append(sender_data["vorname"])
            if sender_data.get("name"):
                arzt_name_parts.append(sender_data["name"])
            arzt_name = " ".join(arzt_name_parts)

            # Aktuelles Datum im Format TT.MM.JJJJ
            current_date = datetime.now().strftime("%d.%m.%Y")

            # Unterschrift-Feld: "Name, Datum"
            arzt_unters_value = ""
            if arzt_name:
                arzt_unters_value = f"{arzt_name}, {current_date}"

            # Felder befüllen
            if arzt_name:
                field = fields_by_name.get("NAME_DER_ÄRZTIN")
                if field:
                    field.value = arzt_name
                    field.status = FieldStatus.FILLED
                    field.ai_confidence = "high"

            if sender_data.get("fachrichtung"):
                field = fields_by_name.get("FACHRICHTUNG")
                if field:
                    field.value = sender_data["fachrichtung"]
                    field.status = FieldStatus.FILLED
                    field.ai_confidence = "high"

            if sender_data.get("telefon"):
                field = fields_by_name.get("TELEFONNUMMER_FÜR_RÜCKFRAGEN")
                if field:
                    field.value = sender_data["telefon"]
                    field.status = FieldStatus.FILLED
                    field.ai_confidence = "high"

            if arzt_unters_value:
                field = fields_by_name.get("ARZT_UNTERS_DATUM")
                if field:
                    field.value = arzt_unters_value
                    field.status = FieldStatus.FILLED
                    field.ai_confidence = "high"

        except Exception as e:
            logger.warning(f"Fehler beim Befüllen der Behandlungsfelder mit Sender-Daten: {e}")

    def _copy_patient_to_versicherte(self, fields_by_name: Dict[str, FormField]) -> None:
        """
        Kopiert PAT_* Felder zu VERS_* Feldern (falls VERS_* leer ist).

        Args:
            fields_by_name: Dictionary mit field_name als Key
        """
        # Name kopieren
        self._copy_field_value(fields_by_name, "PAT_NAME", "VERS_NAME")

        # Adresse kopieren
        self._copy_field_value(fields_by_name, "PAT_STRASSE_HNR", "VERS_STRASSE_HNR")
        self._copy_field_value(fields_by_name, "PAT_PLZ", "VERS_PLZ")
        self._copy_field_value(fields_by_name, "PAT_WOHNORT", "VERS_WOHNORT")

    def _generate_s0050_from_s0051(
        self,
        session_id: str,
        s0051_fields: Dict[str, FormField]
    ) -> None:
        """
        Generiert S0050 automatisch aus S0051-Daten und sender_data.json.

        Args:
            session_id: Session-ID
            s0051_fields: Dictionary mit S0051-Feldern (field_name als Key)
        """
        from app.services import pdf_filler
        from app.form_definitions.s0050 import S0050_DEFINITION

        # S0050 Felder erstellen
        s0050_fields = [f.model_copy() for f in S0050_DEFINITION.fields]
        s0050_fields_by_name = {f.field_name: f for f in s0050_fields}

        # Sender-Daten laden (aktiver Arzt)
        sender_data = self._get_active_sender_data()

        # Versicherungsnummer und Kennzeichen von S0051 übernehmen
        vsnr = s0051_fields.get("PAF_VSNR_trim")
        kennz = s0051_fields.get("PAF_AIGR")

        if vsnr and vsnr.value:
            s0050_fields_by_name["PAF_VSNR_trim"].value = vsnr.value
            s0050_fields_by_name["PAF_VSNR_trim"].status = FieldStatus.MANUAL

        if kennz and kennz.value:
            s0050_fields_by_name["PAF_AIGR"].value = kennz.value
            s0050_fields_by_name["PAF_AIGR"].status = FieldStatus.MANUAL

        # Antragsart von S0051 übernehmen (AW_1)
        for s0051_field_name in ["AW_1_med_reha", "AW_1_onko_reha", "AW_1_lta", "AW_1_emr"]:
            s0051_field = s0051_fields.get(s0051_field_name)
            if s0051_field and s0051_field.value == "ja":
                s0050_field = s0050_fields_by_name.get(s0051_field_name)
                if s0050_field:
                    s0050_field.value = "ja"
                    s0050_field.status = FieldStatus.MANUAL
                break

        # Vergütung für S0051 aktivieren
        s0050_fields_by_name["AW_Verguetung_BB"].value = "ja"
        s0050_fields_by_name["AW_Verguetung_BB"].status = FieldStatus.MANUAL

        # Patientendaten von S0051 übernehmen
        pat_name = s0051_fields.get("PAT_NAME")
        pat_gebdat = s0051_fields.get("PAT_Geburtsdatum")

        if pat_name and pat_name.value:
            s0050_fields_by_name["PAT_NAME"].value = pat_name.value
            s0050_fields_by_name["PAT_NAME"].status = FieldStatus.MANUAL

        if pat_gebdat and pat_gebdat.value:
            s0050_fields_by_name["PAT_Geburtsdatum"].value = pat_gebdat.value
            s0050_fields_by_name["PAT_Geburtsdatum"].status = FieldStatus.MANUAL

        # Versicherte/r Daten - immer übernehmen (auch wenn identisch mit Patient)
        vers_name = s0051_fields.get("VERS_NAME")
        vers_gebdat = s0051_fields.get("VERS_GEBDAT")

        # VERS_NAME: direkt aus S0051 VERS_NAME, Fallback auf PAT_NAME
        if vers_name and vers_name.value:
            s0050_fields_by_name["VERS_NAME"].value = vers_name.value
            s0050_fields_by_name["VERS_NAME"].status = FieldStatus.MANUAL
        elif pat_name and pat_name.value:
            s0050_fields_by_name["VERS_NAME"].value = pat_name.value
            s0050_fields_by_name["VERS_NAME"].status = FieldStatus.MANUAL

        # VERS_GEBDAT: aus S0051 VERS_GEBDAT, Fallback auf PAT_Geburtsdatum
        if vers_gebdat and vers_gebdat.value:
            s0050_fields_by_name["VERS_GEBDAT"].value = vers_gebdat.value
            s0050_fields_by_name["VERS_GEBDAT"].status = FieldStatus.MANUAL
        elif pat_gebdat and pat_gebdat.value:
            s0050_fields_by_name["VERS_GEBDAT"].value = pat_gebdat.value
            s0050_fields_by_name["VERS_GEBDAT"].status = FieldStatus.MANUAL

        # Absender-Daten befüllen
        if sender_data:
            # IBAN: erste 2 Zeichen (Länderkennung "DE") entfernen
            if sender_data.get("iban"):
                iban_raw = sender_data["iban"]
                iban_value = iban_raw[2:] if len(iban_raw) > 2 else iban_raw
                s0050_fields_by_name["KONTOINH_IBAN"].value = iban_value
                s0050_fields_by_name["KONTOINH_IBAN"].status = FieldStatus.MANUAL

            # Geldinstitut
            if sender_data.get("kreditinstitut"):
                s0050_fields_by_name["KONTOINH_BANK_1"].value = sender_data["kreditinstitut"]
                s0050_fields_by_name["KONTOINH_BANK_1"].status = FieldStatus.MANUAL

            # Kontoinhaber: Vorname + Name
            kontoinhaber_parts = []
            if sender_data.get("vorname"):
                kontoinhaber_parts.append(sender_data["vorname"])
            if sender_data.get("name"):
                kontoinhaber_parts.append(sender_data["name"])
            if kontoinhaber_parts:
                s0050_fields_by_name["KONTOINH_NAME_1"].value = " ".join(kontoinhaber_parts)
                s0050_fields_by_name["KONTOINH_NAME_1"].status = FieldStatus.MANUAL

            # Adresse: Strasse + PLZ + Ort
            adresse_parts = []
            if sender_data.get("strasse"):
                strasse = sender_data["strasse"]
                if sender_data.get("hausnummer"):
                    strasse += " " + sender_data["hausnummer"]
                adresse_parts.append(strasse)
            if sender_data.get("plz") and sender_data.get("ort"):
                adresse_parts.append(f"{sender_data['plz']} {sender_data['ort']}")
            if adresse_parts:
                s0050_fields_by_name["KONTOINH_ORT_1"].value = ", ".join(adresse_parts)
                s0050_fields_by_name["KONTOINH_ORT_1"].status = FieldStatus.MANUAL

        # Aktuelles Datum
        current_date = datetime.now().strftime("%d.%m.%Y")
        current_date_nodots = datetime.now().strftime("%d%m%Y")

        # Rechnungsdatum: ohne Punkte (Format TTMMJJJJ)
        s0050_fields_by_name["RECHNUNG_VOM"].value = current_date_nodots
        s0050_fields_by_name["RECHNUNG_VOM"].status = FieldStatus.MANUAL

        # Ort, Datum (für ARZT_ORT): [aktuelles Datum] + Ort
        ort_datum = current_date
        if sender_data.get("ort"):
            ort_datum = f"{sender_data['ort']}, {current_date}"
        s0050_fields_by_name["ARZT_ORT"].value = ort_datum
        s0050_fields_by_name["ARZT_ORT"].status = FieldStatus.MANUAL

        # Unterschrift (ARZT_UNTERS): Vorname + Name
        arzt_unters_parts = []
        if sender_data.get("vorname"):
            arzt_unters_parts.append(sender_data["vorname"])
        if sender_data.get("name"):
            arzt_unters_parts.append(sender_data["name"])
        if arzt_unters_parts:
            s0050_fields_by_name["ARZT_UNTERS"].value = " ".join(arzt_unters_parts)
            s0050_fields_by_name["ARZT_UNTERS"].status = FieldStatus.MANUAL

        # S0050 PDF generieren
        s0050_template_path = settings.FORM_TEMPLATE_DIR / "S0050.pdf"
        s0050_output_path = settings.OUTPUT_DIR / f"S0050_{session_id}.pdf"

        pdf_filler.fill_pdf(s0050_template_path, s0050_output_path, s0050_fields)

        # Stabile Output-Datei
        try:
            stable_output_path = settings.OUTPUT_DIR / "S0050_ausgefuellt.pdf"
            shutil.copy2(s0050_output_path, stable_output_path)
            logger.debug(f"S0050 stabile Output-Datei aktualisiert: {stable_output_path}")
        except Exception as e:
            logger.warning(f"Konnte S0050 stabile Output-Datei nicht aktualisieren: {e}")
