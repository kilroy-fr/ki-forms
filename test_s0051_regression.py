from pathlib import Path
import re

import pikepdf

from app.form_definitions.s0051 import S0051_DEFINITION
from app.models.form_schema import FieldType
from app.services.pdf_filler import fill_pdf


def _build_fields():
    fields = [f.model_copy() for f in S0051_DEFINITION.fields]

    radio_selection = {
        "AW_1": "AW_1_med_reha",
        "AW_2": "AW_2_woechentlich",
        "AW_3": "AW_3_nein",
        "AW_4": "AW_4_nicht",
        "AW_5": "AW_5_nicht",
        "AW_6": "AW_6_nicht",
        "AW_7": "AW_7_nicht",
        "AW_8": "AW_8_nicht",
        "AW_9": "AW_9_nicht",
        "AW_10": "AW_10_nicht",
        "AW_11": "AW_11_nicht",
        "AW_12": "AW_12_nicht",
        "AW_14": "AW_14_uebergewicht",
        "AW_20": "AW_20_nein",
        "AW_21": "AW_21_nein",
        "AW_23": "AW_23_ja",
        "AW_24": "AW_24_nein",
        "AW_25": "AW_25_nein",
        "AW_26": "AW_26_nein",
    }
    checkbox_on = {"AW_13", "AW_15", "AW_16", "AW_17", "AW_18", "AW_19"}
    text_values = {
        "PAF_VSNR_trim": "D684016264",
        "PAF_AIGR": "1240080590",
        "MSAT_MSNR": "123",
        "DRV_Kopf_PAF_Reha_MSAT_MSNR": "123",
        "PAT_NAME": "Overmans, Gertrud",
        "PAT_Geburtsdatum": "06.01.1980",
        "PAT_STRASSE_HNR": "Jakobsgäßchen 3",
        "PAT_PLZ": "91541",
        "PAT_WOHNORT": "Ansbach",
        "NAME_DER_ÄRZTIN": "Jan Overmans",
        "TELEFONNUMMER_FÜR_RÜCKFRAGEN": "01775571634",
    }

    for f in fields:
        if f.field_type == FieldType.TEXT and f.field_name in text_values:
            f.value = text_values[f.field_name]
        elif f.field_type == FieldType.CHECKBOX and f.field_name in checkbox_on:
            f.value = "ja"
        elif f.field_type == FieldType.RADIO:
            if radio_selection.get(f.radio_group) == f.field_name:
                f.value = "ja"

    by_name = {f.field_name: f for f in fields}
    for src, dst in [
        ("MSAT_MSNR", "DRV_Kopf_PAF_Reha_MSAT_MSNR"),
        ("PAT_STRASSE_HNR", "VERS_STRASSE_HNR"),
        ("PAT_PLZ", "VERS_PLZ"),
        ("PAT_WOHNORT", "VERS_WOHNORT"),
    ]:
        if by_name.get(src) and by_name.get(dst):
            by_name[dst].value = by_name[src].value
    return fields


def _field_by_name(pdf: pikepdf.Pdf):
    acroform = pdf.Root["/AcroForm"]
    out = {}
    for ref in acroform["/Fields"]:
        f = ref.resolve() if hasattr(ref, "resolve") else ref
        t = f.get("/T")
        if t is None:
            continue
        out[str(t)] = f
    return out


def _selected_widget_has_valid_as(field_obj: pikepdf.Dictionary) -> bool:
    kids = field_obj.get("/Kids") or []
    if not kids:
        asv = field_obj.get("/AS")
        if asv is None or str(asv) == "/Off":
            return False
        apn = field_obj.get("/AP", {}).get("/N", {})
        try:
            return any(str(k) == str(asv) for k in apn.keys())
        except Exception:
            return False

    for kid_ref in kids:
        kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
        if not isinstance(kid, pikepdf.Dictionary):
            continue
        asv = kid.get("/AS")
        if asv is None or str(asv) == "/Off":
            continue
        apn = kid.get("/AP", {}).get("/N", {})
        try:
            return any(str(k) == str(asv) for k in apn.keys())
        except Exception:
            return False
    return False


def main():
    template = Path("data/S0051.pdf")
    output = Path("output/S0051_regression_test.pdf")
    fields = _build_fields()
    fill_pdf(template, output, fields)

    pdf = pikepdf.open(str(output))
    by_name = _field_by_name(pdf)

    groups = [
        "AW_1", "AW_2", "AW_3", "AW_4", "AW_5", "AW_6", "AW_7", "AW_8", "AW_9",
        "AW_10", "AW_11", "AW_12", "AW_14", "AW_20", "AW_21", "AW_23", "AW_24", "AW_25", "AW_26",
    ]
    checks = ["AW_13", "AW_15", "AW_16", "AW_17", "AW_18", "AW_19"]

    failed = []
    for g in groups:
        f = by_name.get(g)
        if f is None:
            failed.append(f"{g}: fehlt im PDF")
            continue
        if f.get("/V") is None or str(f.get("/V")) == "/Off":
            failed.append(f"{g}: /V nicht gesetzt")
            continue
        if not _selected_widget_has_valid_as(f):
            failed.append(f"{g}: sichtbarer State ungültig (AS/AP)")

    for c in checks:
        f = by_name.get(c)
        if f is None:
            failed.append(f"{c}: fehlt im PDF")
            continue
        if f.get("/V") is None or str(f.get("/V")) == "/Off":
            failed.append(f"{c}: Checkbox nicht gesetzt")

    for txt in ["PAF_VSNR_trim", "PAF_AIGR", "DRV_Kopf_PAF_Reha_MSAT_MSNR", "VERS_PLZ", "VERS_WOHNORT"]:
        f = by_name.get(txt)
        if f is None or not f.get("/V"):
            failed.append(f"{txt}: Textwert fehlt")

    if failed:
        print("REGRESSION FEHLER")
        for e in failed:
            print(" -", e)
        raise SystemExit(1)

    print("REGRESSION OK")
    print(f"Datei: {output}")


if __name__ == "__main__":
    main()
