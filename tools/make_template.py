"""Convert a filled-in Daily Permit to Work .docx into a template with {{PLACEHOLDERS}}.

Usage:
    python tools/make_template.py "Daily permit to work.docx" templates/ptw_template.docx

The script looks for the sample values of the original MSC form (dates, times,
names) and replaces them with placeholders that ptw.docgen fills in later.
Only run texts are changed, so all formatting of the form is kept.
"""
import copy
import sys

import docx
from docx.oxml.ns import qn

# exact run text -> placeholder
RUN_REPLACEMENTS = {
    "13/07/2026": "{{DATE}}",
    "08:00": "{{TIME_ISSUE}}",
    "12:00": "{{TIME_TRANSFER}}",
    "20:00": "{{TIME_CLOSE}}",
    "Chief Engineer / Vadim Medvedev": "{{AO}}",
    "Fourth Engineer/Parth Kausal": "{{PC}}",
    "Third Engineer/ Arun Singh": "{{TRANSFER_TO}}",
    "Second Engineer/ Gleb Strizhkov": "{{PC_CLOSE}}",
}


def paragraphs(document):
    """All unique w:p elements of body, headers and footers."""
    parts = [document.element.body]
    for s in document.sections:
        parts += [s.header._element, s.footer._element]
    for part in parts:
        yield from part.iter(qn("w:p"))


def runs(p):
    return [r for r in p.iter(qn("w:r")) if r.find(qn("w:t")) is not None]


def text_of(r):
    return "".join(t.text or "" for t in r.findall(qn("w:t")))


def set_text(r, value):
    ts = r.findall(qn("w:t"))
    ts[0].text = value
    ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in ts[1:]:
        r.remove(t)


def p_text(p):
    return "".join(text_of(r) for r in runs(p))


def fill_paragraph(p, value):
    """Put value into the first run and blank all other runs."""
    rs = runs(p)
    set_text(rs[0], value)
    for r in rs[1:]:
        set_text(r, "")


def main(src, dst):
    d = docx.Document(src)
    ps = list(paragraphs(d))

    for p in ps:
        for r in runs(p):
            t = text_of(r)
            if t in RUN_REPLACEMENTS:
                set_text(r, RUN_REPLACEMENTS[t])

    # section 6 gets its own date so it stays empty when nobody takes over
    for p in ps:
        if "{{TIME_TRANSFER}}" in p_text(p):
            for r in runs(p):
                if text_of(r) == "{{DATE}}":
                    set_text(r, "{{TRANSFER_DATE}}")

    sample_run = None
    for i, p in enumerate(ps):
        t = p_text(p)
        rs = runs(p)
        if t.startswith("Consecutive Permit"):
            # ['Consecutive Permit ', 'No: ', 'E-   ', '              ', '/2026']
            set_text(rs[-2], "{{PERMIT_NO}}")
            set_text(rs[-1], "/{{YEAR}}")
        elif t.strip() == "Engine Room,":
            fill_paragraph(p, "{{LOCATION}}")
            sample_run = rs[0]
        elif t.startswith("Risk assessment checked"):
            # the number gets its own run, so only it is shrunk when too long
            set_text(rs[-1], text_of(rs[-1]).rstrip() + " ")
            ra = copy.deepcopy(rs[-1])
            set_text(ra, "{{RA_NO}}")
            rs[-1].addnext(ra)

    # Scope of Work table: the value paragraph follows each label paragraph
    labels = {
        "Plant Apparatus / Identification": "{{PLANT}}",
        "Work to be done": "{{WORK}}",
        "Permit issued to": "{{ISSUED_TO}}",
    }
    for i, p in enumerate(ps):
        t = p_text(p)
        for label, ph in labels.items():
            if t.startswith(label):
                target = ps[i + 1]
                if runs(target):
                    fill_paragraph(target, ph)
                else:
                    r = copy.deepcopy(sample_run)
                    set_text(r, ph)
                    target.append(r)

    d.save(dst)
    leftovers = [p_text(p) for p in paragraphs(docx.Document(dst))
                 if "2026" in p_text(p) and "{{" not in p_text(p)]
    print("Template saved:", dst)
    if leftovers:
        print("Check these paragraphs manually:", leftovers)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
