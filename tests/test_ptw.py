import datetime as dt
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
    path = docgen.write_permits(store, plan)[0]
    assert path.endswith("2026-07-13 ME Fuel Valves Overhaul.docx")
    text = _all_text(path)
    assert "{{" not in text
    for s in ("13/07/2026", "E-   41/2026", "Main Engine fuel injection valves",
              "Risk Assessment number RA-E01", "2ND ENG DMITRII, 3RD ENG ARUN, 4TH ENG PARTH",
              "Chief Engineer / Vadim Medvedev", "Fourth Engineer / Parth Kaushal",
              "Third Engineer / Arun Singh", "Asst. Second Engineer / Dmitrii Sukhoverkhii",
              "08:00", "12:00", "20:00"):
        assert s in text, s
    assert store.settings["next_permit_no"] == 42
    assert store.history[-1]["file"] == "2026-07-13 ME Fuel Valves Overhaul.docx"


def test_no_transfer_leaves_section_6_empty(store):
    plan = [{"date": "2026-07-14", "job_id": "fo_strainers_cleaning", "crew": ["pal", "padilla"],
             "pc": "pal", "transfer": "", "close": "pal"}]
    text = _all_text(docgen.write_permits(store, plan)[0])
    assert text.count("14/07/2026") == 3  # header, section 5, section 7
    assert "12:00" not in text


def test_same_name_gets_suffix(store):
    p = {"date": "2026-07-14", "job_id": "fo_strainers_cleaning", "crew": ["pal"],
         "pc": "pal", "transfer": "", "close": "pal"}
    a, b = docgen.write_permits(store, [dict(p), dict(p)])
    assert a != b and b.endswith("(2).docx")


def test_file_name_is_safe(store):
    store.settings["filename_pattern"] = "{date} {title} / {ra}"
    name = docgen.file_name(store, {"date": "2026-07-14", "job_id": "fo_strainers_cleaning"})
    assert "/" not in name and name.endswith(".docx")
