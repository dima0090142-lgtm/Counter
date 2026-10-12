"""Check that every permit prints on ONE A4 page.

Needs LibreOffice (soffice) for the PDF conversion; pdftotext (poppler) is optional
and adds the check that each value stays on one line.

    python tools/check_print.py            # all jobs, worst-case crew
    python tools/check_print.py --keep out # keep the .docx/.pdf files in ./out

For every job the biggest possible team with the longest names is used, plus a few
stress permits with very long texts. Exit code 1 if any file has more than one page.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ptw import docgen, generator, storage  # noqa: E402

LONG = {
    "location": "Engine Room, M/E top platform, cylinder units No.1 to No.8, port and starboard side",
    "plant": "Main Engine fuel injection valves, fuel pumps, high pressure pipes and leakage alarm system",
    "work": "Removal, overhaul, pressure test and refitting of all fuel valves, renewal of nozzles, springs and O-rings",
    "ra_no": "RA-ENG-PTW-0123/2026",
}


def find_soffice():
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    for path in (r"C:\Program Files\LibreOffice\program\soffice.exe",
                 r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if os.path.exists(path):
            return path
    return None


def worst_crew(store, job):
    """Lead + the most helpers the job allows, longest names first."""
    def by_len(ranks, exclude=()):
        ms = [m for m in store.crew if m.get("active", True) and m["rank"] in ranks
              and m["id"] not in exclude]
        return sorted(ms, key=lambda m: -len(generator.issued_to_text(store, [m["id"]])))

    lead = by_len(job["lead_ranks"])[:1]
    team = [m["id"] for m in lead]
    team += [m["id"] for m in by_len(job.get("officer_ranks", []), team)[:job.get("officers", [0, 0])[1]]]
    team += [m["id"] for m in by_len(job.get("rating_ranks", []), team)[:job.get("ratings", [0, 0])[1]]]
    return team


def longest_officer(store):
    officers = [m["id"] for m in store.crew if store.rank(m["rank"]).get("officer")]
    return max(officers, key=lambda i: len(generator.sign_text(store, i)))


def build_permits(store):
    permits = []
    officer = longest_officer(store)
    for n, job in enumerate(store.jobs):
        crew = worst_crew(store, job)
        if not crew:
            continue
        permits.append({"date": "2026-12-28", "job_id": job["id"], "crew": crew,
                        "pc": crew[-1], "transfer": officer, "close": crew[0],
                        "permit_no": 9000 + n})
    # stress: very long texts and every crew member on one permit
    stress = dict(store.jobs[0], id="zz_stress_long_text", title="ZZ Stress long text", **LONG)
    store.jobs.append(stress)
    everybody = [m["id"] for m in store.crew if m["id"] != store.settings.get("ao_id")]
    permits.append({"date": "2026-12-29", "job_id": stress["id"], "crew": everybody,
                    "pc": officer, "transfer": officer, "close": officer, "permit_no": 99999})
    return permits


def pdf_pages(path):
    with open(path, "rb") as f:
        data = f.read()
    m = re.findall(rb"/Type\s*/Pages\b.*?/Count\s+(\d+)", data, re.S)
    if m:
        return max(int(x) for x in m)
    return len(re.findall(rb"/Type\s*/Page\b(?!s)", data))


def convert(soffice, files, outdir):
    profile = tempfile.mkdtemp(prefix="lo_profile_")
    try:
        for i in range(0, len(files), 40):
            subprocess.run([soffice, f"-env:UserInstallation=file:///{profile.replace(os.sep, '/')}",
                            "--headless", "--convert-to", "pdf", "--outdir", outdir, *files[i:i + 40]],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=900)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def one_line_problems(pdf, values, cut=()):
    """Values that pdftotext shows broken over two lines (cut values end with an ellipsis)."""
    tool = shutil.which("pdftotext")
    if not tool:
        return []
    text = subprocess.run([tool, "-layout", pdf, "-"], capture_output=True, text=True).stdout
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    bad = []
    for key, value in values.items():
        v = re.sub(r"\s+", " ", value).strip()
        if key in cut:
            ok = any(v[:12] in ln and "\u2026" in ln for ln in lines)
        else:
            ok = not v or any(v in ln for ln in lines)
        if not ok:
            bad.append(key)
    return bad


CHECK_KEYS = ("LOCATION", "PLANT", "WORK", "ISSUED_TO", "AO", "PC", "TRANSFER_TO", "PC_CLOSE")


def run(store, outdir, soffice):
    store.settings.update(output_dir=outdir, auto_number=False, fit_one_line=True)
    permits = build_permits(store)
    storage.save = lambda *a, **k: None  # never touch the real history / settings
    paths, warnings = docgen.write_permits(store, permits)
    convert(soffice, paths, outdir)
    cut_keys = dict(warnings)
    results = []
    for p, path in zip(permits, paths):
        pdf = os.path.splitext(path)[0] + ".pdf"
        pages = pdf_pages(pdf) if os.path.exists(pdf) else 0
        vals = docgen.values_for(store, p)
        cut = cut_keys.get(os.path.basename(path), [])
        res = docgen.check_fit(storage.template_path(store.settings), "ISSUED_TO",
                               vals["ISSUED_TO"], float(store.settings.get("min_font_size", 6.5)))
        if res and not res[1]:  # same rule as docgen.write_permits
            vals["ISSUED_TO"] = generator.issued_to_text(store, p["crew"], compact=True)
        broken = one_line_problems(pdf, {k: vals[k] for k in CHECK_KEYS}, cut) if pages else []
        results.append((os.path.basename(path), pages, broken))
    return results, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keep", help="folder to keep the generated files in")
    args = ap.parse_args()
    soffice = find_soffice()
    if not soffice:
        sys.exit("LibreOffice (soffice) not found - install it to run this check.")
    outdir = os.path.abspath(args.keep) if args.keep else tempfile.mkdtemp(prefix="ptw_print_")
    os.makedirs(outdir, exist_ok=True)
    store = storage.Store()
    store.history = []
    results, warnings = run(store, outdir, soffice)
    failed = [r for r in results if r[1] != 1 or r[2]]
    for name, pages, broken in results:
        mark = "OK " if pages == 1 and not broken else "BAD"
        extra = f"  wrapped: {', '.join(broken)}" if broken else ""
        print(f"{mark} {pages} page(s)  {name}{extra}")
    if warnings:
        print("\nText too long even in the smallest font, shortened with '...':")
        for name, keys in warnings:
            print(f"  {name}: {', '.join(keys)}")
    print(f"\n{len(results) - len(failed)} of {len(results)} permits print on one page, one line per value.")
    if not args.keep:
        shutil.rmtree(outdir, ignore_errors=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
