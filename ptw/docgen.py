"""Filling the Word template and saving permits."""
import datetime as dt
import os
import re

import docx
from docx.oxml.ns import qn

from . import fontmetrics, generator, storage

PLACEHOLDER = re.compile(r"\{\{\s*([A-Z_]+)\s*\}\}")
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _paragraphs(document):
    parts = [document.element.body]
    for s in document.sections:
        for hf in (s.header, s.footer, s.first_page_header, s.first_page_footer,
                   s.even_page_header, s.even_page_footer):
            if not hf.is_linked_to_previous:
                parts.append(hf._element)
    for part in parts:
        yield from list(part.iter(qn("w:p")))


def _replace_in_paragraph(p, values):
    """Replace {{KEY}} even when Word split it over several runs.

    Returns the keys found and the w:t elements that received a value."""
    ts = list(p.iter(qn("w:t")))
    full = "".join(t.text or "" for t in ts)
    if "{{" not in full:
        return [], []
    # character offset where each w:t starts
    starts, pos = [], 0
    for t in ts:
        starts.append(pos)
        pos += len(t.text or "")
    keys, filled = [], []
    for m in reversed(list(PLACEHOLDER.finditer(full))):
        key = m.group(1)
        if key not in values:
            continue
        keys.append(key)
        a, b = m.span()
        first = True
        for t, s in zip(ts, starts):
            text = t.text or ""
            e = s + len(text)
            if e <= a or s >= b:
                continue
            lo, hi = max(a, s) - s, min(b, e) - s
            t.text = text[:lo] + (str(values[key]) if first else "") + text[hi:]
            t.set(_XML_SPACE, "preserve")
            if first:
                filled.append(t)
            first = False
    return keys, filled


# ---------- keeping every value on one line (the form must fit one page) ----------

DEFAULT_CELL_MARGIN = 108  # dxa (twentieths of a point), Word default left/right
# leave a little room: Word and LibreOffice lay out text slightly differently
SAFETY_RATIO, SAFETY_PT = 0.99, 3.0


def _run_size(r):
    rpr = r.find(qn("w:rPr"))
    sz = rpr.find(qn("w:sz")) if rpr is not None else None
    return int(sz.get(qn("w:val"))) / 2 if sz is not None else 9.0


def _run_bold(r):
    rpr = r.find(qn("w:rPr"))
    b = rpr.find(qn("w:b")) if rpr is not None else None
    return b is not None and b.get(qn("w:val"), "true") not in ("0", "false")


def _set_run_size(r, size):
    rpr = r.find(qn("w:rPr"))
    if rpr is None:
        rpr = r.makeelement(qn("w:rPr"), {})
        r.insert(0, rpr)
    half = str(int(round(size * 2)))
    for tag in ("w:sz", "w:szCs"):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set(qn("w:val"), half)


def _available_width(p):
    """Width in points a paragraph inside a table cell can use, or None."""
    tc = p.getparent()
    while tc is not None and tc.tag != qn("w:tc"):
        tc = tc.getparent()
    if tc is None:
        return None
    tcpr = tc.find(qn("w:tcPr"))
    w = tcpr.find(qn("w:tcW")) if tcpr is not None else None
    if w is None or w.get(qn("w:type")) not in ("dxa", None):
        return None
    width = int(w.get(qn("w:w"))) - 2 * DEFAULT_CELL_MARGIN
    ppr = p.find(qn("w:pPr"))
    ind = ppr.find(qn("w:ind")) if ppr is not None else None
    if ind is not None:
        for side in ("left", "start", "right", "end", "firstLine"):
            v = ind.get(qn("w:" + side))
            if v:
                width -= int(v)
    return width / 20 * SAFETY_RATIO - SAFETY_PT


def _value_runs(p, filled):
    """Runs holding inserted values, in document order."""
    wanted = {t.getparent() for t in filled}
    return [r for r in p.iter(qn("w:r")) if r in wanted]


def _cut(runs, room, size):
    """Shorten the text of runs so that it is at most `room` points wide."""
    ell = fontmetrics.text_width("\u2026", size)
    used, cutting = 0.0, False
    for r in runs:
        for t in r.findall(qn("w:t")):
            text = t.text or ""
            if cutting:
                t.text = ""
                continue
            keep = ""
            for ch in text:
                w = fontmetrics.text_width(ch, size, _run_bold(r))
                if used + w > room - ell:
                    cutting = True
                    break
                keep += ch
                used += w
            if cutting:
                t.text = keep.rstrip(" ,") + "\u2026"
            else:
                t.text = keep


def fit_paragraph(p, filled, min_size):
    """Keep the paragraph on one line: shrink the inserted values, cut them as a last resort.

    Returns "ok", "shrunk" or "cut"."""
    avail = _available_width(p)
    if avail is None or not filled:
        return "ok"
    runs = list(p.iter(qn("w:r")))
    if any(r.find(qn("w:tab")) is not None for r in runs):
        return "ok"  # tab stops: cannot measure reliably
    vruns = _value_runs(p, filled)
    fixed = value = 0.0
    for r in runs:
        text = "".join(t.text or "" for t in r.findall(qn("w:t")))
        w = fontmetrics.text_width(text, _run_size(r), _run_bold(r))
        if r in vruns:
            value += w
        else:
            fixed += w
    if fixed + value <= avail or value == 0:
        return "ok"
    scale = (avail - fixed) / value
    status = "shrunk"
    sizes = []
    for r in vruns:
        size = int(_run_size(r) * scale * 2) / 2  # Word uses half points
        if size < min_size:
            size, status = min_size, "cut"
        sizes.append(size)
        _set_run_size(r, size)
    if status == "cut":
        _cut(vruns, avail - fixed, min(sizes))
    return status


