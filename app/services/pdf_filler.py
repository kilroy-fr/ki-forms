import logging
import re
from pathlib import Path

import pikepdf

from app.models.form_schema import FormField, FieldType

logger = logging.getLogger(__name__)


def fill_pdf(
    template_path: Path,
    output_path: Path,
    fields: list[FormField],
) -> Path:
    """
    Oeffnet die PDF-Vorlage und schreibt die Feldwerte hinein.
    - Textfelder und Checkboxen werden ueber Page-Annotations gefuellt.
    - Radio-Buttons werden ueber den AcroForm-Feldbaum gefuellt,
      da Radio-Widgets kein eigenes /T haben (erben es vom Parent).
    """
    pdf = pikepdf.open(str(template_path))

    # Lookup-Maps erstellen
    text_map: dict[str, str] = {}
    checkbox_map: dict[str, str] = {}
    radio_map: dict[str, str] = {}  # radio_group (= PDF-Feldname) -> pdf_state

    for f in fields:
        if f.field_type == FieldType.TEXT:
            if f.value:
                text_map[f.field_name] = _normalize_text_value_for_field(f.field_name, f.value)
        elif f.field_type == FieldType.CHECKBOX:
            if f.value:
                checkbox_map[f.field_name] = f.value
        elif f.field_type == FieldType.RADIO:
            # Nur tatsaechlich ausgewaehlte Radio-Optionen uebernehmen.
            if f.value and str(f.value).strip().lower() in ("ja", "yes", "true", "1", "on"):
                if f.pdf_state and f.radio_group:
                    radio_map[f.radio_group] = f.pdf_state

    if radio_map:
        logger.debug(f"Radio-Gruppen mit Auswahl: {sorted(radio_map.keys())}")
    else:
        logger.warning("Keine Radio-Auswahlen fuer PDF erhalten (radio_map ist leer)")

    filled_count = 0

    # --- Text- und Checkbox-Felder ueber Page-Annotations fuellen ---
    for page in pdf.pages:
        if "/Annots" not in page:
            continue

        for annot in page["/Annots"]:
            annot_obj = annot.resolve() if hasattr(annot, "resolve") else annot

            field_name_obj = annot_obj.get("/T")
            if field_name_obj is None:
                continue

            try:
                field_name = str(field_name_obj)
            except UnicodeDecodeError:
                # Fallback für Latin-1 kodierte Feldnamen (deutsche Umlaute)
                try:
                    field_name = bytes(field_name_obj).decode('latin-1')
                except:
                    logger.warning(f"Konnte Feldname nicht dekodieren, überspringe")
                    continue

            if field_name in text_map:
                _set_text_field(pdf, annot_obj, text_map[field_name])
                filled_count += 1
            elif field_name in checkbox_map:
                _set_checkbox_field(annot_obj, checkbox_map[field_name])
                filled_count += 1

    # --- Radio-Buttons ueber AcroForm-Feldbaum fuellen ---
    acroform = pdf.Root.get("/AcroForm")
    if acroform and "/Fields" in acroform:
        if text_map:
            for field_ref in acroform["/Fields"]:
                filled_count += _fill_text_in_tree(field_ref, text_map, pdf)
        if radio_map:
            for field_ref in acroform["/Fields"]:
                filled_count += _fill_radio_in_tree(field_ref, radio_map)
            _repair_section5_radio_appearances(pdf)

    # Mit eigenen Appearance-Streams fuer gefuellte Textfelder brauchen wir
    # kein viewer-spezifisches Regenerieren.
    if "/AcroForm" in pdf.Root:
        pdf.Root["/AcroForm"][pikepdf.Name("/NeedAppearances")] = False
    else:
        logger.warning("Kein AcroForm im PDF gefunden")

    pdf.save(str(output_path))
    pdf.close()

    # Finale Sicherheitsreparatur auf der bereits gespeicherten Datei.
    # Dieser zweite Pass hat sich als robust erwiesen bei Section-5-Radios.
    try:
        post_pdf = pikepdf.open(str(output_path), allow_overwriting_input=True)
        _repair_section5_radio_appearances(post_pdf)
        _burn_in_section5_marks(post_pdf)
        _burn_in_problematic_button_marks(post_pdf)
        if "/AcroForm" in post_pdf.Root:
            post_pdf.Root["/AcroForm"][pikepdf.Name("/NeedAppearances")] = False
        post_pdf.save(str(output_path))
        post_pdf.close()
    except Exception as ex:
        logger.warning(f"Post-Repair fehlgeschlagen: {ex}")

    logger.info(f"PDF gespeichert: {output_path} ({filled_count} Felder ausgefuellt)")
    return output_path


# ---------------------------------------------------------------------------
# Radio-Buttons: AcroForm-Feldbaum durchlaufen
# ---------------------------------------------------------------------------

