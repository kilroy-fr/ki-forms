from app.models.form_schema import FormField, FieldType, FormDefinition

S0051_FIELDS = [
    # ===================================================================
    # Sektion 0: Kopfdaten / Identifikation
    # ===================================================================
    FormField(
        field_name="PAF_VSNR_trim",
        field_type=FieldType.TEXT,
        label_de="Versicherungsnummer",
        section=0,
        description="Versicherungsnummer der Person, aus deren Versicherung die Leistung beantragt wird",
    ),
    FormField(
        field_name="PAF_AIGR",
        field_type=FieldType.TEXT,
        label_de="Kennzeichen",
        section=0,
        description="Kennzeichen / Aktenzeichen (soweit bekannt)",
    ),
    FormField(
        field_name="DRV_Kopf_PAF_Reha_MSAT_MSNR",
        field_type=FieldType.TEXT,
        label_de="MSAT / MSNR",
        section=0,
        description="Massnahme-Satz-Nummer / Massnahme-Nummer",
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
        field_name="VERS_STRASSE_HNR",
        field_type=FieldType.TEXT,
        label_de="Strasse, Hausnummer",
        section=0,
        description="Strasse und Hausnummer des Patienten",
    ),
    FormField(
        field_name="VERS_PLZ",
        field_type=FieldType.TEXT,
        label_de="Postleitzahl",
        section=0,
        description="Postleitzahl des Wohnorts",
    ),
    FormField(
        field_name="VERS_WOHNORT",
        field_type=FieldType.TEXT,
        label_de="Wohnort",
        section=0,
        description="Wohnort des Patienten",
    ),

    # Antragsart-Checkboxen
    FormField(
        field_name="AW_1",
        field_type=FieldType.CHECKBOX,
        label_de="Leistungen zur medizinischen Rehabilitation",
        section=0,
        description="Antrag auf Leistungen zur medizinischen Rehabilitation",
    ),
    FormField(
        field_name="AW_2",
        field_type=FieldType.CHECKBOX,
        label_de="Leistungen zur onkologischen Rehabilitation",
        section=0,
        description="Antrag auf Leistungen zur onkologischen Rehabilitation",
    ),
    FormField(
        field_name="AW_3",
        field_type=FieldType.CHECKBOX,
        label_de="Leistungen zur Teilhabe am Arbeitsleben (LTA)",
        section=0,
        description="Antrag auf Leistungen zur Teilhabe am Arbeitsleben",
    ),
    FormField(
        field_name="AW_4",
        field_type=FieldType.CHECKBOX,
        label_de="Erwerbsminderungsrente",
        section=0,
        description="Antrag auf Erwerbsminderungsrente",
    ),
    FormField(
        field_name="AW_5",
        field_type=FieldType.CHECKBOX,
        label_de="Sonstige Leistungen",
        section=0,
        description="Antrag auf sonstige Leistungen",
    ),

    # ===================================================================
    # Sektion 1: Behandlung
    # ===================================================================
    FormField(
        field_name="NAME_DER_ÄRZTIN",
        field_type=FieldType.TEXT,
        label_de="Name der Aerztin / des Arztes",
        section=1,
        description="Name der behandelnden Aerztin / des Arztes / Psychotherapeutin / Psychotherapeut",
    ),
    FormField(
        field_name="FACHRICHTUNG",
        field_type=FieldType.TEXT,
        label_de="Fachrichtung",
        section=1,
        description="Medizinische Fachrichtung der behandelnden Aerztin / des Arztes",
    ),
    FormField(
        field_name="VERS_BEHANDLUNG",
        field_type=FieldType.TEXT,
        label_de="In Behandlung seit",
        section=1,
        description="Datum, seit dem sich der Patient in Behandlung befindet (Format: TT.MM.JJJJ)",
    ),
    FormField(
        field_name="VERS_KONTAKT_AM",
        field_type=FieldType.TEXT,
        label_de="Letzter Kontakt am",
        section=1,
        description="Datum des letzten Kontakts mit dem Patienten (Format: TT.MM.JJJJ)",
    ),
    FormField(
        field_name="TELEFONNUMMER_FÜR_RÜCKFRAGEN",
        field_type=FieldType.TEXT,
        label_de="Telefonnummer fuer Rueckfragen",
        section=1,
        description="Telefonnummer der Aerztin / des Arztes fuer Rueckfragen",
    ),

    # Kontakthaeufigkeit
    FormField(
        field_name="AW_6",
        field_type=FieldType.CHECKBOX,
        label_de="woechentlich",
        section=1,
        description="Kontakthaeufigkeit: woechentlich",
    ),
    FormField(
        field_name="AW_7",
        field_type=FieldType.CHECKBOX,
        label_de="14-taegig",
        section=1,
        description="Kontakthaeufigkeit: 14-taegig / alle zwei Wochen",
    ),
    FormField(
        field_name="AW_8",
        field_type=FieldType.CHECKBOX,
        label_de="monatlich",
        section=1,
        description="Kontakthaeufigkeit: monatlich",
    ),
    FormField(
        field_name="AW_9",
        field_type=FieldType.CHECKBOX,
        label_de="seltener",
        section=1,
        description="Kontakthaeufigkeit: seltener als monatlich",
    ),

    # Antrag auf Anregung
    FormField(
        field_name="AW_10",
        field_type=FieldType.CHECKBOX,
        label_de="Antrag nicht auf meine Anregung",
        section=1,
        description="Der Antrag wurde nicht auf Anregung des Arztes gestellt",
    ),
    FormField(
        field_name="AW_11",
        field_type=FieldType.CHECKBOX,
        label_de="Antrag auf meine Anregung",
        section=1,
        description="Der Antrag wurde auf Anregung des Arztes gestellt",
    ),

    # Sprache
    FormField(
        field_name="VERS_SPRACHE_23_1",
        field_type=FieldType.TEXT,
        label_de="Sprache (falls nicht Deutsch)",
        section=1,
        description="Sprache des Patienten, falls nicht Deutsch",
    ),

    # ===================================================================
    # Sektion 2: Diagnosen
    # ===================================================================
    FormField(
        field_name="VERS_DIAGNOSE_1",
        field_type=FieldType.TEXT,
        label_de="Diagnose 1",
        section=2,
        description="Erste Diagnose (Diagnosetext)",
    ),
    FormField(
        field_name="VERS_DIAGNOSESCH_1",
        field_type=FieldType.TEXT,
        label_de="ICD-10 Code 1",
        section=2,
        description="ICD-10 Diagnoseschluessel zur ersten Diagnose (z.B. M54.5)",
    ),
    FormField(
        field_name="VERS_DIAGNOSE_2",
        field_type=FieldType.TEXT,
        label_de="Diagnose 2",
        section=2,
        description="Zweite Diagnose (Diagnosetext)",
    ),
    FormField(
        field_name="VERS_DIAGNOSESCH_2",
        field_type=FieldType.TEXT,
        label_de="ICD-10 Code 2",
        section=2,
        description="ICD-10 Diagnoseschluessel zur zweiten Diagnose",
    ),
    FormField(
        field_name="VERS_DIAGNOSE_3",
        field_type=FieldType.TEXT,
        label_de="Diagnose 3",
        section=2,
        description="Dritte Diagnose (Diagnosetext)",
    ),
    FormField(
        field_name="VERS_DIAGNOSESCH_3",
        field_type=FieldType.TEXT,
        label_de="ICD-10 Code 3",
        section=2,
        description="ICD-10 Diagnoseschluessel zur dritten Diagnose",
    ),
    FormField(
        field_name="VERS_DIAGNOSE_4",
        field_type=FieldType.TEXT,
        label_de="Diagnose 4",
        section=2,
        description="Vierte Diagnose (Diagnosetext)",
    ),
    FormField(
        field_name="VERS_DIAGNOSESCH_4",
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
        description="Daraus resultierende Funktionseinschraenkungen in Beruf und Alltag, was ist krankheitsbedingt nicht mehr moeglich",
    ),

    # ===================================================================
    # Sektion 5: Aktivitaeten und Teilhabe (Checkbox-Matrix)
    # ===================================================================
    FormField(
        field_name="AW_12",
        field_type=FieldType.CHECKBOX,
        label_de="Lernen und Wissensanwendung - beeintraechtigt",
        section=5,
        description="Aktivitaet Lernen und Wissensanwendung ist beeintraechtigt",
    ),
    FormField(
        field_name="AW_13",
        field_type=FieldType.CHECKBOX,
        label_de="Allgemeine Aufgaben und Anforderungen - beeintraechtigt",
        section=5,
        description="Aktivitaet Allgemeine Aufgaben und Anforderungen ist beeintraechtigt",
    ),
    FormField(
        field_name="AW_14",
        field_type=FieldType.CHECKBOX,
        label_de="Kommunikation - beeintraechtigt",
        section=5,
        description="Aktivitaet Kommunikation ist beeintraechtigt",
    ),
    FormField(
        field_name="AW_15",
        field_type=FieldType.CHECKBOX,
        label_de="Mobilitaet - beeintraechtigt",
        section=5,
        description="Aktivitaet Mobilitaet ist beeintraechtigt",
    ),
    FormField(
        field_name="AW_16",
        field_type=FieldType.CHECKBOX,
        label_de="Selbstversorgung - beeintraechtigt",
        section=5,
        description="Aktivitaet Selbstversorgung ist beeintraechtigt",
    ),
    FormField(
        field_name="AW_17",
        field_type=FieldType.CHECKBOX,
        label_de="Haeusl. Leben / Haushaltsfuehrung - beeintraechtigt",
        section=5,
        description="Aktivitaet Haeusliches Leben und Haushaltsfuehrung ist beeintraechtigt",
    ),
    FormField(
        field_name="AW_18",
        field_type=FieldType.CHECKBOX,
        label_de="Interpersonelle Aktivitaeten - beeintraechtigt",
        section=5,
        description="Interpersonelle Aktivitaeten und Beziehungen sind beeintraechtigt",
    ),
    FormField(
        field_name="AW_19",
        field_type=FieldType.CHECKBOX,
        label_de="Bedeutende Lebensbereiche (Arbeit) - beeintraechtigt",
        section=5,
        description="Bedeutende Lebensbereiche wie Arbeit und Beschaeftigung sind beeintraechtigt",
    ),
    FormField(
        field_name="AW_20",
        field_type=FieldType.CHECKBOX,
        label_de="Erziehung / Bildung - beeintraechtigt",
        section=5,
        description="Gemeinschafts-, soziales und staatsbuergerliches Leben (Erziehung/Bildung) ist beeintraechtigt",
    ),

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
        field_name="VERS_KOERPERLAENGE",
        field_type=FieldType.TEXT,
        label_de="Koerperlaenge (cm)",
        section=7,
        description="Koerperlaenge / Koerpergroesse in Zentimetern",
    ),
    FormField(
        field_name="VERS_GEWICHT",
        field_type=FieldType.TEXT,
        label_de="Gewicht (kg)",
        section=7,
        description="Koerpergewicht in Kilogramm",
    ),

    # ===================================================================
    # Sektion 8: Medizinisch-technische Befunde
    # ===================================================================
    FormField(
        field_name="MED_TECHN_BEFUNDE",
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
    # Sektion 10: Risikofaktoren
    # ===================================================================
    FormField(
        field_name="SONSTIGES",
        field_type=FieldType.TEXT,
        label_de="Sonstiges",
        section=10,
        description="Sonstige relevante Informationen und Risikofaktoren",
    ),
    FormField(
        field_name="AW_21",
        field_type=FieldType.CHECKBOX,
        label_de="Bewegungsmangel",
        section=10,
        description="Risikofaktor: Bewegungsmangel",
    ),
    FormField(
        field_name="AW_22",
        field_type=FieldType.CHECKBOX,
        label_de="Uebergewicht",
        section=10,
        description="Risikofaktor: Uebergewicht",
    ),
    FormField(
        field_name="AW_23",
        field_type=FieldType.CHECKBOX,
        label_de="Drogen / Medikamentenmissbrauch",
        section=10,
        description="Risikofaktor: Drogen- oder Medikamentenmissbrauch",
    ),
    FormField(
        field_name="AW_24",
        field_type=FieldType.CHECKBOX,
        label_de="Tabakkonsum",
        section=10,
        description="Risikofaktor: Tabakkonsum / Rauchen",
    ),
    FormField(
        field_name="AW_25",
        field_type=FieldType.CHECKBOX,
        label_de="Alkoholkonsum",
        section=10,
        description="Risikofaktor: erhoehter Alkoholkonsum",
    ),
    FormField(
        field_name="AW_26",
        field_type=FieldType.CHECKBOX,
        label_de="Medikamenteneinnahme",
        section=10,
        description="Risikofaktor: dauerhafte Medikamenteneinnahme",
    ),

    # ===================================================================
    # Sektion 11: Arbeitsunfaehigkeit / Prognose
    # ===================================================================
    FormField(
        field_name="VERS_AU_GRUND",
        field_type=FieldType.TEXT,
        label_de="Grund der Arbeitsunfaehigkeit",
        section=11,
        description="Grund der Arbeitsunfaehigkeit",
    ),
    FormField(
        field_name="ARZT_UNTERS_DATUM",
        field_type=FieldType.TEXT,
        label_de="Datum der Untersuchung",
        section=11,
        description="Datum der aerztlichen Untersuchung (Format: TT.MM.JJJJ)",
    ),
    FormField(
        field_name="VERS_BESSERUNG_DATUM_1",
        field_type=FieldType.TEXT,
        label_de="Besserung seit (Datum 1)",
        section=11,
        description="Datum, seit dem eine Besserung eingetreten ist (Format: TT.MM.JJJJ)",
    ),
    FormField(
        field_name="VERS_BESSERUNG_DATUM_2",
        field_type=FieldType.TEXT,
        label_de="Besserung seit (Datum 2)",
        section=11,
        description="Zweites Datum fuer Besserung (Format: TT.MM.JJJJ)",
    ),
    FormField(
        field_name="VERS_VERSCHLECHTERUNG_DATUM",
        field_type=FieldType.TEXT,
        label_de="Verschlechterung seit",
        section=11,
        description="Datum, seit dem eine Verschlechterung eingetreten ist (Format: TT.MM.JJJJ)",
    ),
    FormField(
        field_name="AW_24_1",
        field_type=FieldType.CHECKBOX,
        label_de="Reisefaehigkeit / mit Begleitung",
        section=11,
        description="Patient ist reisefaehig, ggf. mit Begleitung",
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
]

S0051_DEFINITION = FormDefinition(
    form_id="S0051",
    form_title="Befundbericht fuer die Deutsche Rentenversicherung",
    fields=S0051_FIELDS,
)
