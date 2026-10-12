import datetime as dt
import os
import random

import docx
from docx.oxml.ns import qn
import pytest

from ptw import docgen, generator, storage


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path / "data"))
    st = storage.Store()
    st.history = []
    st.settings["output_dir"] = str(tmp_path / "out")
    return st


def make_plan(store, days=60, seed=1):
    start = dt.date(2026, 1, 1)
    return generator.Planner(store, random.Random(seed)).plan(start, start + dt.timedelta(days=days - 1))


def test_one_permit_per_day(store):
    plan = make_plan(store, 30)
    assert [p["date"] for p in plan] == [(dt.date(2026, 1, 1) + dt.timedelta(d)).isoformat()
                                        for d in range(30)]


def test_job_not_repeated_within_window(store):
    window = store.settings["no_repeat_days"]
    plan = make_plan(store, 90)
    last = {}
    for p in plan:
        d = dt.date.fromisoformat(p["date"])
        if p["job_id"] in last:
            assert (d - last[p["job_id"]]).days > window
        last[p["job_id"]] = d


def test_crew_matches_job_ranks_and_ce_not_used(store):
    for p in make_plan(store, 60):
        job = store.job(p["job_id"])
        ranks = [store.member(i)["rank"] for i in p["crew"]]
        assert ranks[0] in job["lead_ranks"]
        allowed = set(job["lead_ranks"]) | set(job["officer_ranks"]) | set(job["rating_ranks"])
        assert set(ranks) <= allowed
        assert "CE" not in ranks
        assert len(set(p["crew"])) == len(p["crew"])
        assert p["close"] == p["crew"][0]


def test_lead_rotates(store):
    plan = make_plan(store, 120)
    same = sum(a["crew"][0] == b["crew"][0] for a, b in zip(plan, plan[1:]))
    assert same < len(plan) * 0.15


def test_crew_spread(store):
    plan = make_plan(store, 120)
    count = {}
    for p in plan:
        for c in p["crew"]:
            count[c] = count.get(c, 0) + 1
    motormen = [count.get(m["id"], 0) for m in store.crew if m["rank"] == "MM"]
    assert min(motormen) > 0.6 * max(motormen)


def test_several_permits_per_day_use_different_people(store):
    store.settings["permits_per_day"] = 2
    plan = make_plan(store, 20)
    assert len(plan) == 40
    for d in {p["date"] for p in plan}:
        a, b = [p for p in plan if p["date"] == d]
        assert a["job_id"] != b["job_id"]


def test_history_influences_next_plan(store):
    first = make_plan(store, 5)
    store.history = first
    nxt = generator.Planner(store, random.Random(2)).plan(dt.date(2026, 1, 6), dt.date(2026, 1, 8))
    assert not {p["job_id"] for p in nxt} & {p["job_id"] for p in first[-3:]}


def test_reroll_keeps_date(store):
    plan = make_plan(store, 7)
    old = plan[3]
    generator.Planner(store, random.Random(5)).reroll(plan, 3)
    assert plan[3]["date"] == old["date"]
    assert plan[3]["job_id"] != old["job_id"]


def _all_text(path):
    """Text of every paragraph once (merged table cells are not repeated)."""
    body = docx.Document(path).element.body
    return "\n".join("".join(t.text or "" for t in p.iter(qn("w:t")))
                     for p in body.iter(qn("w:p")))


def test_write_permits_fills_template(store):
    store.settings["auto_number"] = True
    store.settings["next_permit_no"] = 41
    plan = [{"date": "2026-07-13", "job_id": "me_fuel_valves_overhaul",
             "crew": ["sukhoverkhii", "singh", "kaushal"],
             "pc": "kaushal", "transfer": "singh", "close": "sukhoverkhii"}]
    path = docgen.write_permits(store, plan)[0][0]
    assert path.endswith("2026-07-13 ME Fuel Valves Overhaul.docx")
    text = _all_text(path)
    assert "{{" not in text
    for s in ("13/07/2026", "E-   41/2026", "Main Engine fuel injection valves",
              "Risk Assessment number RA-001", "2ND ENG DMITRII, 3RD ENG ARUN, 4TH ENG PARTH",
              "Chief Engineer / Vadim Medvedev", "Fourth Engineer / Parth Kaushal",
              "Third Engineer / Arun Singh", "Asst. Second Engineer / Dmitrii Sukhoverkhii",
              "08:00", "12:00", "20:00"):
        assert s in text, s
    assert store.settings["next_permit_no"] == 42
    assert store.history[-1]["file"] == "2026-07-13 ME Fuel Valves Overhaul.docx"


def test_no_transfer_leaves_section_6_empty(store):
    plan = [{"date": "2026-07-14", "job_id": "fo_strainers_cleaning", "crew": ["pal", "padilla"],
             "pc": "pal", "transfer": "", "close": "pal"}]
    text = _all_text(docgen.write_permits(store, plan)[0][0])
    assert text.count("14/07/2026") == 3  # header, section 5, section 7
    assert "12:00" not in text