def fill_template(template, values, out_path, fit=True, min_size=6.5):
    """Fill the template; returns the keys whose text had to be cut to fit one line."""
    d = docx.Document(template)
    too_long = []
    for p in _paragraphs(d):
        keys, filled = _replace_in_paragraph(p, values)
        if fit and filled and fit_paragraph(p, filled, min_size) == "cut":
            too_long += keys
    d.save(out_path)
    return too_long


_limits_cache = {}


def field_limits(template):
    """{KEY: (free width in pt, font size)} for placeholders that sit in table cells."""
    try:
        stamp = (template, os.path.getmtime(template))
    except OSError:
        return {}
    if stamp in _limits_cache:
        return _limits_cache[stamp]
    limits = {}
    d = docx.Document(template)
    for p in _paragraphs(d):
        avail = _available_width(p)
        if avail is None:
            continue
        fixed, size, keys = 0.0, 9.0, []
        for r in p.iter(qn("w:r")):
            text = "".join(t.text or "" for t in r.findall(qn("w:t")))
            found = PLACEHOLDER.findall(text)
            if found:
                keys += found
                size = _run_size(r)
            fixed += fontmetrics.text_width(PLACEHOLDER.sub("", text), _run_size(r), _run_bold(r))
        if len(keys) == 1:
            limits.setdefault(keys[0], (avail - fixed, size))
    _limits_cache[stamp] = limits
    return limits


def check_fit(template, key, text, min_size=6.5):
    """None if text fits at normal size, else (size it will be printed at, fits at all)."""
    lim = field_limits(template).get(key)
    if not lim or not text:
        return None
    free, size = lim
    width = fontmetrics.text_width(text, size)
    if width <= free:
        return None
    new = int(size * free / width * 2) / 2
    return max(new, min_size), new >= min_size


def values_for(store, permit):
    s = store.settings
    day = generator.parse_date(permit["date"])
    job = store.job(permit["job_id"]) or {}
    no = permit.get("permit_no")
    return {
        "SHIP": s.get("ship_name", ""),
        "DATE": day.strftime("%d/%m/%Y"),
        "YEAR": day.strftime("%Y"),
        "PERMIT_NO": str(no) if no else " " * 14,
        "TIME_ISSUE": s["time_issue"],
        "TIME_TRANSFER": s["time_transfer"] if permit.get("transfer") else "",
        "TRANSFER_DATE": day.strftime("%d/%m/%Y") if permit.get("transfer") else "",
        "TIME_CLOSE": s["time_close"],
        "LOCATION": job.get("location", ""),
        "PLANT": job.get("plant", ""),
        "WORK": job.get("work", ""),
        "RA_NO": job.get("ra_no", ""),
        "ISSUED_TO": generator.issued_to_text(store, permit["crew"]),
        "AO": generator.sign_text(store, s.get("ao_id")),
        "PC": generator.sign_text(store, permit.get("pc")),
        "TRANSFER_TO": generator.sign_text(store, permit.get("transfer")),
        "PC_CLOSE": generator.sign_text(store, permit.get("close")),
    }


_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def file_name(store, permit):
    s = store.settings
    job = store.job(permit["job_id"]) or {"title": permit["job_id"]}
    day = generator.parse_date(permit["date"])
    name = s.get("filename_pattern") or "{date} {title}"
    name = name.format(date=day.strftime(s.get("filename_date_format") or "%Y-%m-%d"),
                       title=job["title"], ra=job.get("ra_no", ""),
                       no=permit.get("permit_no") or "")
    name = _BAD.sub("_", name).strip(" .") or "permit"
    return name + ".docx"


def unique_path(folder, name):
    path = os.path.join(folder, name)
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(path):
        path = f"{base} ({n}){ext}"
        n += 1
    return path


def write_permits(store, permits, replace_dates=False):
    """Create .docx files, number them and record history.

    Returns (paths, warnings); warnings name permits with text that may wrap."""
    s = store.settings
    folder = s.get("output_dir")
    if not folder:
        raise ValueError("Output folder is not set (Settings).")
    template = storage.template_path(s)
    if not os.path.exists(template):
        raise FileNotFoundError(f"Template not found: {template}")
    os.makedirs(folder, exist_ok=True)

    if replace_dates:
        dates = {p["date"] for p in permits}
        store.history = [h for h in store.history if h["date"] not in dates]

    paths, warnings = [], []
    for p in permits:
        if s.get("auto_number") and not p.get("permit_no"):
            p["permit_no"] = s["next_permit_no"]
            s["next_permit_no"] = int(s["next_permit_no"]) + 1
        path = unique_path(folder, file_name(store, p))
        min_size = float(s.get("min_font_size", 6.5))
        values = values_for(store, p)
        res = check_fit(template, "ISSUED_TO", values["ISSUED_TO"], min_size)
        if res and not res[1]:  # a big team: "2E DMITRII" instead of "2ND ENG DMITRII"
            values["ISSUED_TO"] = generator.issued_to_text(store, p["crew"], compact=True)
        too_long = fill_template(template, values, path,
                                 fit=s.get("fit_one_line", True), min_size=min_size)
        paths.append(path)
        if too_long:
            warnings.append((os.path.basename(path), sorted(set(too_long))))
        store.history.append({**p, "file": os.path.basename(path),
                              "created": dt.datetime.now().isoformat(timespec="seconds")})
    store.history.sort(key=lambda h: h["date"])
    storage.save("history", store.history)
    storage.save("settings", store.settings)
    return paths, warnings
