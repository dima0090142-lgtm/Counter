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


def _wait(app, cond, seconds=10):
    import time
    end = time.time() + seconds
    while time.time() < end and not cond():
        app.update()
        time.sleep(0.05)
    for _ in range(5):  # let the progress window close
        app.update()
        time.sleep(0.05)


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
        assert ed.current == ed.view[target]
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


def test_enter_presses_focused_button(app):
    from ptw import win95
    got = {}

    def press():
        box = [w for w in app.winfo_children() if isinstance(w, win95.MessageBox)][0]
        box.buttons[1].focus_set()  # Tab to "No"
        box.update()
        box.event_generate("<Return>")

    app.after(300, press)
    got["answer"] = gui.messagebox.askyesno("t", "Delete?", parent=app)
    assert got["answer"] is False


def test_message_box_gives_the_grab_back(app):
    from ptw import win95
    dlg = tk.Toplevel(app)
    dlg.grab_set()
    app.after(200, lambda: [w for w in dlg.winfo_children()
                            if isinstance(w, win95.MessageBox)][0]._done(True))
    gui.messagebox.showinfo("t", "x", parent=dlg)
    assert app.grab_current() is dlg
    dlg.destroy()


def test_new_rank_cannot_sign_as_pc(app, monkeypatch):
    monkeypatch.setattr(gui.messagebox, "showwarning", lambda *a, **k: None)
    app.edit_ranks()
    ed = [w for w in app.winfo_children() if isinstance(w, gui.ListEditor)][0]
    ed.new()
    rec = ed.records[-1]
    assert rec["can_pc"] is False and rec["can_loto"] is False and rec["officer"] is False
    assert rec["order"] > max(r["order"] for r in app.store.ranks)
    ed.destroy()