def _fill_radio_in_tree(field_ref, radio_map: dict[str, str], parent_name: str = None) -> int:
    """AcroForm-Feldbaum rekursiv durchlaufen und Radio-Gruppen fuellen."""
    field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref

    if not isinstance(field_obj, pikepdf.Dictionary):
        return 0

    t = field_obj.get("/T")
    if t is not None:
        try:
            name = str(t)
        except UnicodeDecodeError:
            # Fallback für Latin-1 kodierte Feldnamen
            try:
                name = bytes(t).decode('latin-1')
            except:
                name = parent_name
    else:
        name = parent_name

    kids = field_obj.get("/Kids")

    if name and name in radio_map and kids:
        # Dieses Feld ist eine Radio-Gruppe die gefuellt werden soll
        selected_state = radio_map[name]
        return _activate_radio_option(field_obj, kids, selected_state, name)

    if kids:
        # Zwischenknoten - weiter in die Tiefe
        count = 0
        for kid_ref in kids:
            count += _fill_radio_in_tree(kid_ref, radio_map, name)
        return count

    return 0


def _fill_text_in_tree(field_ref, text_map: dict[str, str], pdf: pikepdf.Pdf, parent_name: str = None) -> int:
    """AcroForm-Baum fuer Textfelder (/Tx) rekursiv verarbeiten."""
    field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref
    if not isinstance(field_obj, pikepdf.Dictionary):
        return 0

    t = field_obj.get("/T")
    name = None
    if t is not None:
        try:
            name = str(t)
        except Exception:
            try:
                name = bytes(t).decode("latin-1")
            except Exception:
                name = None
    if not name:
        name = parent_name

    kids = field_obj.get("/Kids")
    ft = field_obj.get("/FT")
    ft_name = str(ft) if ft is not None else ""
    count = 0

    if name and name in text_map and (ft_name == "/Tx" or kids):
        value = text_map[name]
        field_ff = field_obj.get("/Ff")
        field_max_len = field_obj.get("/MaxLen")
        field_obj[pikepdf.Name("/V")] = pikepdf.String(value)

        if kids:
            for kid_ref in kids:
                kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
                if not isinstance(kid, pikepdf.Dictionary):
                    continue
                kid[pikepdf.Name("/V")] = pikepdf.String(value)
                _set_text_widget_appearance(pdf, kid, value, field_ff=field_ff, field_max_len=field_max_len)
        else:
            _set_text_widget_appearance(pdf, field_obj, value, field_ff=field_ff, field_max_len=field_max_len)

        count += 1

    if kids:
        for kid_ref in kids:
            count += _fill_text_in_tree(kid_ref, text_map, pdf, name)

    return count


def _activate_radio_option(field_obj: pikepdf.Dictionary, kids, selected_state: str, field_name: str) -> int:
    """
    selected_state muss EXACT der PDF-On-State sein (Key unter /AP /N), z.B.:
      'Keine Beeintr鋍htigungen', 'Einschr鋘kungen', 'Personelle Hilfe n鰐ig', 'nicht durchf黨rbar', 'Keine Angabe m鰃lich'
    """
    logger.debug(f"Aktiviere Radio: Feld={field_name}, PDF-State='{selected_state}'")

    set_count = 0
    found = False
    selected_key_obj = None

    selected_state_norm = _normalize_state_text(selected_state)
    selected_state_token = _canonical_state_token(selected_state_norm)

    # Robuster Pfad fuer bekannte Radio-Gruppen mit stabiler Widget-Reihenfolge.
    known_states = _known_radio_states_for_group(field_name)
    if known_states and len(kids) >= len(known_states):
        for idx, kid_ref in enumerate(kids):
            kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
            if not isinstance(kid, pikepdf.Dictionary):
                continue

            state = known_states[idx] if idx < len(known_states) else None
            token = _canonical_state_token(_normalize_state_text(state)) if state else ""
            if token and token == selected_state_token:
                key_obj = _find_on_state_key_for_text(kid, state) if state else None
                if key_obj is None:
                    key_obj = _get_first_on_state_key(kid)
                if key_obj is None and state:
                    key_obj = _pdf_name_from_legacy_text(state)
                if key_obj is None:
                    key_obj = pikepdf.Name("/Yes")
                kid[pikepdf.Name("/AS")] = key_obj
                selected_key_obj = key_obj
                found = True
                set_count += 1
            else:
                kid[pikepdf.Name("/AS")] = pikepdf.Name("/Off")

        if not found:
            logger.warning(
                f"Radio-State nicht gefunden: Feld={field_name}, gesucht='{selected_state}', "
                f"vorhanden={known_states}"
            )
            return 0

        if selected_key_obj is not None:
            field_obj[pikepdf.Name("/V")] = selected_key_obj
        return set_count

    for kid_ref in kids:
        kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
        if not isinstance(kid, pikepdf.Dictionary):
            continue

        # Jeder Radio-Widget hat genau einen "On"-State (zusätzlich zu Off)
        on_state, on_state_key = _get_widget_on_state_info(kid)

        on_state_norm = _normalize_state_text(on_state)
        on_state_token = _canonical_state_token(on_state_norm)

        state_matches = (on_state_norm == selected_state_norm)
        if not state_matches and selected_state_token and on_state_token:
            state_matches = (on_state_token == selected_state_token)

        if state_matches:
            key_obj = on_state_key if on_state_key is not None else _pdf_name_from_text(selected_state)
            kid[pikepdf.Name("/AS")] = key_obj
            selected_key_obj = key_obj
            found = True
            set_count += 1
        else:
            kid[pikepdf.Name("/AS")] = pikepdf.Name("/Off")

    if not found:
        logger.warning(
            f"Radio-State nicht gefunden: Feld={field_name}, gesucht='{selected_state}', "
            f"vorhanden={_collect_kid_states(kids)}"
        )
        return 0

    field_obj[pikepdf.Name("/V")] = selected_key_obj if selected_key_obj is not None else _pdf_name_from_text(selected_state)
    return set_count


