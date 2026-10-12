"""GUI checks (need a display: run under xvfb-run on Linux; skipped without one)."""
import os
import sys

import pytest

tk = pytest.importorskip("tkinter")
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    pytest.skip("no display", allow_module_level=True)

from ptw import gui, sound, storage  # noqa: E402


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path / "data"))
    sound.enabled = False
    monkeypatch.setattr(gui.App, "_first_start", lambda self: None)
    a = gui.App(splash=False)
    a.store.settings["sounds"] = False
    sound.enabled = False
    a.update()
    yield a
    a.destroy()


def _click(lb, index):
    """What a mouse click on a Listbox row does."""
    lb.selection_clear(0, "end")
    lb.selection_set(index)
    lb.event_generate("<<ListboxSelect>>")
    lb.update()


def test_list_editor_highlights_one_row(app, monkeypatch):
    monkeypatch.setattr(gui.messagebox, "showwarning", lambda *a, **k: None)
    ed = gui.ListEditor(app, "Jobs", app.store.jobs,
                        [("id", "ID", "str"), ("title", "Title (file name)", "str"),
                         ("work", "Work to be done", "str")],
                        lambda j: j["title"], lambda j: j["title"], lambda r: None)
    ed.update()
    for target in (3, 7, 2):
        # change the current record, then go to another one (this used to leave 2 rows blue)
        w = ed.widgets["work"][0]
        w.insert("end", " x")
        _click(ed.lb, target)
        assert ed.lb.curselection() == (target,)
        assert ed.current == target
    ed.destroy()


def test_pc_lists_only_allowed_ranks(app):
    form = app.manual_tab.form
    for mid in ("kaushal", "pal", "padilla", "singh"):
        form.check_vars[mid].set(True)
    form._crew_changed()
    names = [n for n in form.roles["pc"]["values"] if n]
    assert names == ["Third Engineer / Arun Singh"]
    form.check_vars["singh"].set(False)
    form._crew_changed()
    jid = [j["id"] for j in form.jobs].index("fo_strainers_cleaning")
    form.job.current(jid)
    with pytest.raises(ValueError):
        form.get()  # 4E + 5E + motorman: nobody may sign as P.C.


def test_manual_loto_empty_until_ticked(app):
    form = app.manual_tab.form
    jid = [j["id"] for j in form.jobs].index("hfo_purifier_bowl_cleaning")
    form.job.current(jid)
    form._job_changed()
    form.auto_crew()
    p = form.get()
    assert p["loto"] == ""  # empty by default
    assert app.store.can_pc(p["pc"]) and app.store.can_pc(p["close"])
    form.loto_var.set(True)
    form._loto_toggled()
    assert form.get()["loto"] == "remesan"  # ticked: the electrician is proposed
    form.loto_var.set(False)
    form._loto_toggled()
    assert form.get()["loto"] == ""