def test_same_name_gets_suffix(store):
    p = {"date": "2026-07-14", "job_id": "fo_strainers_cleaning", "crew": ["pal"],
         "pc": "pal", "transfer": "", "close": "pal"}
    a, b = docgen.write_permits(store, [dict(p), dict(p)])[0]
    assert a != b and b.endswith("(2).docx")


def test_file_name_is_safe(store):
    store.settings["filename_pattern"] = "{date} {title} / {ra}"
    name = docgen.file_name(store, {"date": "2026-07-14", "job_id": "fo_strainers_cleaning"})
    assert "/" not in name and name.endswith(".docx")


def _runs_with(path, needle):
    body = docx.Document(path).element.body
    for r in body.iter(qn("w:r")):
        text = "".join(t.text or "" for t in r.findall(qn("w:t")))
        if needle in text:
            sz = r.find(qn("w:rPr")).find(qn("w:sz"))
            yield text, int(sz.get(qn("w:val"))) / 2


def test_long_text_is_shrunk_to_one_line(store):
    job = store.job("me_fuel_valves_overhaul")
    job["work"] = ("Removal, overhaul, pressure test and refitting of all fuel valves, "
                   "renewal of nozzles, springs, O-rings and HP pipe gaskets on all units")
    p = {"date": "2026-07-14", "job_id": job["id"], "crew": ["sukhoverkhii"],
         "pc": "sukhoverkhii", "transfer": "", "close": "sukhoverkhii"}
    (path,), warnings = docgen.write_permits(store, [p])
    (text, size), = _runs_with(path, "Removal, overhaul")
    assert text == job["work"] and 6.5 <= size < 9
    assert not warnings
    (_, size), = _runs_with(path, "Main Engine fuel injection valves")
    assert size == 9  # short values keep the normal size


def test_too_long_text_is_cut_and_reported(store):
    job = store.job("me_fuel_valves_overhaul")
    job["work"] = "Very long description " * 20
    p = {"date": "2026-07-14", "job_id": job["id"], "crew": ["sukhoverkhii"],
         "pc": "sukhoverkhii", "transfer": "", "close": "sukhoverkhii"}
    (path,), warnings = docgen.write_permits(store, [p])
    (text, size), = _runs_with(path, "Very long description")
    assert text.endswith("…") and size == 6.5
    assert warnings == [(os.path.basename(path), ["WORK"])]


def test_big_team_uses_compact_ranks(store):
    everybody = [m["id"] for m in store.crew if m["id"] != "ce"]
    p = {"date": "2026-07-14", "job_id": "fo_strainers_cleaning", "crew": everybody,
         "pc": "pal", "transfer": "", "close": "pal"}
    (path,), _ = docgen.write_permits(store, [p])
    text = _all_text(path)
    assert "2E DMITRII, 3E ARUN" in text and "2ND ENG DMITRII" not in text


def test_fit_check_for_editor(store):
    tpl = storage.template_path(store.settings)
    assert docgen.check_fit(tpl, "WORK", "Short text") is None
    size, ok = docgen.check_fit(tpl, "WORK", "x" * 120)
    assert ok and 6.5 <= size < 9
    assert docgen.check_fit(tpl, "WORK", "x" * 400)[1] is False


def test_skip_weekdays(store):
    store.settings["skip_weekdays"] = [5, 6]
    plan = make_plan(store, 14)
    assert len(plan) == 10
    assert all(dt.date.fromisoformat(p["date"]).weekday() < 5 for p in plan)


def test_all_default_jobs_fit_at_normal_size(store):
    tpl = storage.template_path(store.settings)
    for j in store.jobs:
        for key in ("location", "plant", "work", "ra_no"):
            assert docgen.check_fit(tpl, key.upper(), j[key]) is None, (j["id"], key)
    ids = [j["id"] for j in store.jobs]
    assert len(ids) == len(set(ids)) >= 100
    ranks = {r["code"] for r in store.ranks}
    for j in store.jobs:
        assert set(j["lead_ranks"]) | set(j["officer_ranks"]) | set(j["rating_ranks"]) <= ranks


def test_every_ui_string_is_translated():
    tk = pytest.importorskip("tkinter")  # noqa: F841
    import ast
    import re as _re

    from ptw import gui
    from ptw.i18n import RU
    src = open(gui.__file__, encoding="utf-8").read()
    strings = set(gui.WEEKDAYS) | {t for _, t in gui.PLAN_COLUMNS + gui.HistoryTab.COLS}
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "T" and n.args \
                and isinstance(n.args[0], ast.Constant):
            strings.add(n.args[0].value)
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "hint":
            strings.add(ast.literal_eval(n.value))
    strings |= {m.group(1) for m in _re.finditer(
        r'\("\w+", "([^"]+)", "(?:str|int|bool|codes|range|rank)"\)', src)}
    strings |= {"5) P.C. (accepts permit):", "6) Transferred to:", "7) P.C. (closes permit):"}
    assert [s for s in strings if s not in RU] == []
