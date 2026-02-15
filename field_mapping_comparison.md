# Feldmapping-Probleme S0051

## Kritische Unterschiede zwischen s0051.py und tatsächlichen PDF-Feldnamen

### 1. Felder die KOMPLETT FEHLEN im PDF:
- `NAME_DER_ÄRZTIN` → **KEIN entsprechendes PDF-Feld**
- `KENNZEICHEN` → **KEIN entsprechendes PDF-Feld**
- `DRV_Kopf_PAF_Reha_MSAT_MSNR` → **KEIN entsprechendes PDF-Feld**
- `MSAT_MSNR` → **KEIN entsprechendes PDF-Feld**
- `VERS_NAME` → **KEIN entsprechendes PDF-Feld**
- `PAT_STRASSE_HNR` → **KEIN entsprechendes PDF-Feld**
- `PAT_PLZ_WOHNORT` → **KEIN entsprechendes PDF-Feld**

### 2. Falsche Feldnamen (müssen umbenannt werden):

| s0051.py                      | Tatsächliches PDF-Feld            |
|-------------------------------|-----------------------------------|
| `VERS_WOHNORT`                | `VERS_PLZ`                        |
| `BEHANDLUNG_SEIT`             | `VERS_BEHANDLUNG`                 |
| `KONTAKT_LETZTER`             | `VERS_KONTAKT_AM`                 |
| `TEL`                         | `TELEFONNUMMER_FÜR_RÜCKFRAGEN`    |
| `DIAG_1`                      | `VERS_DIAGNOSE_1`                 |
| `ICD_1`                       | `VERS_DIAGNOSESCH_1`              |
| `DIAG_2`                      | `VERS_DIAGNOSE_2`                 |
| `ICD_2`                       | `VERS_DIAGNOSESCH_2`              |
| `DIAG_3`                      | `VERS_DIAGNOSE_3`                 |
| `ICD_3`                       | `VERS_DIAGNOSESCH_3`              |
| `DIAG_4`                      | `VERS_DIAGNOSE_4`                 |
| `ICD_4`                       | `VERS_DIAGNOSESCH_4`              |
| `GROESSE_CM`                  | `VERS_KOERPERLAENGE`              |
| `GEWICHT_KG`                  | `VERS_GEWICHT`                    |
| `TECHNISCHE_BEFEUNDE`         | `MED_TECHN_BEFUNDE`               |
| `AU_WEGEN`                    | `VERS_AU_GRUND`                   |
| `VERS_BESSERUNG_DATUM`        | `VERS_BESSERUNG_DATUM_1`          |
| `SPRACHE`                     | `VERS_SPRACHE_23_1`               |

### 3. Falsche Feldtypen:

Die folgenden Felder sind in s0051.py als **CHECKBOX** definiert, sind aber im PDF tatsächlich **RADIO-BUTTONS** (2 Optionen: ja/nein):
- `AW_17` (Bewegungsmangel)
- `AW_18` (Übergewicht)
- `AW_19` (Drogen)
- `AW_20` (Medikamente)
- `AW_21` (Untergewicht)
- `AW_22` (Nikotin)
- `AW_23` (Alkohol)

### 4. Fehlende PDF-Felder in s0051.py:

Diese Felder existieren im PDF, sind aber nicht in der Formulardefinition:
- `VERS_STRASSE_HNR` (existiert im PDF)
- `VERS_BESSERUNG_DATUM_2`

## Lösung

Alle field_name Einträge in s0051.py müssen auf die tatsächlichen PDF-Feldnamen korrigiert werden.
