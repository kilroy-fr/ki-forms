from app.models.form_schema import FormField, FieldType, FormDefinition

S0051_FIELDS = [
    # ===================================================================
    # Sektion 0: Kopfdaten / Identifikation
    # ===================================================================
    FormField(
        field_name="VERS_VNR",
        field_type=FieldType.TEXT,
        label_de="Versicherungsnummer",
        section=0,
        description="Versicherungsnummer der Person, aus deren Versicherung die Leistung beantragt wird",
        extract_from_ai=False,
    ),
    FormField(
        field_name="KENNZEICHEN",
        field_type=FieldType.TEXT,
        label_de="Kennzeichen",
        section=0,
        description="Kennzeichen / Aktenzeichen (soweit bekannt)",
        extract_from_ai=False,
    ),
    FormField(
        field_name="DRV_Kopf_PAF_Reha_MSAT_MSNR",
        field_type=FieldType.TEXT,
        label_de="MSAT / MSNR (Kopfzeile)",
        section=0,
        description="Massnahme-Satz-Nummer / Massnahme-Nummer (Kopfzeile, alle Seiten)",
        extract_from_ai=False,
    ),
    FormField(
        field_name="MSAT_MSNR",
        field_type=FieldType.TEXT,
        label_de="MSAT / MSNR",
        section=0,
        description="Massnahme-Satz-Nummer / Massnahme-Nummer",
        extract_from_ai=False,
    ),
    FormField(
        field_name="VERS_NAME",
        field_type=FieldType.TEXT,
        label_de="Name, Vorname (Versicherte/r)",
        section=0,
        description="Name, Vorname der Person, aus deren Versicherung die Leistung beantragt wird",
    ),
    FormField(
        field_name="VERS_GEBDAT",
        field_type=FieldType.TEXT,
        label_de="Geburtsdatum (Versicherte/r)",
        section=0,
        description="Geburtsdatum der versicherten Person (Format: TT.MM.JJJJ)",
    ),
    FormField(
        field_name="VERS_STRASSE_HNR",
        field_type=FieldType.TEXT,
        label_de="Strasse, Hausnummer (Versicherte/r)",
        section=0,
        description="Strasse und Hausnummer der versicherten Person",
    ),
    FormField(
        field_name="VERS_WOHNORT",
        field_type=FieldType.TEXT,
        label_de="PLZ, Wohnort (Versicherte/r)",
        section=0,
        description="Postleitzahl und Wohnort der versicherten Person",
    ),
    FormField(
        field_name="PAT_NAME",
        field_type=FieldType.TEXT,
        label_de="Patient/in (Name, Vorname)",
        section=0,
        description="Name, Vorname der Patientin / des Patienten",
    ),
    FormField(
        field_name="PAT_Geburtsdatum",
        field_type=FieldType.TEXT,
        label_de="Geburtsdatum (Patient/in)",
        section=0,
        description="Geburtsdatum der Patientin / des Patienten (Format: TT.MM.JJJJ)",
    ),
    FormField(
        field_name="PAT_STRASSE_HNR",
        field_type=FieldType.TEXT,
        label_de="Strasse, Hausnummer (Patient/in)",
        section=0,
        description="Strasse und Hausnummer der Patientin / des Patienten",
    ),
    FormField(
        field_name="PAT_PLZ_WOHNORT",
        field_type=FieldType.TEXT,
        label_de="PLZ, Wohnort (Patient/in)",
        section=0,
        description="Postleitzahl und Wohnort der Patientin / des Patienten",
    ),

    # Antragsart: PDF-Feld AW_1 (Radio-Gruppe mit 5 States)
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
    FormField(
        field_name="AW_1_sonstige",
        field_type=FieldType.RADIO,
        label_de="Sonstige Leistungen",
        section=0,
        description="Antrag auf sonstige Leistungen",
        radio_group="AW_1",
        pdf_state="Sonstiges",
        extract_from_ai=False,
    ),
    FormField(
        field_name="SONSTIGES",
        field_type=FieldType.TEXT,
        label_de="Sonstige Leistungen (Details)",
        section=0,
        description="Naehere Angabe bei Auswahl 'Sonstige Leistungen'",
        extract_from_ai=False,
    ),

    # ===================================================================
    # Sektion 1: Behandlung
    # ===================================================================
    FormField(
        field_name="NAME_DER_ÄRZTIN",
        field_type=FieldType.TEXT,
        label_de="Name der Aerztin/des Arztes",
        section=1,
        description="Name der behandelnden Aerztin / des Arztes / Psychotherapeutin / Psychotherapeut",
        extract_from_ai=False,
    ),
    FormField(
        field_name="FACHRICHTUNG",
        field_type=FieldType.TEXT,
        label_de="Fachrichtung",
        section=1,
        description="Medizinische Fachrichtung der behandelnden Aerztin / des Arztes",
        extract_from_ai=False,
    ),
    FormField(
        field_name="BEHANDLUNG_SEIT",
        field_type=FieldType.TEXT,
        label_de="In Behandlung seit",
        section=1,
        description="Datum, seit dem sich der Patient in Behandlung befindet (Format: TT.MM.JJJJ)",
    ),
    FormField(
        field_name="KONTAKT_LETZTER",
        field_type=FieldType.TEXT,
        label_de="Letzter Kontakt am",
        section=1,
        description="Datum des letzten Kontakts mit dem Patienten (Format: TT.MM.JJJJ)",
        extract_from_ai=False,
    ),
    FormField(
        field_name="TEL",
        field_type=FieldType.TEXT,
        label_de="Telefonnummer",
        section=1,
        description="Telefonnummer der Aerztin / des Arztes fuer Rueckfragen",
        extract_from_ai=False,
    ),

    # Kontakthaeufigkeit: PDF-Feld AW_2 (Radio-Gruppe mit 4 States)
    FormField(
        field_name="AW_2_woechentlich",
        field_type=FieldType.RADIO,
        label_de="woechentlich",
        section=1,
        description="Kontakthaeufigkeit: woechentlich",
        radio_group="AW_2",
        pdf_state="w\u00f6chentlich",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_2_14taegig",
        field_type=FieldType.RADIO,
        label_de="14-taegig",
        section=1,
        description="Kontakthaeufigkeit: 14-taegig / alle zwei Wochen",
        radio_group="AW_2",
        pdf_state="14-t\u00e4gig",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_2_monatlich",
        field_type=FieldType.RADIO,
        label_de="monatlich",
        section=1,
        description="Kontakthaeufigkeit: monatlich",
        radio_group="AW_2",
        pdf_state="monatlich",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_2_seltener",
        field_type=FieldType.RADIO,
        label_de="seltener",
        section=1,
        description="Kontakthaeufigkeit: seltener als monatlich",
        radio_group="AW_2",
        pdf_state="seltener",
        extract_from_ai=False,
    ),

    # Anregung: PDF-Feld AW_3 (Radio-Gruppe mit 2 States)
    FormField(
        field_name="AW_3_nein",
        field_type=FieldType.RADIO,
        label_de="Antrag nicht auf meine Anregung",
        section=1,
        description="Der Antrag wurde nicht auf Anregung des Arztes gestellt",
        radio_group="AW_3",
        pdf_state="nein",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_3_ja",
        field_type=FieldType.RADIO,
        label_de="Antrag auf meine Anregung",
        section=1,
        description="Der Antrag wurde auf Anregung des Arztes gestellt",
        radio_group="AW_3",
        pdf_state="ja",
        extract_from_ai=False,
    ),

    # ===================================================================
    # Sektion 2: Diagnosen
    # ===================================================================
    FormField(
        field_name="DIAG_1",
        field_type=FieldType.TEXT,
        label_de="Diagnose 1",
        section=2,
        description="Erste Diagnose (Diagnosetext)",
    ),
    FormField(
        field_name="ICD_1",
        field_type=FieldType.TEXT,
        label_de="ICD-10 Code 1",
        section=2,
        description="ICD-10 Diagnoseschluessel zur ersten Diagnose (z.B. M54.5)",
    ),
    FormField(
        field_name="DIAG_2",
        field_type=FieldType.TEXT,
        label_de="Diagnose 2",
        section=2,
        description="Zweite Diagnose (Diagnosetext)",
    ),
    FormField(
        field_name="ICD_2",
        field_type=FieldType.TEXT,
        label_de="ICD-10 Code 2",
        section=2,
        description="ICD-10 Diagnoseschluessel zur zweiten Diagnose",
    ),
    FormField(
        field_name="DIAG_3",
        field_type=FieldType.TEXT,
        label_de="Diagnose 3",
        section=2,
        description="Dritte Diagnose (Diagnosetext)",
    ),
    FormField(
        field_name="ICD_3",
        field_type=FieldType.TEXT,
        label_de="ICD-10 Code 3",
        section=2,
        description="ICD-10 Diagnoseschluessel zur dritten Diagnose",
    ),
    FormField(
        field_name="DIAG_4",
        field_type=FieldType.TEXT,
        label_de="Diagnose 4",
        section=2,
        description="Vierte Diagnose (Diagnosetext)",
    ),
    FormField(
        field_name="ICD_4",
        field_type=FieldType.TEXT,
        label_de="ICD-10 Code 4",
        section=2,
        description="ICD-10 Diagnoseschluessel zur vierten Diagnose",
    ),

    # ===================================================================
    # Sektion 3: Anamnese
    # ===================================================================
    FormField(
        field_name="ANAMNESE",
        field_type=FieldType.TEXT,
        label_de="Antragsrelevante Anamnese",
        section=3,
        description="Antragsrelevante Anamnese einschliesslich Krankenhausaufenthalte und Berichte anderer Fachaerzte",
    ),

    # ===================================================================
    # Sektion 4: Funktionseinschraenkungen
    # ===================================================================
    FormField(
        field_name="FUNKTIONSEINSCHRAENKUNGEN",
        field_type=FieldType.TEXT,
        label_de="Funktionseinschraenkungen",
        section=4,
        description="Daraus resultierende Funktionseinschraenkungen in Beruf und Alltag",
    ),

    # ===================================================================
    # Sektion 5: Aktivitaeten und Teilhabe (Radio-Button-Matrix)
    # Jedes PDF-Feld (AW_4 bis AW_12) hat 5 States:
    #   Keine Beeintraechtigungen, Einschraenkungen,
    #   Personelle Hilfe noetig, nicht durchfuehrbar, Keine Angabe moeglich
    # ===================================================================

    # 1. Lernen und Wissensanwendung (PDF: AW_4)
    FormField(field_name="AW_4_keine", field_type=FieldType.RADIO, label_de="keine Beeintraechtigungen", section=5, description="Lernen und Wissensanwendung: keine Beeintraechtigungen", radio_group="AW_4", pdf_state="Keine Beeintr\u00e4chtigungen", extract_from_ai=False),
    FormField(field_name="AW_4_einschr", field_type=FieldType.RADIO, label_de="Einschraenkungen", section=5, description="Lernen und Wissensanwendung: Einschraenkungen", radio_group="AW_4", pdf_state="Einschr\u00e4nkungen", extract_from_ai=False),
    FormField(field_name="AW_4_hilfe", field_type=FieldType.RADIO, label_de="Personelle Hilfe noetig", section=5, description="Lernen und Wissensanwendung: Personelle Hilfe noetig", radio_group="AW_4", pdf_state="Personelle Hilfe n\u00f6tig", extract_from_ai=False),
    FormField(field_name="AW_4_nicht", field_type=FieldType.RADIO, label_de="nicht durchfuehrbar", section=5, description="Lernen und Wissensanwendung: nicht durchfuehrbar", radio_group="AW_4", pdf_state="nicht durchf\u00fchrbar", extract_from_ai=False),
    FormField(field_name="AW_4_ka", field_type=FieldType.RADIO, label_de="Keine Angabe moeglich", section=5, description="Lernen und Wissensanwendung: Keine Angabe moeglich", radio_group="AW_4", pdf_state="Keine Angabe m\u00f6glich", extract_from_ai=False),

    # 2. Allgemeine Aufgaben und Anforderungen (PDF: AW_5)
    FormField(field_name="AW_5_keine", field_type=FieldType.RADIO, label_de="keine Beeintraechtigungen", section=5, description="Allgemeine Aufgaben und Anforderungen: keine Beeintraechtigungen", radio_group="AW_5", pdf_state="keine Beeintr\u00e4chtigungen", extract_from_ai=False),
    FormField(field_name="AW_5_einschr", field_type=FieldType.RADIO, label_de="Einschraenkungen", section=5, description="Allgemeine Aufgaben und Anforderungen: Einschraenkungen", radio_group="AW_5", pdf_state="Einschr\u00e4nkungen", extract_from_ai=False),
    FormField(field_name="AW_5_hilfe", field_type=FieldType.RADIO, label_de="Personelle Hilfe noetig", section=5, description="Allgemeine Aufgaben und Anforderungen: Personelle Hilfe noetig", radio_group="AW_5", pdf_state="Personelle Hilfe n\u00f6tig", extract_from_ai=False),
    FormField(field_name="AW_5_nicht", field_type=FieldType.RADIO, label_de="nicht durchfuehrbar", section=5, description="Allgemeine Aufgaben und Anforderungen: nicht durchfuehrbar", radio_group="AW_5", pdf_state="nicht durchf\u00fchrbar", extract_from_ai=False),
    FormField(field_name="AW_5_ka", field_type=FieldType.RADIO, label_de="Keine Angabe moeglich", section=5, description="Allgemeine Aufgaben und Anforderungen: Keine Angabe moeglich", radio_group="AW_5", pdf_state="Keine Angabe m\u00f6glich", extract_from_ai=False),

    # 3. Kommunikation (PDF: AW_6)
    FormField(field_name="AW_6_keine", field_type=FieldType.RADIO, label_de="keine Beeintraechtigungen", section=5, description="Kommunikation: keine Beeintraechtigungen", radio_group="AW_6", pdf_state="Keine Beeintr\u00e4chtigungen", extract_from_ai=False),
    FormField(field_name="AW_6_einschr", field_type=FieldType.RADIO, label_de="Einschraenkungen", section=5, description="Kommunikation: Einschraenkungen", radio_group="AW_6", pdf_state="Einschr\u00e4nkungen", extract_from_ai=False),
    FormField(field_name="AW_6_hilfe", field_type=FieldType.RADIO, label_de="Personelle Hilfe noetig", section=5, description="Kommunikation: Personelle Hilfe noetig", radio_group="AW_6", pdf_state="Personelle Hilfe n\u00f6tig", extract_from_ai=False),
    FormField(field_name="AW_6_nicht", field_type=FieldType.RADIO, label_de="nicht durchfuehrbar", section=5, description="Kommunikation: nicht durchfuehrbar", radio_group="AW_6", pdf_state="nicht durchf\u00fchrbar", extract_from_ai=False),
    FormField(field_name="AW_6_ka", field_type=FieldType.RADIO, label_de="Keine Angabe moeglich", section=5, description="Kommunikation: Keine Angabe moeglich", radio_group="AW_6", pdf_state="Keine Angabe m\u00f6glich", extract_from_ai=False),

    # 4. Mobilitaet (PDF: AW_7)
    FormField(field_name="AW_7_keine", field_type=FieldType.RADIO, label_de="keine Beeintraechtigungen", section=5, description="Mobilitaet: keine Beeintraechtigungen", radio_group="AW_7", pdf_state="Keine Beeintr\u00e4chtigungen", extract_from_ai=False),
    FormField(field_name="AW_7_einschr", field_type=FieldType.RADIO, label_de="Einschraenkungen", section=5, description="Mobilitaet: Einschraenkungen", radio_group="AW_7", pdf_state="Einschr\u00e4nkungen", extract_from_ai=False),
    FormField(field_name="AW_7_hilfe", field_type=FieldType.RADIO, label_de="Personelle Hilfe noetig", section=5, description="Mobilitaet: Personelle Hilfe noetig", radio_group="AW_7", pdf_state="Personelle Hilfe n\u00f6tig", extract_from_ai=False),
    FormField(field_name="AW_7_nicht", field_type=FieldType.RADIO, label_de="nicht durchfuehrbar", section=5, description="Mobilitaet: nicht durchfuehrbar", radio_group="AW_7", pdf_state="nicht durchf\u00fchrbar", extract_from_ai=False),
    FormField(field_name="AW_7_ka", field_type=FieldType.RADIO, label_de="Keine Angabe moeglich", section=5, description="Mobilitaet: Keine Angabe moeglich", radio_group="AW_7", pdf_state="Keine Angabe m\u00f6glich", extract_from_ai=False),

    # 5. Arbeit und Beschaeftigung (PDF: AW_8)
    FormField(field_name="AW_8_keine", field_type=FieldType.RADIO, label_de="keine Beeintraechtigungen", section=5, description="Arbeit und Beschaeftigung: keine Beeintraechtigungen", radio_group="AW_8", pdf_state="Keine Beeintr\u00e4chtigungen", extract_from_ai=False),
    FormField(field_name="AW_8_einschr", field_type=FieldType.RADIO, label_de="Einschraenkungen", section=5, description="Arbeit und Beschaeftigung: Einschraenkungen", radio_group="AW_8", pdf_state="Einschr\u00e4nkungen", extract_from_ai=False),
    FormField(field_name="AW_8_hilfe", field_type=FieldType.RADIO, label_de="Personelle Hilfe noetig", section=5, description="Arbeit und Beschaeftigung: Personelle Hilfe noetig", radio_group="AW_8", pdf_state="Personelle Hilfe n\u00f6tig", extract_from_ai=False),
    FormField(field_name="AW_8_nicht", field_type=FieldType.RADIO, label_de="nicht durchfuehrbar", section=5, description="Arbeit und Beschaeftigung: nicht durchfuehrbar", radio_group="AW_8", pdf_state="nicht durchf\u00fchrbar", extract_from_ai=False),
    FormField(field_name="AW_8_ka", field_type=FieldType.RADIO, label_de="Keine Angabe moeglich", section=5, description="Arbeit und Beschaeftigung: Keine Angabe moeglich", radio_group="AW_8", pdf_state="Keine Angabe m\u00f6glich", extract_from_ai=False),

    # 6. Erziehung / Bildung (PDF: AW_9)
    FormField(field_name="AW_9_keine", field_type=FieldType.RADIO, label_de="keine Beeintraechtigungen", section=5, description="Erziehung / Bildung: keine Beeintraechtigungen", radio_group="AW_9", pdf_state="Keine Beeintr\u00e4chtigungen", extract_from_ai=False),
    FormField(field_name="AW_9_einschr", field_type=FieldType.RADIO, label_de="Einschraenkungen", section=5, description="Erziehung / Bildung: Einschraenkungen", radio_group="AW_9", pdf_state="Einschr\u00e4nkungen", extract_from_ai=False),
    FormField(field_name="AW_9_hilfe", field_type=FieldType.RADIO, label_de="Personelle Hilfe noetig", section=5, description="Erziehung / Bildung: Personelle Hilfe noetig", radio_group="AW_9", pdf_state="Personelle Hilfe n\u00f6tig", extract_from_ai=False),
    FormField(field_name="AW_9_nicht", field_type=FieldType.RADIO, label_de="nicht durchfuehrbar", section=5, description="Erziehung / Bildung: nicht durchfuehrbar", radio_group="AW_9", pdf_state="nicht durchf\u00fchrbar", extract_from_ai=False),
    FormField(field_name="AW_9_ka", field_type=FieldType.RADIO, label_de="Keine Angabe moeglich", section=5, description="Erziehung / Bildung: Keine Angabe moeglich", radio_group="AW_9", pdf_state="Keine Angabe m\u00f6glich", extract_from_ai=False),

    # 7. Interpersonelle Aktivitaeten (PDF: AW_10)
    FormField(field_name="AW_10_keine", field_type=FieldType.RADIO, label_de="keine Beeintraechtigungen", section=5, description="Interpersonelle Aktivitaeten: keine Beeintraechtigungen", radio_group="AW_10", pdf_state="Keine Beeintr\u00e4chtigungen", extract_from_ai=False),
    FormField(field_name="AW_10_einschr", field_type=FieldType.RADIO, label_de="Einschraenkungen", section=5, description="Interpersonelle Aktivitaeten: Einschraenkungen", radio_group="AW_10", pdf_state="Einschr\u00e4nkungen", extract_from_ai=False),
    FormField(field_name="AW_10_hilfe", field_type=FieldType.RADIO, label_de="Personelle Hilfe noetig", section=5, description="Interpersonelle Aktivitaeten: Personelle Hilfe noetig", radio_group="AW_10", pdf_state="Personelle Hilfe n\u00f6tig", extract_from_ai=False),
    FormField(field_name="AW_10_nicht", field_type=FieldType.RADIO, label_de="nicht durchfuehrbar", section=5, description="Interpersonelle Aktivitaeten: nicht durchfuehrbar", radio_group="AW_10", pdf_state="nicht durchf\u00fchrbar", extract_from_ai=False),
    FormField(field_name="AW_10_ka", field_type=FieldType.RADIO, label_de="Keine Angabe moeglich", section=5, description="Interpersonelle Aktivitaeten: Keine Angabe moeglich", radio_group="AW_10", pdf_state="Keine Angabe m\u00f6glich", extract_from_ai=False),

    # 8. Haeusliches Leben / Haushaltsfuehrung (PDF: AW_11)
    FormField(field_name="AW_11_keine", field_type=FieldType.RADIO, label_de="keine Beeintraechtigungen", section=5, description="Haeusliches Leben: keine Beeintraechtigungen", radio_group="AW_11", pdf_state="Keine Beeintr\u00e4chtigungen", extract_from_ai=False),
    FormField(field_name="AW_11_einschr", field_type=FieldType.RADIO, label_de="Einschraenkungen", section=5, description="Haeusliches Leben: Einschraenkungen", radio_group="AW_11", pdf_state="Einschr\u00e4nkungen", extract_from_ai=False),
    FormField(field_name="AW_11_hilfe", field_type=FieldType.RADIO, label_de="Personelle Hilfe noetig", section=5, description="Haeusliches Leben: Personelle Hilfe noetig", radio_group="AW_11", pdf_state="Personelle Hilfe n\u00f6tig", extract_from_ai=False),
    FormField(field_name="AW_11_nicht", field_type=FieldType.RADIO, label_de="nicht durchfuehrbar", section=5, description="Haeusliches Leben: nicht durchfuehrbar", radio_group="AW_11", pdf_state="nicht durchf\u00fchrbar", extract_from_ai=False),
    FormField(field_name="AW_11_ka", field_type=FieldType.RADIO, label_de="Keine Angabe moeglich", section=5, description="Haeusliches Leben: Keine Angabe moeglich", radio_group="AW_11", pdf_state="Keine Angabe m\u00f6glich", extract_from_ai=False),

    # 9. Selbstversorgung (PDF: AW_12)
    FormField(field_name="AW_12_keine", field_type=FieldType.RADIO, label_de="keine Beeintraechtigungen", section=5, description="Selbstversorgung: keine Beeintraechtigungen", radio_group="AW_12", pdf_state="Keine Beeintr\u00e4chtigungen", extract_from_ai=False),
    FormField(field_name="AW_12_einschr", field_type=FieldType.RADIO, label_de="Einschraenkungen", section=5, description="Selbstversorgung: Einschraenkungen", radio_group="AW_12", pdf_state="Einschr\u00e4nkungen", extract_from_ai=False),
    FormField(field_name="AW_12_hilfe", field_type=FieldType.RADIO, label_de="Personelle Hilfe noetig", section=5, description="Selbstversorgung: Personelle Hilfe noetig", radio_group="AW_12", pdf_state="Personelle Hilfe n\u00f6tig", extract_from_ai=False),
    FormField(field_name="AW_12_nicht", field_type=FieldType.RADIO, label_de="nicht durchfuehrbar", section=5, description="Selbstversorgung: nicht durchfuehrbar", radio_group="AW_12", pdf_state="nicht durchf\u00fchrbar", extract_from_ai=False),
    FormField(field_name="AW_12_ka", field_type=FieldType.RADIO, label_de="Keine Angabe moeglich", section=5, description="Selbstversorgung: Keine Angabe moeglich", radio_group="AW_12", pdf_state="Keine Angabe m\u00f6glich", extract_from_ai=False),

    # ===================================================================
    # Sektion 6: Therapie
    # ===================================================================
    FormField(
        field_name="THERAPIE",
        field_type=FieldType.TEXT,
        label_de="Bisherige und aktuelle Therapie",
        section=6,
        description="Bisherige und aktuelle Therapie (Medikamente, Physiotherapie, Psychotherapie etc.)",
    ),

    # ===================================================================
    # Sektion 7: Untersuchungsbefunde
    # ===================================================================
    FormField(
        field_name="UNTERSUCHUNGSBEFUNDE",
        field_type=FieldType.TEXT,
        label_de="Untersuchungsbefunde",
        section=7,
        description="Koerperliche und/oder psychische Untersuchungsbefunde",
    ),
    FormField(
        field_name="GROESSE_CM",
        field_type=FieldType.TEXT,
        label_de="Koerpergroesse (cm)",
        section=7,
        description="Koerpergroesse in Zentimetern",
    ),
    FormField(
        field_name="GEWICHT_KG",
        field_type=FieldType.TEXT,
        label_de="Gewicht (kg)",
        section=7,
        description="Koerpergewicht in Kilogramm",
    ),

    # ===================================================================
    # Sektion 8: Medizinisch-technische Befunde
    # ===================================================================
    FormField(
        field_name="TECHNISCHE_BEFEUNDE",
        field_type=FieldType.TEXT,
        label_de="Medizinisch-technische Befunde",
        section=8,
        description="Medizinisch-technische Befunde (Labor, Roentgen, EKG, etc.)",
    ),

    # ===================================================================
    # Sektion 9: Lebensumstaende
    # ===================================================================
    FormField(
        field_name="LEBENSUMSTAENDE",
        field_type=FieldType.TEXT,
        label_de="Lebensumstaende / Kontextfaktoren",
        section=9,
        description="Lebensumstaende und Kontextfaktoren (soziales Umfeld, Wohnsituation, berufliche Situation)",
    ),

    # ===================================================================
    # Sektion 10: Risikofaktoren (Checkboxen, PDF: AW_17 bis AW_23)
    # ===================================================================
    FormField(
        field_name="AW_17",
        field_type=FieldType.CHECKBOX,
        label_de="Bewegungsmangel",
        section=10,
        description="Risikofaktor: Bewegungsmangel",
    ),
    FormField(
        field_name="AW_18",
        field_type=FieldType.CHECKBOX,
        label_de="Uebergewicht",
        section=10,
        description="Risikofaktor: Uebergewicht",
    ),
    FormField(
        field_name="AW_19",
        field_type=FieldType.CHECKBOX,
        label_de="Drogen",
        section=10,
        description="Risikofaktor: Drogenkonsum",
    ),
    FormField(
        field_name="AW_20",
        field_type=FieldType.CHECKBOX,
        label_de="Medikamente",
        section=10,
        description="Risikofaktor: Medikamentenmissbrauch",
    ),
    FormField(
        field_name="AW_21",
        field_type=FieldType.CHECKBOX,
        label_de="Untergewicht",
        section=10,
        description="Risikofaktor: Untergewicht",
    ),
    FormField(
        field_name="AW_22",
        field_type=FieldType.CHECKBOX,
        label_de="Nikotin",
        section=10,
        description="Risikofaktor: Nikotinkonsum / Rauchen",
    ),
    FormField(
        field_name="AW_23",
        field_type=FieldType.CHECKBOX,
        label_de="Alkohol",
        section=10,
        description="Risikofaktor: erhoehter Alkoholkonsum",
    ),

    # ===================================================================
    # Sektion 11: Arbeitsunfaehigkeit / Prognose
    # ===================================================================

    # Frage 1: Arbeitsunfaehigkeit (PDF: AW_13)
    FormField(
        field_name="AW_13_nein",
        field_type=FieldType.RADIO,
        label_de="nein",
        section=11,
        description="Patient ist nicht arbeitsunfaehig geschrieben",
        radio_group="AW_13",
        pdf_state="nein",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_13_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Patient ist arbeitsunfaehig geschrieben",
        radio_group="AW_13",
        pdf_state="ja",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AU_SEIT",
        field_type=FieldType.TEXT,
        label_de="seit (Datum)",
        section=11,
        description="Arbeitsunfaehig seit (Format: TT.MM.JJJJ)",
        extract_from_ai=False,
        conditional_on="AW_13_ja",
        conditional_value="AW_13_ja",
    ),
    FormField(
        field_name="AU_WEGEN",
        field_type=FieldType.TEXT,
        label_de="wegen",
        section=11,
        description="Grund der Arbeitsunfaehigkeit",
        extract_from_ai=False,
        conditional_on="AW_13_ja",
        conditional_value="AW_13_ja",
    ),

    # Frage 2: Befundaenderung (PDF: AW_14)
    FormField(
        field_name="AW_14_nein",
        field_type=FieldType.RADIO,
        label_de="nein",
        section=11,
        description="Keine Befundaenderung in den letzten 12 Monaten",
        radio_group="AW_14",
        pdf_state="nein",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_14_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Befundaenderung in den letzten 12 Monaten",
        radio_group="AW_14",
        pdf_state="ja",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_15_besserung",
        field_type=FieldType.RADIO,
        label_de="Besserung seit",
        section=11,
        description="Befund hat sich gebessert",
        radio_group="AW_15",
        pdf_state="Besserung seit",
        extract_from_ai=False,
        conditional_on="AW_14_ja",
        conditional_value="AW_14_ja",
    ),
    FormField(
        field_name="VERS_BESSERUNG_DATUM",
        field_type=FieldType.TEXT,
        label_de="Datum Besserung",
        section=11,
        description="Datum, seit dem eine Besserung eingetreten ist (Format: TT.MM.JJJJ)",
        extract_from_ai=False,
        conditional_on="AW_15_besserung",
        conditional_value="AW_15_besserung",
    ),
    FormField(
        field_name="AW_15_verschlechterung",
        field_type=FieldType.RADIO,
        label_de="Verschlechterung seit",
        section=11,
        description="Befund hat sich verschlechtert",
        radio_group="AW_15",
        pdf_state="Verschlechterung seit",
        extract_from_ai=False,
        conditional_on="AW_14_ja",
        conditional_value="AW_14_ja",
    ),
    FormField(
        field_name="VERS_VERSCHLECHTERUNG_DATUM",
        field_type=FieldType.TEXT,
        label_de="Datum Verschlechterung",
        section=11,
        description="Datum, seit dem eine Verschlechterung eingetreten ist (Format: TT.MM.JJJJ)",
        extract_from_ai=False,
        conditional_on="AW_15_verschlechterung",
        conditional_value="AW_15_verschlechterung",
    ),

    # Frage 3: Deutsche Sprache (PDF: AW_16)
    FormField(
        field_name="AW_16_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Verstaendigung in deutscher Sprache moeglich",
        radio_group="AW_16",
        pdf_state="ja",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_16_nein",
        field_type=FieldType.RADIO,
        label_de="nein",
        section=11,
        description="Verstaendigung in deutscher Sprache nicht moeglich",
        radio_group="AW_16",
        pdf_state="nein",
        extract_from_ai=False,
    ),
    FormField(
        field_name="SPRACHE",
        field_type=FieldType.TEXT,
        label_de="Wenn nein, in welcher Sprache?",
        section=11,
        description="Sprache des Patienten fuer Verstaendigung",
        extract_from_ai=False,
        conditional_on="AW_16_nein",
        conditional_value="AW_16_nein",
    ),

    # Frage 4: Reisefaehigkeit (PDF: AW_24)
    FormField(
        field_name="AW_24_nein",
        field_type=FieldType.RADIO,
        label_de="nein",
        section=11,
        description="Reisefaehigkeit fuer oeffentliche Verkehrsmittel besteht nicht",
        radio_group="AW_24",
        pdf_state="nein",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_24_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Reisefaehigkeit fuer oeffentliche Verkehrsmittel besteht",
        radio_group="AW_24",
        pdf_state="ja",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_24_1",
        field_type=FieldType.CHECKBOX,
        label_de="mit Begleitung",
        section=11,
        description="Reisefaehigkeit nur mit Begleitung",
        extract_from_ai=False,
        conditional_on="AW_24_ja",
        conditional_value="AW_24_ja",
    ),

    # Frage 5: Besserung der Leistungsfaehigkeit (PDF: AW_25)
    FormField(
        field_name="AW_25_nein",
        field_type=FieldType.RADIO,
        label_de="nein",
        section=11,
        description="Besserung der Leistungsfaehigkeit ist nicht moeglich",
        radio_group="AW_25",
        pdf_state="nein",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_25_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Besserung der Leistungsfaehigkeit ist moeglich",
        radio_group="AW_25",
        pdf_state="ja",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_25_kb",
        field_type=FieldType.RADIO,
        label_de="kann ich nicht beurteilen",
        section=11,
        description="Besserung der Leistungsfaehigkeit kann nicht beurteilt werden",
        radio_group="AW_25",
        pdf_state="kann ich nicht beurteilen",
        extract_from_ai=False,
    ),

    # Frage 6: Belastbarkeit fuer Rehabilitation (PDF: AW_26)
    FormField(
        field_name="AW_26_nein",
        field_type=FieldType.RADIO,
        label_de="nein",
        section=11,
        description="Belastbarkeit fuer eine Rehabilitation besteht nicht",
        radio_group="AW_26",
        pdf_state="nein",
        extract_from_ai=False,
    ),
    FormField(
        field_name="AW_26_ja",
        field_type=FieldType.RADIO,
        label_de="ja",
        section=11,
        description="Belastbarkeit fuer eine Rehabilitation besteht",
        radio_group="AW_26",
        pdf_state="ja",
        extract_from_ai=False,
    ),

    # ===================================================================
    # Sektion 12: Bemerkungen
    # ===================================================================
    FormField(
        field_name="BEMERKUNGEN",
        field_type=FieldType.TEXT,
        label_de="Bemerkungen",
        section=12,
        description="Ergaenzende Bemerkungen und Anmerkungen",
    ),
    FormField(
        field_name="ARZT_UNTERS_DATUM",
        field_type=FieldType.TEXT,
        label_de="Unterschrift, Datum, Stempel",
        section=12,
        description="Unterschrift, Datum, Stempel, Berufsbezeichnung, ggf. Facharztbezeichnung",
        extract_from_ai=False,
    ),
]

S0051_DEFINITION = FormDefinition(
    form_id="S0051",
    form_title="Befundbericht fuer die Deutsche Rentenversicherung",
    fields=S0051_FIELDS,
)
