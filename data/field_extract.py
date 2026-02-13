#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extract AcroForm fields (internal names /T) from a PDF, including:
- field name (/T)
- field type (/FT)
- tooltip (/TU)
- page number(s)
- widget rect(s) (/Rect)
- button appearance states (/AP /N keys) for checkboxes/radios
Outputs CSV to stdout.
"""

import sys
import csv

try:
    import pikepdf
except ImportError:
    print("Missing dependency: pikepdf\nInstall via: pip install pikepdf", file=sys.stderr)
    sys.exit(1)


PDF_PATH = "S0051.pdf"   # adjust path as needed


def to_str(x):
    """Convert pikepdf objects safely to readable strings."""
    if x is None:
        return ""
    try:
        # pikepdf String objects can be converted directly
        return str(x)
    except Exception:
        try:
            return x.decode("utf-8", errors="replace")
        except Exception:
            return repr(x)


def normalize_ft(ft):
    # /Tx, /Btn, /Ch, /Sig are typical
    if not ft:
        return ""
    s = to_str(ft)
    return s.replace("/", "")


def collect_button_states(annot):
    """
    For buttons (checkbox/radio), try to get possible appearance states from /AP /N.
    Returns a '|' separated string.
    """
    try:
        ap = annot.get("/AP", None)
        if not ap:
            return ""
        n = ap.get("/N", None)
        if not n:
            return ""
        # /N can be a dict of appearance streams keyed by state name
        if isinstance(n, pikepdf.Dictionary):
            keys = []
            for k in n.keys():
                ks = to_str(k)
                # Key names are like '/Yes', '/Off' etc.
                keys.append(ks.lstrip("/"))
            # keep stable order: Off first if present, then the rest sorted
            keys_sorted = []
            if "Off" in keys:
                keys_sorted.append("Off")
            keys_sorted.extend(sorted([x for x in keys if x != "Off"]))
            return "|".join(keys_sorted)
        return ""
    except Exception:
        return ""


def extract_fields(pdf_path):
    pdf = pikepdf.open(pdf_path)
    results = []

    # Build a mapping from indirect object (field) to its core props
    # AcroForm Fields tree is on /Root /AcroForm /Fields
    acroform = pdf.Root.get("/AcroForm", None)
    fields = []
    if acroform and "/Fields" in acroform:
        fields = list(acroform["/Fields"])

    # Helper: walk field tree (kids)
    def walk_field(field, parent_T=None, parent_TU=None, parent_FT=None):
        # Field dictionaries can inherit /T /TU /FT from parents
        T = field.get("/T", None)
        TU = field.get("/TU", None)
        FT = field.get("/FT", None)

        eff_T  = T  if T  is not None else parent_T
        eff_TU = TU if TU is not None else parent_TU
        eff_FT = FT if FT is not None else parent_FT

        # If it has Kids, recurse; Widgets may live in Kids or be the field itself
        kids = field.get("/Kids", None)
        if kids:
            for kid in kids:
                walk_field(kid, eff_T, eff_TU, eff_FT)
        else:
            # leaf field (or single widget)
            results.append({
                "field_obj": field,
                "T": to_str(eff_T),
                "TU": to_str(eff_TU),
                "FT": normalize_ft(eff_FT),
            })

    for f in fields:
        walk_field(f)

    # Now map widgets to pages by scanning page annotations and matching by object id
    # We'll create a dict: widget_obj_id -> (page_index, rect, ap_states)
    widget_map = {}

    for page_index, page in enumerate(pdf.pages, start=1):
        annots = page.get("/Annots", None)
        if not annots:
            continue
        for a in annots:
            try:
                annot = a.get_object()
            except Exception:
                annot = a
            if not isinstance(annot, pikepdf.Dictionary):
                continue

            # Only widget annotations are interesting for form fields
            subtype = annot.get("/Subtype", None)
            if to_str(subtype) != "/Widget":
                continue

            rect = annot.get("/Rect", None)
            rect_str = ""
            if rect and hasattr(rect, "__iter__"):
                rect_str = ",".join([to_str(v) for v in rect])

            ap_states = collect_button_states(annot)

            # Key by object id (indirect reference)
            # pikepdf doesn't expose an easy stable "object number" for dicts,
            # but we can use the underlying reference if available.
            ref = getattr(a, "objgen", None)
            # If it's indirect, a.objgen exists, else None
            if ref:
                widget_key = f"{ref[0]} {ref[1]}"
            else:
                widget_key = None

            widget_map.setdefault(widget_key, []).append({
                "page": page_index,
                "rect": rect_str,
                "states": ap_states,
            })

    # Produce final rows:
    # For each leaf field, find its widget(s) by reading /Kids or itself if it’s a widget.
    rows = []

    for item in results:
        field = item["field_obj"]
        name = item["T"]
        ft = item["FT"]
        tu = item["TU"]

        # Determine widgets: either the field itself is a widget (has /Subtype /Widget),
        # or it has /Kids which are widgets (but that would have been "kids"; leaf means none).
        # In practice, leaf field dict often *is* the widget.
        widgets = [field]

        page_set = set()
        rects = []
        states_set = set()

        # Attempt to resolve each widget’s indirect ref so we can match against page annots
        for w in widgets:
            # find its indirect ref if possible by looking for it among all annots.
            # simplest: scan widget_map for entries whose dict equals w is hard.
            # better: use w.objgen if it exists (pikepdf gives it for indirect objects).
            objgen = getattr(w, "objgen", None)
            widget_key = f"{objgen[0]} {objgen[1]}" if objgen else None

            if widget_key in widget_map:
                for hit in widget_map[widget_key]:
                    page_set.add(hit["page"])
                    if hit["rect"]:
                        rects.append(f"p{hit['page']}[{hit['rect']}]")
                    if hit["states"]:
                        states_set.add(hit["states"])
            else:
                # fallback: no page match found
                pass

        pages_str = ",".join(map(str, sorted(page_set))) if page_set else ""
        rects_str = " | ".join(rects)

        # Merge states: if multiple widgets, keep unique
        # Some PDFs repeat identical "Off|Yes" strings; we de-dupe.
        states_str = ""
        if states_set:
            # Flatten if multiple combined strings
            uniq = sorted(states_set)
            states_str = " || ".join(uniq)

        rows.append({
            "field_name": name,
            "type": ft,
            "pages": pages_str,
            "tooltip": tu,
            "rects": rects_str,
            "states": states_str,
        })

    return rows


def main():
    rows = extract_fields(PDF_PATH)

    # Stable order: by pages then field_name
    def sort_key(r):
        # pages like "1,2" -> first page int; empty -> 9999
        if r["pages"]:
            try:
                first = int(r["pages"].split(",")[0])
            except Exception:
                first = 9999
        else:
            first = 9999
        return (first, r["field_name"])

    rows.sort(key=sort_key)

    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=["field_name", "type", "pages", "tooltip", "rects", "states"],
        delimiter=";",
        quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(r)


if __name__ == "__main__":
    main()