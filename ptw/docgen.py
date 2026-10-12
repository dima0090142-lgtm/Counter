"""Filling the Word template and saving permits."""
import datetime as dt
import os
import re

import docx
from docx.oxml.ns import qn

from . import generator, storage

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
    """Replace {{KEY}} even when Word split it over several runs."""
    ts = list(p.iter(qn("w:t")))
    full = "".join(t.text or "" for t in ts)
    if "{{" not in full:
        return
    # character offset where each w:t starts
    starts, pos = [], 0
    for t in ts:
        starts.append(pos)
        pos += len(t.text or "")
    for m in reversed(list(PLACEHOLDER.finditer(full))):
        key = m.group(1)
        if key not in values:
            continue
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
            first = False


def fill_template(template, values, out_path):
    d = docx.Document(template)
    for p in _paragraphs(d):
        _replace_in_paragraph(p, values)
    d.save(out_path)


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
    """Create .docx files, number them and record history. Returns file paths."""
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

    paths = []
    for p in permits:
        if s.get("auto_number") and not p.get("permit_no"):
            p["permit_no"] = s["next_permit_no"]
            s["next_permit_no"] = int(s["next_permit_no"]) + 1
        path = unique_path(folder, file_name(store, p))
        fill_template(template, values_for(store, p), path)
        paths.append(path)
        store.history.append({**p, "file": os.path.basename(path),
                              "created": dt.datetime.now().isoformat(timespec="seconds")})
    store.history.sort(key=lambda h: h["date"])
    storage.save("history", store.history)
    storage.save("settings", store.settings)
    return paths
