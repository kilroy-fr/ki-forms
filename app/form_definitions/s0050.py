from app.models.form_schema import FormField, FieldType, FormDefinition

S0050_FIELDS = [
    # ===================================================================
    # Seite 1: Kopfdaten
    # ===================================================================
    FormField(
        field_name="PAF_VSNR_trim",
        field_type=FieldType.TEXT,
        label_de="Versicherungsnummer",
        section=0,
        description="Versicherungsnummer",
        extract_from_ai=False,
    ),
    FormField(
        field_name="PAF_AIGR",
        field_type=FieldType.TEXT,
        label_de="Kennzeichen",
        section=0,
        description="Kennzeichen / Aktenzeichen",
        extract_from_ai=False,
    ),

    # Antragsart Radio-Gruppe (PDF-Feld: AW_1)
    FormField(
        field_name="AW_1_med_reha",
        field_type=FieldType.RADIO,
        label_de="Leistungen zur medizinischen Rehabilitation",
        section=0,
        description="Antrag auf Leistungen zur medizinischen Rehabilitation",
        radio_group="AW_1",
        pdf_state="Leistungen zur medizinischen Rehabilitation",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_1_onko_reha",
        field_type=FieldType.RADIO,
        label_de="Leistungen zur onkologischen Rehabilitation",
        section=0,
        description="Antrag auf Leistungen zur onkologischen Rehabilitation",
        radio_group="AW_1",
        pdf_state="Leistungen zur onkologischen Rehabilitation",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_1_lta",
        field_type=FieldType.RADIO,
        label_de="Leistungen zur Teilhabe am Arbeitsleben (LTA)",
        section=0,
        description="Antrag auf Leistungen zur Teilhabe am Arbeitsleben",
        radio_group="AW_1",
        pdf_state="Leistungen zur Teilhabe am Arbeitsleben (LTA)",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_1_emr",
        field_type=FieldType.RADIO,
        label_de="Erwerbsminderungsrente",
        section=0,
        description="Antrag auf Erwerbsminderungsrente",
        radio_group="AW_1",
        pdf_state="Erwerbsminderungsrente",
        extract_from_ai=False,
    ),

    # Vergütungs-Checkboxen
    FormField(
        field_name="AW_Verguetung_BB",
        field_type=FieldType.CHECKBOX,
        label_de="Vergütung für Formular S0051 (41,04 EUR)",
        section=0,
        description="Vergütung für das Formular S0051 - Befundbericht",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_ZusBogen_onkol",
        field_type=FieldType.CHECKBOX,
        label_de="Vergütung für Formular S0052 (5 EUR)",
        section=0,
        description="Vergütung für das Formular S0052 - Zusatzbogen onkologische Rehabilitation",
        extract_from_ai=False,
    ),

    # Personalien Patientin/Patient
    FormField(
        field_name="PAT_NAME",
        field_type=FieldType.TEXT,
        label_de="Name, Vorname (Patientin/Patient)",
        section=1,
        description="Name und Vorname der Patientin / des Patienten",
        extract_from_ai=False,
    ),
    FormField(
        field_name="PAT_Geburtsdatum",
        field_type=FieldType.TEXT,
        label_de="Geburtsdatum (Patientin/Patient)",
        section=1,
        description="Geburtsdatum der Patientin / des Patienten",
        extract_from_ai=False,
    ),

    # Personalien Versicherte/r (falls abweichend)
    FormField(
        field_name="VERS_NAME",
        field_type=FieldType.TEXT,
        label_de="Name, Vorname (Versicherte/r)",
        section=1,
        description="Name und Vorname der/des Versicherten (falls abweichend von Patientin/Patient)",
        extract_from_ai=False,
    ),
    FormField(
        field_name="VERS_GEBDAT",
        field_type=FieldType.TEXT,
        label_de="Geburtsdatum (Versicherte/r)",
        section=1,
        description="Geburtsdatum der/des Versicherten (falls abweichend)",
        extract_from_ai=False,
    ),

    # ===================================================================
    # Seite 2: Zahlungsempfänger und Bankdaten
    # ===================================================================
    FormField(
        field_name="INSTITUTIONSKENNZEICHEN",
        field_type=FieldType.TEXT,
        label_de="Institutionskennzeichen",
        section=2,
        description="Institutionskennzeichen",
        extract_from_ai=False,
    ),
    FormField(
        field_name="KONTOINH_IBAN",
        field_type=FieldType.TEXT,
        label_de="IBAN",
        section=2,
        description="IBAN (International Bank Account Number)",
        extract_from_ai=False,
    ),
    FormField(
        field_name="KONTOINH_BANK_1",
        field_type=FieldType.TEXT,
        label_de="Geldinstitut (Name, Ort)",
        section=2,
        description="Name und Ort des Geldinstituts",
        extract_from_ai=False,
    ),
    FormField(
        field_name="KONTOINH_NAME_1",
        field_type=FieldType.TEXT,
        label_de="Kontoinhaber/in",
        section=2,
        description="Name der Kontoinhaberin / des Kontoinhabers",
        extract_from_ai=False,
    ),
    FormField(
        field_name="KONTOINH_ORT_1",
        field_type=FieldType.TEXT,
        label_de="Straße, Hausnummer, PLZ, Ort",
        section=2,
        description="Vollständige Adresse (Straße, Hausnummer, PLZ, Ort)",
        extract_from_ai=False,
    ),
    FormField(
        field_name="RECHNUNG_NUM_1",
        field_type=FieldType.TEXT,
        label_de="Rechnungsnummer",
        section=2,
        description="Rechnungsnummer",
        extract_from_ai=False,
    ),
    FormField(
        field_name="RECHNUNG_VOM",
        field_type=FieldType.TEXT,
        label_de="Rechnung vom",
        section=2,
        description="Rechnungsdatum",
        extract_from_ai=False,
    ),
    FormField(
        field_name="ARZT_ORT",
        field_type=FieldType.TEXT,
        label_de="Ort, Datum",
        section=2,
        description="Ort und Datum der Unterschrift",
        extract_from_ai=False,
    ),
    FormField(
        field_name="ARZT_UNTERS",
        field_type=FieldType.TEXT,
        label_de="Unterschrift des Arztes",
        section=2,
        description="Unterschrift, Name des Arztes",
        extract_from_ai=False,
    ),
]

S0050_DEFINITION = FormDefinition(
    form_id="S0050",
    form_title="Honorarabrechnung für die Deutsche Rentenversicherung",
    fields=S0050_FIELDS,
)