def _collect_kid_states(kids) -> list[str]:
    """Alle On-States der Kids sammeln (fuer Debug-Logging)."""
    states = []
    for kid_ref in kids:
        kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
        if isinstance(kid, pikepdf.Dictionary):
            states.append(_get_widget_on_state_info(kid)[0])
    return states


# ---------------------------------------------------------------------------
# Text- und Checkbox-Felder
# ---------------------------------------------------------------------------

def _set_text_field(pdf: pikepdf.Pdf, annot: pikepdf.Dictionary, value: str):
    """Textfeld-Wert in die PDF-Annotation schreiben."""
    annot[pikepdf.Name("/V")] = pikepdf.String(value)
    _set_text_widget_appearance(pdf, annot, value)


def _set_text_widget_appearance(
    pdf: pikepdf.Pdf,
    annot: pikepdf.Dictionary,
    value: str,
    field_ff=None,
    field_max_len=None,
) -> None:
    """Erzeugt einen statischen /AP-/N-Stream fuer ein Text-Widget."""
    rect = annot.get("/Rect")
    if not isinstance(rect, pikepdf.Array) or len(rect) != 4:
        return

    try:
        x0, y0, x1, y1 = [float(v) for v in rect]
    except Exception:
        return

    width = max(1.0, abs(x1 - x0))
    height = max(1.0, abs(y1 - y0))
    font_size = max(7.0, min(11.0, height * 0.6))
    leading = font_size * 1.15
    max_lines = max(1, int(height // leading))

    ff_value = _to_int_or_default(annot.get("/Ff"), 0)
    if ff_value == 0 and field_ff is not None:
        ff_value = _to_int_or_default(field_ff, 0)
    max_len = _to_int_or_default(annot.get("/MaxLen"), None)
    if max_len is None and field_max_len is not None:
        max_len = _to_int_or_default(field_max_len, None)

    is_multiline = bool(ff_value & (1 << 12))
    is_comb = bool(ff_value & (1 << 24)) and max_len and max_len > 0

    if is_comb:
        lines = []
    elif is_multiline:
        lines = _wrap_text_lines(value or "", width - 4.0, font_size)[:max_lines]
    else:
        lines = _wrap_text_lines(value or "", width - 4.0, font_size)[:1]

    parts = [
        "q",
        "BT",
        f"/F0 {font_size:.2f} Tf",
        "0 g",
    ]

    if is_comb:
        text = re.sub(r"\s+", "", value or "")
        if max_len:
            text = text[:max_len]
        cell_width = width / float(max_len or 1)
        baseline_y = max(1.0, (height - font_size) / 2.0)
        for idx, ch in enumerate(text):
            ch_width = _approx_text_width(ch, font_size)
            cell_x = idx * cell_width
            text_x = cell_x + max(0.0, (cell_width - ch_width) / 2.0)
            literal = _pdf_literal_string(ch)
            parts.append(f"1 0 0 1 {text_x:.3f} {baseline_y:.3f} Tm")
            parts.append(f"({literal}) Tj")
    else:
        y = height - font_size - 1.0
        for line in lines:
            literal = _pdf_literal_string(line)
            parts.append(f"1 0 0 1 2 {y:.3f} Tm")
            parts.append(f"({literal}) Tj")
            y -= leading

    parts.extend(["ET", "Q"])
    content = ("\n".join(parts) + "\n").encode("ascii", errors="ignore")

    stream = pdf.make_stream(content)
    stream[pikepdf.Name("/Type")] = pikepdf.Name("/XObject")
    stream[pikepdf.Name("/Subtype")] = pikepdf.Name("/Form")
    stream[pikepdf.Name("/BBox")] = pikepdf.Array([0, 0, width, height])
    stream[pikepdf.Name("/Resources")] = pikepdf.Dictionary(
        Font=pikepdf.Dictionary(
            F0=pikepdf.Dictionary(
                Type=pikepdf.Name("/Font"),
                Subtype=pikepdf.Name("/Type1"),
                BaseFont=pikepdf.Name("/Helvetica"),
                Encoding=pikepdf.Name("/WinAnsiEncoding"),
            )
        )
    )

    ap_dict = annot.get("/AP")
    if not isinstance(ap_dict, pikepdf.Dictionary):
        ap_dict = pikepdf.Dictionary()
        annot[pikepdf.Name("/AP")] = ap_dict
    ap_dict[pikepdf.Name("/N")] = stream


def _pdf_literal_string(text: str) -> str:
    """Escaped PDF-Literal-String (WinAnsi/CP1252) fuer Appearance-Streams."""
    b = (text or "").encode("cp1252", errors="replace")
    out = []
    for byte in b:
        if byte in (40, 41, 92):  # ( ) \
            out.append("\\" + chr(byte))
        elif 32 <= byte <= 126:
            out.append(chr(byte))
        else:
            out.append(f"\\{byte:03o}")
    return "".join(out)



def _to_int_or_default(value, default):
    """Konvertiert PDF-Zahlen robust nach int, sonst default."""
    try:
        return int(value)
    except Exception:
        return default


def _approx_text_width(text: str, font_size: float) -> float:
    """Einfache Breiten-Schaetzung fuer Helvetica zur Zeilenumbruch-Logik."""
    if not text:
        return 0.0
    total = 0.0
    for ch in text:
        if ch in "il.,:;|!'` ":
            factor = 0.28
        elif ch in "mwMW@#%&":
            factor = 0.86
        else:
            factor = 0.56
        total += factor * font_size
    return total


def _split_long_token(token: str, max_width: float, font_size: float) -> list[str]:
    """Bricht lange Woerter hart um, falls sie nicht in eine Zeile passen."""
    if not token:
        return [""]
    out: list[str] = []
    current = ""
    for ch in token:
        candidate = current + ch
        if current and _approx_text_width(candidate, font_size) > max_width:
            out.append(current)
            current = ch
        else:
            current = candidate
    if current:
        out.append(current)
    return out or [token]


def _wrap_text_lines(text: str, max_width: float, font_size: float) -> list[str]:
    """Text in Zeilen umbrechen (inkl. harter Umbruch bei zu langen Tokens)."""
    if max_width <= 1:
        return [text or ""]

    paragraphs = (text or "").replace("\r", "").split("\n")
    lines: list[str] = []

    for para in paragraphs:
        words = para.split()
        if not words:
            lines.append("")
            continue

        current = ""
        for word in words:
            if _approx_text_width(word, font_size) > max_width:
                chunks = _split_long_token(word, max_width, font_size)
                if current:
                    lines.append(current)
                    current = ""
                lines.extend(chunks[:-1])
                current = chunks[-1]
                continue

            candidate = word if not current else f"{current} {word}"
            if _approx_text_width(candidate, font_size) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        if current or not words:
            lines.append(current)

    return lines or [""]


def _normalize_text_value_for_field(field_name: str, value: str) -> str:
    """Feldspezifische Normalisierung fuer problematische Textfelder."""
    text = (value or "").strip()

    if field_name in ("VERS_GEBDAT", "PAT_Geburtsdatum"):
        return re.sub(r"\D", "", text)[:8]

    if re.fullmatch(r"VERS_DIAGNOSESCH_[1-4]", field_name or ""):
        return re.sub(r"[^A-Za-z0-9]", "", text).upper()[:5]

    return text
def _set_checkbox_field(annot: pikepdf.Dictionary, value: str):
    """Checkbox setzen. Wert 'ja' = angekreuzt, sonst nicht."""
    if value.lower() in ("ja", "yes", "true", "1", "on"):
        on_state, on_state_key = _get_widget_on_state_info(annot)
        key_obj = on_state_key if on_state_key is not None else _pdf_name_from_text(on_state)
        annot[pikepdf.Name("/V")] = key_obj
        annot[pikepdf.Name("/AS")] = key_obj
    else:
        annot[pikepdf.Name("/V")] = pikepdf.Name("/Off")
        annot[pikepdf.Name("/AS")] = pikepdf.Name("/Off")


def _get_widget_on_state_info(annot: pikepdf.Dictionary) -> tuple[str, object]:
    """
    Den 'On'-State-Namen eines Widgets ermitteln.
    Checkboxen/Radio-Buttons verwenden /Yes, /On, /1 oder beschreibende Namen.
    Rueckgabe: (lesbarer Name, originales Key-Objekt aus /AP /N)
    """
    _normalize_widget_ap_names(annot)

    ap = annot.get("/AP")
    if ap is None:
        return "Yes", pikepdf.Name("/Yes")

    normal = ap.get("/N")
    if normal is None:
        return "Yes", pikepdf.Name("/Yes")

    if not isinstance(normal, pikepdf.Dictionary):
        return "Yes", pikepdf.Name("/Yes")

    # Methode 1: Versuche mit as_dict() um rohe Objekte zu bekommen
    try:
        items = list(normal.items())

        for key_obj, value in items:
            name = None

            # Extrahiere den Key-Namen mit Latin-1 Handling
            try:
                # Prüfe ob es ein Name-Objekt ist
                if hasattr(key_obj, '__str__'):
                    # str() kann UnicodeDecodeError werfen - fangen wir es ab
                    try:
                        raw_name = str(key_obj)
                        clean_name = raw_name.lstrip("/")

                        # Prüfe auf Surrogate (0xdc00-0xdcff)
                        has_surrogates = any(0xdc00 <= ord(c) <= 0xdcff for c in clean_name)

                        if has_surrogates:
                            # Konvertiere Surrogate zurück zu Latin-1
                            fixed_bytes = bytearray()
                            for char in clean_name:
                                if 0xdc00 <= ord(char) <= 0xdcff:
                                    fixed_bytes.append(ord(char) - 0xdc00)
                                else:
                                    fixed_bytes.append(ord(char))
                            name = fixed_bytes.decode('latin-1')
                        else:
                            name = clean_name
                    except UnicodeDecodeError:
                        # str() hat UTF-8 Fehler - versuche bytes-Konvertierung
                        if hasattr(key_obj, '_name'):
                            # Direkter Zugriff auf internal _name (bytes)
                            name_bytes = key_obj._name
                            if isinstance(name_bytes, bytes):
                                name = name_bytes.decode('latin-1').lstrip(b'/').lstrip('/')
                        elif hasattr(key_obj, 'unparse'):
                            # Alternative: unparse() liefert bytes
                            name_bytes = key_obj.unparse()
                            if isinstance(name_bytes, bytes):
                                name = name_bytes.decode('latin-1').lstrip(b'/').lstrip('/')

                # Fallback: bytes-Konvertierung
                if not name and isinstance(key_obj, bytes):
                    name = key_obj.decode('latin-1').lstrip("/")

            except Exception:
                pass

            if name and name != "Off":
                return name, key_obj

    except Exception:
        pass

    return "Yes", pikepdf.Name("/Yes")


def _normalize_widget_ap_names(annot: pikepdf.Dictionary) -> None:
    """Normalisiert /AP /N State-Keys eines Widgets auf gueltige Unicode-Namen."""
    ap = annot.get("/AP")
    if ap is None:
        return

    normal = ap.get("/N")
    if normal is None or not isinstance(normal, pikepdf.Dictionary):
        return

    new_normal = pikepdf.Dictionary()
    changed = False

    try:
        items = list(normal.items())
    except Exception:
        return

    for key_obj, value in items:
        name = _decode_pdf_name_key(key_obj)
        if not name:
            continue

        new_key = _pdf_name_from_text(name)
        new_normal[new_key] = value

        try:
            original = str(key_obj).lstrip("/")
            if original != name:
                changed = True
        except Exception:
            changed = True

    if changed and len(new_normal) > 0:
        ap[pikepdf.Name("/N")] = new_normal


def _decode_pdf_name_key(key_obj) -> str | None:
    """Dekodiert einen PDF-Name-Key robust (inkl. Surrogate-Latin-1-Fix)."""
    try:
        raw_name = str(key_obj).lstrip("/")
    except Exception:
        return None

    has_surrogates = any(0xDC00 <= ord(c) <= 0xDCFF for c in raw_name)
    if not has_surrogates:
        return raw_name

    fixed_bytes = bytearray()
    for char in raw_name:
        code = ord(char)
        if 0xDC00 <= code <= 0xDCFF:
            fixed_bytes.append(code - 0xDC00)
        else:
            fixed_bytes.append(code)
    return fixed_bytes.decode("latin-1")


def _pdf_name_from_text(text: str) -> pikepdf.Name:
    """
    Erzeugt ein PDF-Name-Objekt mit stabiler #xx-Escaping-Kodierung (UTF-8),
    damit /AS, /V und /AP/N-Keys byte-identisch verglichen werden koennen.
    """
    b = text.encode("utf-8")
    out = "/"
    for byte in b:
        # Zulassen: sichtbare ASCII-Zeichen ausser '#'
        if 33 <= byte <= 126 and byte != 35:
            out += chr(byte)
        else:
            out += f"#{byte:02x}"
    return pikepdf.Name(out)


def _pdf_name_from_legacy_text(text: str) -> pikepdf.Name:
    """
    Erzeugt einen PDF-Namen aus einem bereits dekodierten (oft Latin-1) State-Text.
    Das verhindert Surrogate-Probleme beim Zurueckschreiben.
    """
    try:
        b = text.encode("latin-1")
    except UnicodeEncodeError:
        b = text.encode("utf-8")

    out = "/"
    for byte in b:
        if 33 <= byte <= 126 and byte != 35:
            out += chr(byte)
        else:
            out += f"#{byte:02x}"
    return pikepdf.Name(out)


def _normalize_state_text(value: str | None) -> str:
    """
    Radio-State-Namen robust normalisieren.
    Behandelt u.a. Mojibake-Varianten aus externen Quellen.
    """
    text = (value or "").strip()
    if not text:
        return ""
    text = _decode_pdf_name_text(text)

    replacements = {
        "Ã¤": "ä",
        "Ã¶": "ö",
        "Ã¼": "ü",
        "ÃŸ": "ß",
        "鋍": "ä",
        "鋘": "ä",
        "鰐": "ö",
        "黨": "ü",
        "鰃": "ö",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    return " ".join(text.split()).casefold()


def _decode_pdf_name_text(value: str) -> str:
    """
    Dekodiert #xx-escapte PDF-Name-Texte nach Unicode (UTF-8, Fallback Latin-1).
    Beispiel: 'Einschr#c3#a4nkungen' -> 'Einschränkungen'
    """
    if "#" not in value:
        return value

    raw_bytes = bytearray()
    i = 0
    while i < len(value):
        if value[i] == "#" and i + 2 < len(value):
            part = value[i + 1:i + 3]
            if re.fullmatch(r"[0-9a-fA-F]{2}", part):
                raw_bytes.append(int(part, 16))
                i += 3
                continue
        ch = value[i]
        if ord(ch) <= 0xFF:
            raw_bytes.append(ord(ch))
        else:
            raw_bytes.extend(ch.encode("utf-8", errors="ignore"))
        i += 1

    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1", errors="ignore")


def _canonical_state_token(normalized_text: str) -> str:
    """
    Semantischer Token fuer robuste Radio-State-Matches bei Encoding-Schaeden.
    """
    if not normalized_text:
        return ""

    compact = "".join(ch for ch in normalized_text if ch.isalnum() or ch.isspace())
    compact = " ".join(compact.split())

    if "keine angabe" in compact:
        return "keine_angabe"
    if "personelle" in compact and "hilfe" in compact:
        return "personelle_hilfe"
    if "nicht" in compact and "durchf" in compact:
        return "nicht_durchfuehrbar"
    if "einschr" in compact:
        return "einschraenkungen"
    if "keine" in compact and ("beeintr" in compact or "beein" in compact):
        return "keine_beeintraechtigungen"

    return compact


def _section5_states_for_group(field_name: str | None) -> list[str] | None:
    """Soll-State-Reihenfolge fuer AW_4..AW_12 (#0..#4)."""
    if not field_name or not field_name.startswith("AW_"):
        return None
    try:
        n = int(field_name.split("_", 1)[1])
    except Exception:
        return None

    if n < 4 or n > 12:
        return None

    first = "Keine Beeinträchtigungen" if n == 4 else "keine Beeinträchtigungen"
    return [
        first,
        "Einschränkungen",
        "Personelle Hilfe nötig",
        "nicht durchführbar",
        "Keine Angabe möglich",
    ]


def _known_radio_states_for_group(field_name: str | None) -> list[str] | None:
    """Bekannte Radio-Gruppen mit definierter Reihenfolge der Optionen."""
    section5 = _section5_states_for_group(field_name)
    if section5:
        return section5

    mapping: dict[str, list[str]] = {
        "AW_1": [
            "Leistungen zur medizinischen Rehabilitation",
            "Leistungen zur onkologischen Rehabilitation",
            "Leistungen zur Teilhabe am Arbeitsleben (LTA)",
            "Erwerbsminderungsrente",
            "Sonstiges",
        ],
        "AW_2": ["wöchentlich", "14-tägig", "monatlich", "seltener"],
        "AW_3": ["nein", "ja"],
        "AW_14": ["Übergewicht", "Untergewicht"],
        "AW_20": ["nein", "ja"],
        "AW_21": ["nein", "ja"],
        "AW_22": ["Besserung", "Verschlechterung"],
        "AW_23": ["nein", "ja"],
        "AW_24": ["nein", "ja"],
        "AW_25": ["nein", "ja", "kann ich nicht beurteilen"],
        "AW_26": ["nein", "ja"],
    }
    return mapping.get(field_name or "")


def _get_first_on_state_key(annot: pikepdf.Dictionary):
    """Ermittelt den vorhandenen On-State-Key direkt aus /AP /N (ohne Text-Dekodierung)."""
    _normalize_widget_ap_names(annot)
    ap = annot.get("/AP")
    if ap is None:
        return None
    normal = ap.get("/N")
    if normal is None or not isinstance(normal, pikepdf.Dictionary):
        return None
    try:
        keys = list(normal.keys())
    except Exception:
        return None
    if not keys:
        return None

    for key_obj in keys:
        name = _decode_pdf_name_key(key_obj)
        if name and name != "Off":
            return key_obj
    return None


def _find_on_state_key_for_text(annot: pikepdf.Dictionary, state_text: str):
    """Findet den passenden On-State-Key eines Widgets anhand des Soll-Texts."""
    _normalize_widget_ap_names(annot)
    ap = annot.get("/AP")
    if ap is None:
        return None
    normal = ap.get("/N")
    if normal is None or not isinstance(normal, pikepdf.Dictionary):
        return None

    wanted_token = _canonical_state_token(_normalize_state_text(state_text))
    if not wanted_token:
        return None

    try:
        items = list(normal.items())
    except Exception:
        return None

    for key_obj, _ in items:
        name = _decode_pdf_name_key(key_obj)
        if not name or name == "Off":
            continue
        token = _canonical_state_token(_normalize_state_text(name))
        if token == wanted_token:
            return key_obj
    return None


def _repair_section5_radio_appearances(pdf: pikepdf.Pdf) -> None:
    """
    Sicherheitsnetz fuer bekannte Radio-Gruppen:
    /AS und /V werden auf tatsaechlich vorhandene /AP-/N-Keys gesetzt.
    """
    acroform = pdf.Root.get("/AcroForm")
    if not acroform or "/Fields" not in acroform:
        return

    repaired = 0
    for field_ref in acroform["/Fields"]:
        field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref
        if not isinstance(field_obj, pikepdf.Dictionary):
            continue

        t = field_obj.get("/T")
        if t is None:
            continue
        try:
            field_name = str(t)
        except Exception:
            continue

        known_states = _known_radio_states_for_group(field_name)
        if not known_states:
            continue

        selected_raw = field_obj.get("/V")
        selected_token = _canonical_state_token(_normalize_state_text(str(selected_raw).lstrip("/"))) if selected_raw else ""
        if not selected_token:
            continue

        selected_key = None
        expected_states = known_states
        expected_index = None
        for idx, state in enumerate(expected_states):
            if _canonical_state_token(_normalize_state_text(state)) == selected_token:
                expected_index = idx
                break

        kids = field_obj.get("/Kids") or []
        for kid_ref in kids:
            kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
            if not isinstance(kid, pikepdf.Dictionary):
                continue

            _normalize_widget_ap_names(kid)
            ap = kid.get("/AP")
            normal = ap.get("/N") if ap is not None else None

            match_key = None
            if isinstance(normal, pikepdf.Dictionary):
                try:
                    items = list(normal.items())
                except Exception:
                    items = []
                for key_obj, _ in items:
                    state_name = _decode_pdf_name_key(key_obj)
                    if not state_name or state_name == "Off":
                        continue
                    state_token = _canonical_state_token(_normalize_state_text(state_name))
                    if state_token == selected_token:
                        match_key = key_obj
                        break

            if match_key is not None and selected_key is None:
                kid[pikepdf.Name("/AS")] = match_key
                selected_key = match_key
            else:
                kid[pikepdf.Name("/AS")] = pikepdf.Name("/Off")

        # Harte Fallback-Strategie: Falls Text-Matching nicht greift, nutze stabile
        # Reihenfolge der AW-Widgets (#0..#4) und setze den ersten vorhandenen On-Key.
        if selected_key is None and expected_index is not None and 0 <= expected_index < len(kids):
            for idx, kid_ref in enumerate(kids):
                kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
                if not isinstance(kid, pikepdf.Dictionary):
                    continue
                if idx == expected_index:
                    _normalize_widget_ap_names(kid)
                    key_obj = _get_first_on_state_key(kid)
                    if key_obj is not None:
                        kid[pikepdf.Name("/AS")] = key_obj
                        selected_key = key_obj
                    else:
                        kid[pikepdf.Name("/AS")] = pikepdf.Name("/Off")
                else:
                    kid[pikepdf.Name("/AS")] = pikepdf.Name("/Off")

        if selected_key is not None:
            field_obj[pikepdf.Name("/V")] = selected_key
            repaired += 1

    if repaired:
        logger.info(f"Radio-Reparatur: {repaired} Gruppen auf valide AP-Keys gesetzt")


def _burn_in_section5_marks(pdf: pikepdf.Pdf) -> None:
    """
    Zeichnet fuer AW_4..AW_12 zusaetzlich ein sichtbares X direkt in den Seiteninhalt.
    Damit bleiben Markierungen sichtbar, auch wenn ein Viewer Widget-Appearances ignoriert.
    """
    acroform = pdf.Root.get("/AcroForm")
    if not acroform or "/Fields" not in acroform:
        return

    marked = 0
    for field_ref in acroform["/Fields"]:
        field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref
        if not isinstance(field_obj, pikepdf.Dictionary):
            continue

        t = field_obj.get("/T")
        if t is None:
            continue
        try:
            field_name = str(t)
        except Exception:
            continue

        if not _section5_states_for_group(field_name):
            continue

        selected_kid = None
        for kid_ref in field_obj.get("/Kids") or []:
            kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
            if not isinstance(kid, pikepdf.Dictionary):
                continue
            asv = kid.get("/AS")
            if asv is not None and str(asv) != "/Off":
                selected_kid = kid
                break

        # Falls /AS in der Datei nicht stabil ist, nutze /V + bekannte AW-Reihenfolge.
        if selected_kid is None:
            selected_raw = field_obj.get("/V")
            selected_token = _canonical_state_token(_normalize_state_text(str(selected_raw).lstrip("/"))) if selected_raw else ""
            expected_states = _section5_states_for_group(field_name) or []
            expected_index = None
            for idx, state in enumerate(expected_states):
                if _canonical_state_token(_normalize_state_text(state)) == selected_token:
                    expected_index = idx
                    break
            kids = field_obj.get("/Kids") or []
            if expected_index is not None and 0 <= expected_index < len(kids):
                kid = kids[expected_index]
                selected_kid = kid.resolve() if hasattr(kid, "resolve") else kid

        if selected_kid is None:
            continue
        if _draw_x_on_widget(pdf, selected_kid):
            marked += 1

    if marked:
        logger.info(f"Sektion-5-BurnIn: {marked} sichtbare Markierungen gezeichnet")


def _draw_x_on_widget(pdf: pikepdf.Pdf, kid: pikepdf.Dictionary) -> bool:
    """Zeichnet ein X in das Widget-Rechteck auf der zugehoerigen Seite."""
    rect = kid.get("/Rect")
    page = kid.get("/P")
    if rect is None or page is None:
        return False

    try:
        x0, y0, x1, y1 = [float(v) for v in rect]
    except Exception:
        return False

    left = min(x0, x1) + 1.0
    right = max(x0, x1) - 1.0
    bottom = min(y0, y1) + 1.0
    top = max(y0, y1) - 1.0
    if right <= left or top <= bottom:
        return False

    content = (
        "q\n"
        "0 0 0 RG\n"
        "1.1 w\n"
        f"{left:.3f} {bottom:.3f} m {right:.3f} {top:.3f} l S\n"
        f"{left:.3f} {top:.3f} m {right:.3f} {bottom:.3f} l S\n"
        "Q\n"
    ).encode("ascii")

    page_obj = page.resolve() if hasattr(page, "resolve") else page
    if not isinstance(page_obj, pikepdf.Dictionary):
        return False

    stream = pdf.make_stream(content)
    contents = page_obj.get("/Contents")
    if contents is None:
        page_obj[pikepdf.Name("/Contents")] = stream
        return True

    if isinstance(contents, pikepdf.Array):
        contents.append(stream)
        return True

    page_obj[pikepdf.Name("/Contents")] = pikepdf.Array([contents, stream])
    return True


def _burn_in_problematic_button_marks(pdf: pikepdf.Pdf) -> None:
    """
    Zeichnet zusaetzliche sichtbare X-Markierungen fuer bekannte problematische
    Radio-/Checkbox-Gruppen ausserhalb von Abschnitt 5.
    """
    acroform = pdf.Root.get("/AcroForm")
    if not acroform or "/Fields" not in acroform:
        return

    target_radio_groups = {
        "AW_1", "AW_2", "AW_3", "AW_14", "AW_20", "AW_21", "AW_23", "AW_24", "AW_25", "AW_26"
    }
    target_checkboxes = {"AW_13", "AW_15", "AW_16", "AW_17", "AW_18", "AW_19", "AW_24_1"}

    marked = 0
    for field_ref in acroform["/Fields"]:
        field_obj = field_ref.resolve() if hasattr(field_ref, "resolve") else field_ref
        if not isinstance(field_obj, pikepdf.Dictionary):
            continue

        t = field_obj.get("/T")
        if t is None:
            continue
        try:
            field_name = str(t)
        except Exception:
            continue

        # Abschnitt 5 bleibt bei der spezialisierten Routine.
        if _section5_states_for_group(field_name):
            continue

        kids = field_obj.get("/Kids") or []
        selected_widget = None

        if field_name in target_radio_groups and kids:
            # 1) Direkter Versuch über /AS
            for kid_ref in kids:
                kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
                if not isinstance(kid, pikepdf.Dictionary):
                    continue
                asv = kid.get("/AS")
                if asv is not None and str(asv) != "/Off":
                    selected_widget = kid
                    break

            # 2) Fallback über /V + bekannte Reihenfolge
            if selected_widget is None:
                selected_raw = field_obj.get("/V")
                selected_token = _canonical_state_token(_normalize_state_text(str(selected_raw).lstrip("/"))) if selected_raw else ""
                known_states = _known_radio_states_for_group(field_name) or []
                expected_index = None
                for idx, state in enumerate(known_states):
                    if _canonical_state_token(_normalize_state_text(state)) == selected_token:
                        expected_index = idx
                        break
                if expected_index is not None and 0 <= expected_index < len(kids):
                    kid_ref = kids[expected_index]
                    selected_widget = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref

        elif field_name in target_checkboxes:
            # Checkbox kann direkt im Feld oder in einem einzelnen Kid liegen.
            asv = field_obj.get("/AS")
            if asv is not None and str(asv) != "/Off":
                selected_widget = field_obj
            elif kids:
                for kid_ref in kids:
                    kid = kid_ref.resolve() if hasattr(kid_ref, "resolve") else kid_ref
                    if not isinstance(kid, pikepdf.Dictionary):
                        continue
                    asv = kid.get("/AS")
                    if asv is not None and str(asv) != "/Off":
                        selected_widget = kid
                        break

        if selected_widget is not None and _draw_x_on_widget(pdf, selected_widget):
            marked += 1

    if marked:
        logger.info(f"Button-BurnIn: {marked} Markierungen für problematische Gruppen gezeichnet")