def test_recreate_file_keeps_number(app, tmp_path, monkeypatch):
    from ptw import docgen
    app.store.settings["output_dir"] = str(tmp_path / "out")
    p = {"date": "2026-10-12", "job_id": "fo_strainers_cleaning", "crew": ["singh"],
         "pc": "singh", "transfer": "", "close": "singh"}
    (path,), _ = docgen.write_permits(app.store, [p])
    os.utime(path, (1, 1))
    app.history_tab.show()
    app.history_tab.tree.selection_set(app.history_tab.tree.get_children()[0])
    monkeypatch.setattr(gui.messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(gui.messagebox, "showwarning", lambda *a, **k: None)
    app.history_tab.recreate()
    _wait(app, lambda: os.path.getmtime(path) > 1)  # written in the background
    assert os.path.getmtime(path) > 1  # written again
    assert len(app.store.history) == 1 and app.store.history[0]["permit_no"] == "285"
    assert len(os.listdir(tmp_path / "out")) == 1


def test_settings_refuse_bad_pc_ranks(app, monkeypatch):
    warned = []
    monkeypatch.setattr(gui.messagebox, "showwarning", lambda t, m, **k: warned.append(m))
    d = gui.SettingsDialog(app)
    e = d.code_entries["pc_supervisor_ranks"]
    e.delete(0, "end")
    e.insert(0, "4e")
    d.ok()
    assert warned and app.store.settings["pc_supervisor_ranks"] == ["2E", "3E"]
    e.delete(0, "end")
    e.insert(0, "2e, 3e")
    d.ok()
    assert app.store.settings["pc_supervisor_ranks"] == ["2E", "3E"]


def _jobs_editor(app):
    app.edit_jobs()
    return [w for w in app.winfo_children() if isinstance(w, gui.ListEditor)][0]


def test_jobs_editor_filter_and_sorted_new_job(app, monkeypatch):
    monkeypatch.setattr(gui.messagebox, "showwarning", lambda *a, **k: None)
    ed = _jobs_editor(app)
    ed.filter.insert(0, "purifier bowl")
    ed._refresh_view()
    shown = [ed.records[i] for i in ed.view]
    assert shown and len(shown) < len(ed.records)
    for r in shown:  # every word somewhere in the job (title, equipment, work ...)
        text = " ".join(str(v) for v in r.values()).lower()
        assert "purifier" in text and "bowl" in text
    assert "HFO Purifier Bowl Cleaning" in [r["title"] for r in shown]
    assert ed.count.cget("text").startswith(f"{len(shown)} ")
    # a new job does not end up at the bottom: after Apply it sits among its rank / title
    ed.new()
    assert ed.filter.get() == ""
    w = dict((k, v[0]) for k, v in ed.widgets.items())
    w["title"].insert(0, "AE Aaa New Filter Job")
    w["lead_ranks"].delete(0, "end")
    w["lead_ranks"].insert(0, "3E")
    ed.apply()
    row = ed.view.index(ed.current)
    assert 0 < row < len(ed.view) - 1
    before = ed.records[ed.view[row - 1]]
    assert before["lead_ranks"][0] in ("2E", "3E")
    saved = {}
    ed.on_save = lambda recs: saved.setdefault("recs", recs)
    ed.ok()
    titles = [r["title"] for r in saved["recs"]]
    assert titles.index("AE Aaa New Filter Job") < len(titles) - 1


def test_manual_job_filter(app):
    form = app.manual_tab.form
    form.filter.insert(0, "turbine")
    form._filter_jobs()
    assert len(form.jobs) == 1 and form.current_job()["id"] == "me_tc_turbine_washing"
    form.filter.delete(0, "end")
    form.filter.insert(0, "ra-104")
    form._filter_jobs()
    assert form.current_job()["ra_no"] == "RA-104"
    form._clear_filter()
    assert len(form.jobs) == len(form.all_jobs)


class _Key:
    def __init__(self, keysym, keycode=0):
        self.keysym, self.keycode = keysym, keycode


def test_ctrl_a_selects_all_rows_in_any_layout(app):
    from ptw import win95
    app.auto_tab.generate()
    tree = app.auto_tab.tree
    assert win95.key_letter(_Key("a")) == "a"
    assert win95.key_letter(_Key("Cyrillic_ef")) == "a"  # Russian layout: Ctrl+Ф
    tree.focus_set()
    app.update()
    assert app._on_ctrl(_Key("Cyrillic_ef")) == "break"
    assert len(tree.selection()) == len(tree.get_children()) == len(app.auto_tab.plan)


def test_hotkeys_generate_and_tabs(app):
    app.auto_tab.plan = []
    app._on_ctrl(_Key("g"))
    assert app.auto_tab.plan
    app._on_ctrl(_Key("3"))
    assert app.notebook.index("current") == 2


def test_create_files_in_background_with_progress(app, tmp_path, monkeypatch):
    import datetime as dt
    from ptw import win95
    app.store.settings["output_dir"] = str(tmp_path / "out")
    app.store.settings["open_folder_after"] = False
    seen = []
    orig = win95.ProgressDialog.set
    monkeypatch.setattr(win95.ProgressDialog, "set",
                        lambda self, d, t, n="": (seen.append((d, t)), orig(self, d, t, n)))
    app.auto_tab.set_range(dt.date(2026, 6, 1), dt.date(2026, 6, 30))
    app.auto_tab.generate()
    app.auto_tab.create()
    _wait(app, lambda: not app.auto_tab.plan)
    assert len(os.listdir(tmp_path / "out")) == 30
    assert seen and seen[-1] == (30, 30)
    assert len(app.store.history) == 30


def test_manual_generate_and_crew_table(app):
    form = app.manual_tab.form
    form.generate()
    p = form.get()
    assert p["crew"] and app.store.can_pc(p["pc"])
    marks = {iid: form.crew_tree.set(iid, "on") for iid in form.crew_tree.get_children()}
    assert {k for k, v in marks.items() if v == "\u2611"} == set(p["crew"])
    form._crew_all(False)
    assert form.selected_crew() == []
    form._crew_toggle("singh")
    assert form.selected_crew() == ["singh"]


def test_ctrl_c_copies_rows(app):
    app.auto_tab.generate()
    tree = app.auto_tab.tree
    tree.selection_set(tree.get_children())
    tree.focus_set()
    app.update()
    assert app._on_ctrl(_Key("Cyrillic_es")) == "break"  # Ctrl+C with the Russian layout
    text = app.clipboard_get()
    assert text.split("\n")[0].split("\t")[0] in ("Date", "Дата")
    assert len(text.split("\n")) == len(tree.get_children()) + 1


def test_calendars_start_today_and_stop_today(app):
    import datetime as dt
    today = dt.date.today()
    assert app.auto_tab.cal_from.selection_get() == today
    assert app.auto_tab.cal_to.selection_get() == today
    assert app.auto_tab.cal_to["maxdate"] == today
