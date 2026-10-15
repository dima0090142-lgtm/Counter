"""Main window of the Permit to Work generator."""
import copy
import datetime as dt
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, ttk

from tkcalendar import Calendar, DateEntry

from . import __version__, docgen, generator, i18n, printing, sound, storage, win95
from . import log as ptwlog
from .i18n import T
from .win95 import BG

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def app_title():
    return T("Permit to Work Generator")


class _Messages:
    """Win95-style replacement for tkinter.messagebox, with the program sounds.

    Same call style: messagebox.showinfo(title, text, parent=...)."""

    SOUNDS = {"info": "ding", "warning": "exclamation", "error": "chord", "question": None}

    def _box(self, kind, title, text, buttons, cancel, parent):
        if self.SOUNDS[kind]:
            sound.play(self.SOUNDS[kind])
        return win95.MessageBox(parent, title, text, kind, buttons, cancel).result

    def showinfo(self, title, text, parent=None):
        self._box("info", title, text, [(True, T("OK"))], True, parent)

    def showwarning(self, title, text, parent=None):
        self._box("warning", title, text, [(True, T("OK"))], True, parent)

    def showerror(self, title, text, parent=None):
        self._box("error", title, text, [(True, T("OK"))], True, parent)

    def askyesno(self, title, text, parent=None):
        return self._box("question", title, text, [(True, T("Yes")), (False, T("No"))], False, parent)

    def askyesnocancel(self, title, text, parent=None):
        return self._box("question", title, text,
                         [(True, T("Yes")), (False, T("No")), (None, T("Cancel"))], None, parent)


messagebox = _Messages()


def open_path(path):
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def member_label(store, m):
    return f"{m['rank']:<6} {m['first_name']} {m['last_name']}"


def cal_options():
    """Calendars start on today and do not go into the future (permits are not made ahead)."""
    opts = win95.calendar_options("ru_RU" if i18n.language() == "ru" else "en_GB")
    opts["maxdate"] = dt.date.today()
    return opts


def fit_warnings(store, values):
    """Human readable notes for values that will not fit their line at 9 pt."""
    s = store.settings
    template = storage.template_path(s)
    notes = []
    for key, text in values.items():
        res = docgen.check_fit(template, key, text, float(s.get("min_font_size", 6.5)))
        if res:
            size, ok = res
            msg = T("Text is long and will be printed smaller ({size} pt):", size=size) if ok \
                else T("Text is too long for one line even at {size} pt:", size=size)
            notes.append(f"{msg}\n   {text}")
    return notes


# ======================================================================
# Permit form (used by the Manual tab and the "Edit permit" dialog)
# ======================================================================

class PermitForm(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.store = app.store
        self.check_vars = {}
        self.role_ids = {}
        self.lead = ""

        top = win95.group(self, T("Permit"))
        top.pack(fill="x", padx=4, pady=4)
        tk.Label(top, text=T("Date:")).grid(row=0, column=0, sticky="w")
        self.date = DateEntry(top, width=12, **cal_options())
        self.date.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        win95.fix_calendar_arrows(self.date)
        tk.Label(top, text=T("Permit No:")).grid(row=0, column=2, sticky="w", padx=(16, 0))
        self.permit_no = tk.Entry(top, width=8)
        self.permit_no.grid(row=0, column=3, sticky="w", padx=4)
        tk.Label(top, text=T("(empty = automatic)"), fg=win95.DARK).grid(row=0, column=4, sticky="w")

        tk.Label(top, text=T("Filter:")).grid(row=1, column=0, sticky="w")
        frow = tk.Frame(top, bg=BG)
        frow.grid(row=1, column=1, columnspan=4, sticky="we", padx=4, pady=2)
        self.filter = tk.Entry(frow, width=30)
        self.filter.pack(side="left")
        self.filter.bind("<KeyRelease>", lambda e: self._filter_jobs())
        self.filter.bind("<Return>", lambda e: self.job.focus_set())
        win95.button(frow, "x", self._clear_filter, width=2).pack(side="left", padx=4)
        self.filter_count = tk.Label(frow, fg=win95.DARK)
        self.filter_count.pack(side="left", padx=4)
        tk.Label(frow, text=T("(title, equipment, location, rank or RA No)"),
                 fg=win95.DARK).pack(side="left")
        tk.Label(top, text=T("Job:")).grid(row=2, column=0, sticky="w")
        self.job = ttk.Combobox(top, state="readonly", width=48, height=25)
        self.job.grid(row=2, column=1, columnspan=4, sticky="we", padx=4, pady=2)
        self.job.bind("<<ComboboxSelected>>", lambda e: self._job_changed())

        self.info = tk.Label(top, justify="left", anchor="w", relief="sunken", bd=2,
                             bg=win95.WHITE, padx=4, pady=2, height=4)
        self.info.grid(row=3, column=0, columnspan=5, sticky="we", pady=4)
        top.columnconfigure(4, weight=1)

        mid = tk.Frame(self, bg=BG)
        mid.pack(fill="both", expand=True)
        crew_box = win95.group(mid, T("Crew taking part"))
        crew_box.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        # a table with a scrollbar (any number of crew): click / Space ticks a row
        cols = [("on", ""), ("rank", T("Rank")), ("name", T("Name")), ("pc", "P.C.")]
        self.crew_frame, self.crew_tree = win95.scrolled_tree(crew_box, cols, [28, 70, 220, 50],
                                                              height=9)
        self.crew_tree.configure(selectmode="browse")
        self.crew_tree.column("on", anchor="center")
        self.crew_frame.pack(fill="both", expand=True)
        self.crew_tree.bind("<Button-1>", self._crew_click)
        self.crew_tree.bind("<space>", lambda e: self._crew_toggle(self.crew_tree.focus()))
        cb = tk.Frame(crew_box, bg=BG)
        cb.pack(fill="x", pady=(4, 0))
        win95.button(cb, T("Auto-pick crew"), self.auto_crew, width=18).pack(side="left")
        win95.button(cb, T("All"), lambda: self._crew_all(True), width=8).pack(side="left", padx=4)
        win95.button(cb, T("None"), lambda: self._crew_all(False), width=8).pack(side="left")

        roles = win95.group(mid, T("Signatures"))
        roles.pack(side="left", fill="y", padx=4, pady=4)
        self.roles = {}
        for i, (key, text) in enumerate((("pc", "5) P.C. (accepts permit):"),
                                         ("transfer", "6) Transferred to:"),
                                         ("close", "7) P.C. (closes permit):"))):
            tk.Label(roles, text=T(text)).grid(row=i * 2, column=0, sticky="w")
            cb = ttk.Combobox(roles, state="readonly", width=34)
            cb.grid(row=i * 2 + 1, column=0, sticky="w", pady=(0, 6))
            self.roles[key] = cb
        self.pc_hint = tk.Label(roles, anchor="w", fg=win95.DARK, justify="left")
        self.pc_hint.grid(row=6, column=0, sticky="w", pady=(0, 6))
        self.loto_var = tk.BooleanVar(value=False)
        tk.Checkbutton(roles, text=T("4) LOTO procedure, Rank/Name (A.O.):"), variable=self.loto_var,
                       command=self._loto_toggled).grid(row=7, column=0, sticky="w")
        self.loto = ttk.Combobox(roles, state="readonly", width=34)
        self.loto.grid(row=8, column=0, sticky="w", pady=(0, 6))
        self.ao_label = tk.Label(roles, anchor="w", fg=win95.DARK)
        self.ao_label.grid(row=9, column=0, sticky="w")
        self.refresh()

    # --- data ---
    def refresh(self):
        s = self.store.settings
        self.all_jobs = sorted((j for j in self.store.jobs if j.get("active", True)),
                               key=lambda j: j["title"].lower())
        self._filter_jobs()
        old = {k for k, v in self.check_vars.items() if v.get()}
        self.check_vars = {}
        self.crew_tree.delete(*self.crew_tree.get_children())
        members = [m for m in self.store.crew
                   if m.get("active", True) and m["id"] != s.get("ao_id")]
        members.sort(key=lambda m: self.store.rank(m["rank"])["order"])
        for m in members:
            v = tk.BooleanVar(value=m["id"] in old)
            self.crew_tree.insert("", "end", iid=m["id"], values=(
                "", m["rank"], f"{m['first_name']} {m['last_name']}",
                "P.C." if self.store.can_pc(m["id"]) else ""))
            v.trace_add("write", lambda *_a, mid=m["id"]: self._crew_row(mid))
            self.check_vars[m["id"]] = v
            self._crew_row(m["id"])
        ao = self.store.member(s.get("ao_id"))
        self.ao_label.config(text="A.O.: " + (generator.sign_text(self.store, ao["id"]) if ao
                                               else T("(not set)")))
        pcs = sorted({m["rank"] for m in self.store.crew if self.store.can_pc(m["id"])},
                     key=lambda r: self.store.rank(r)["order"])
        self.pc_ranks_text = ", ".join(pcs) or "-"
        self.pc_hint.config(text=T("P.C. can be: {ranks}", ranks=self.pc_ranks_text))
        self.loto_ids = {"": ""}
        for mid in generator.loto_candidates(self.store):
            self.loto_ids[generator.sign_text(self.store, mid)] = mid
        cur = self.loto.get()
        self.loto["values"] = list(self.loto_ids)
        if cur not in self.loto_ids:
            self.loto.set("")
        self._update_role_lists()

    def _show_job(self):
        j = self.current_job()
        if not j:
            self.info.config(text="")
            return
        loto = "   " + T("LOTO usually needed: {answer}",
                          answer=T("yes") if j.get("loto") else T("no"))
        self.info.config(text=f"{T('Location')}:  {j['location']}\n{T('Plant')}:  {j['plant']}\n"
                              f"{T('Work')}:  {j['work']}\nRisk Assessment:  {j.get('ra_no', '')}"
                              + loto)

    def _job_changed(self):
        self._show_job()

    def _filter_jobs(self):
        """Show only jobs matching the filter words; keep the chosen job if it matches."""
        cur = self.current_job() if hasattr(self, "jobs") else None
        words = self.filter.get().lower().split()
        self.jobs = [j for j in self.all_jobs
                     if not words or text_match(words, j["title"], j.get("plant", ""),
                                                j.get("location", ""), j.get("work", ""),
                                                j.get("ra_no", ""), *j.get("lead_ranks", []))]
        self.job["values"] = [f"{j['title']}   [{j.get('ra_no', '')}]" for j in self.jobs]
        self.filter_count.config(text=T("{n} of {total}", n=len(self.jobs), total=len(self.all_jobs)))
        ids = [j["id"] for j in self.jobs]
        if cur is not None and cur["id"] in ids:
            self.job.current(ids.index(cur["id"]))
        elif len(self.jobs) == 1:  # only one left: take it
            self.job.current(0)
            self._job_changed()
        else:
            self.job.set("")
            self._show_job()

    def _clear_filter(self):
        self.filter.delete(0, "end")
        self._filter_jobs()

    def focus_filter(self):
        self.filter.focus_set()
        self.filter.select_range(0, "end")

    def current_job(self):
        i = self.job.current()
        return self.jobs[i] if 0 <= i < len(self.jobs) else None

    def _crew_row(self, mid):
        if self.crew_tree.exists(mid):
            self.crew_tree.set(mid, "on", "\u2611" if self.check_vars[mid].get() else "\u2610")

    def _crew_toggle(self, mid):
        if mid in self.check_vars:
            self.check_vars[mid].set(not self.check_vars[mid].get())
            self._crew_changed()

    def _crew_click(self, event):
        mid = self.crew_tree.identify_row(event.y)
        if mid and self.crew_tree.identify_region(event.x, event.y) == "cell":
            self.crew_tree.focus(mid)
            self.crew_tree.selection_set(mid)
            self._crew_toggle(mid)
            return "break"
        return None

    def _crew_all(self, on):
        for v in self.check_vars.values():
            v.set(on)
        self._crew_changed()

    def selected_crew(self):
        ids = [k for k, v in self.check_vars.items() if v.get()]
        return generator.sort_by_rank(self.store, ids)

    def _update_role_lists(self, keep=True):
        """Only members allowed to be P.C. can be chosen for sections 5, 6 and 7."""
        ids = [i for i in self.selected_crew() if self.store.can_pc(i)]
        self.role_ids = {"": ""}
        for i in ids:
            self.role_ids[generator.sign_text(self.store, i)] = i
        for cb in self.roles.values():
            cur = cb.get()
            cb["values"] = list(self.role_ids)
            if not keep or cur not in self.role_ids:
                cb.set("")

    def _crew_changed(self):
        crew = self.selected_crew()
        if self.lead not in crew:
            self.lead = crew[0] if crew else ""
        self._update_role_lists()
        self.set_roles(*generator.default_roles(self.store, crew, self.lead,
                                                generator.supervisor_ranks(self.store, self.current_job())))
        if self.loto_var.get() and not self.loto.get():
            self._loto_toggled()

    def _loto_toggled(self):
        if not self.loto_var.get():
            self.loto.set("")
            self.loto.configure(state="disabled")
            return
        self.loto.configure(state="readonly")
        if not self.loto.get():
            pc = self.role_ids.get(self.roles["pc"].get(), "")
            mid = generator.pick_loto(self.store, self.selected_crew(), pc)
            self.loto.set(generator.sign_text(self.store, mid) if mid else "")

    def set_roles(self, pc, transfer, close):
        for key, mid in (("pc", pc), ("transfer", transfer), ("close", close)):
            self.roles[key].set(generator.sign_text(self.store, mid) if mid else "")

    def generate(self):
        """Pick a job and crew for the chosen date with the same rules as Auto generate."""
        day = self.date.get_date()
        planner = generator.Planner(self.store)
        planner.load_history(day, day)
        used, busy = planner._day_start(day)
        p = planner.make_permit(day, used, busy) or planner.make_permit(day)
        if p is None:
            messagebox.showinfo(app_title(), T("No job can be planned (check the jobs and crew)."),
                                parent=self)
            return
        loto = self.loto.get() if self.loto_var.get() else ""
        self.set(p)
        if loto:  # LOTO ticked by the user stays
            self.loto_var.set(True)
            self.loto.set(loto)
            self._loto_toggled()

    def auto_crew(self):
        j = self.current_job()
        if not j:
            messagebox.showwarning(app_title(), T("Select a job first."), parent=self)
            return
        planner = generator.Planner(self.store)
        day = self.date.get_date()
        planner.load_history(day + dt.timedelta(days=1))
        team = planner.make_team(j, day)
        for k, v in self.check_vars.items():
            v.set(k in team["crew"])
        self.lead = team["lead"]
        self._update_role_lists()
        self.set_roles(team["pc"], team["transfer"], team["close"])
        if self.loto_var.get() and not self.loto.get():  # LOTO ticked by the user: fill a name
            self._loto_toggled()

    # --- in / out ---
    def set(self, permit):
        self.date.set_date(generator.parse_date(permit["date"]))
        if self.filter.get():
            self._clear_filter()
        ids = [j["id"] for j in self.jobs]
        if permit["job_id"] in ids:
            self.job.current(ids.index(permit["job_id"]))
        self._show_job()
        for k, v in self.check_vars.items():
            v.set(k in permit["crew"])
        self.lead = permit.get("lead") or (permit["crew"][0] if permit["crew"] else "")
        self._update_role_lists(keep=False)
        self.set_roles(permit.get("pc"), permit.get("transfer"), permit.get("close"))
        loto = permit.get("loto") or ""
        self.loto_var.set(bool(loto))
        self.loto.set(generator.sign_text(self.store, loto) if loto else "")
        self._loto_toggled()
        self.permit_no.delete(0, "end")
        if permit.get("permit_no"):
            self.permit_no.insert(0, str(permit["permit_no"]))

    def get(self):
        j = self.current_job()
        if not j:
            raise ValueError(T("Select a job."))
        crew = self.selected_crew()
        if not crew:
            raise ValueError(T("Select at least one crew member."))
        if not any(self.store.can_pc(i) for i in crew):
            raise ValueError(T("Nobody in the team can sign as P.C. Add one of: {ranks}.",
                               ranks=self.pc_ranks_text))
        pc = self.role_ids.get(self.roles["pc"].get(), "")
        close = self.role_ids.get(self.roles["close"].get(), "")
        if not pc or not close:
            raise ValueError(T("Choose the P.C. for sections 5 and 7."))
        loto = self.loto_ids.get(self.loto.get(), "") if self.loto_var.get() else ""
        if self.loto_var.get() and not loto:
            raise ValueError(T("Choose who applies LOTO, or untick LOTO."))
        no = self.permit_no.get().strip()
        return {"date": self.date.get_date().isoformat(), "job_id": j["id"], "crew": crew,
                "lead": self.lead if self.lead in crew else crew[0],
                "pc": pc, "transfer": self.role_ids.get(self.roles["transfer"].get(), ""),
                "close": close, "loto": loto, "permit_no": no or None}


class PermitDialog(tk.Toplevel):
    def __init__(self, app, permit):
        super().__init__(app)
        self.title(T("Edit permit"))
        self.configure(bg=BG)
        self.transient(app)
        self.result = None
        self.form = PermitForm(self, app)
        self.form.pack(fill="both", expand=True, padx=4, pady=4)
        self.form.set(permit)
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=8)
        win95.button(bar, T("Cancel"), self.destroy).pack(side="right", padx=4)
        win95.button(bar, T("OK"), self.ok).pack(side="right", padx=4)
        win95.center(self, app)
        self.grab_set()
        self.wait_window()

    def ok(self):
        try:
            self.result = self.form.get()
        except ValueError as e:
            messagebox.showwarning(app_title(), str(e), parent=self)
            return
        self.destroy()


def run_with_progress(app, parent, title, text, work, done):
    """Run work(progress, cancelled) in a background thread with a progress window,
    so the window keeps responding (slow network drive, hundreds of files).

    done(result, error, cancelled) is called in the GUI thread at the end."""
    import queue
    import threading
    q = queue.Queue()
    dlg = win95.ProgressDialog(parent, title, text, T("Cancel"))
    state = {"result": None, "error": None}

    def worker():
        try:
            state["result"] = work(lambda k, n, name: q.put((k, n, name)), lambda: dlg.cancelled)
        except Exception as e:  # noqa: BLE001 - reported in the GUI thread and logged
            state["error"] = e
            ptwlog.error(f"{title} failed", True)
        finally:
            q.put(None)

    def poll():
        last = None
        try:
            while True:
                item = q.get_nowait()
                if item is None:
                    if last:
                        dlg.set(*last)
                    dlg.close()
                    done(state["result"], state["error"], dlg.cancelled)
                    return
                last = item
        except queue.Empty:
            pass
        if last:
            dlg.set(*last)
        app.after(100, poll)

    ptwlog.log.info("%s started", title)
    threading.Thread(target=worker, name="files", daemon=True).start()
    app.after(100, poll)


def show_write_result(app, parent, paths, warnings):
    """Status line, warnings about long text, offer to open the folder."""
    s = app.store
    app.history_tab.show()
    app.auto_tab.show()  # plan numbers continue after the new history
    app.status.set(T("{n} files created in {folder}", n=len(paths), folder=s.settings["output_dir"]))
    if not warnings:
        sound.play("tada")
    else:
        lines = [f"{name}: {', '.join(keys)}" for name, keys in warnings[:15]]
        messagebox.showwarning(app_title(), T("Some values were too long even in the smallest font "
                                              "and were shortened (…) to keep the permit on one page:") + "\n\n"
                               + "\n".join(lines), parent=parent)


# ======================================================================
# Tabs
# ======================================================================

PLAN_COLUMNS = [("date", "Date"), ("no", "No."), ("job", "Job"), ("ra", "RA No"),
                ("crew", "Issued to"), ("pc", "P.C. (5)"), ("transfer", "Transfer (6)"),
                ("close", "Close (7)"), ("loto", "LOTO")]
PLAN_WIDTHS = [70, 40, 160, 48, 250, 64, 64, 64, 64]


def short_name(store, mid):
    m = store.member(mid) if mid else None
    return f"{m['rank']} {m['first_name']}" if m else ""


class AutoTab(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.store = app.store
        self.plan = []

        left = tk.Frame(self, bg=BG)
        left.pack(side="left", fill="y", padx=4, pady=4)
        today = dt.date.today()
        g1 = win95.group(left, T("From"))
        g1.pack(fill="x")
        self.cal_from = Calendar(g1, selectmode="day", year=today.year, month=today.month,
                                 day=today.day, **cal_options())
        self.cal_from.pack()
        win95.fix_calendar_arrows(self.cal_from)
        g2 = win95.group(left, T("To"))
        g2.pack(fill="x", pady=(6, 0))
        end = today
        self.cal_to = Calendar(g2, selectmode="day", year=end.year, month=end.month,
                               day=end.day, **cal_options())
        self.cal_to.pack()
        win95.fix_calendar_arrows(self.cal_to)
        self.cal_from.bind("<<CalendarSelected>>", self._from_changed)
        self.range_label = tk.Label(left, anchor="w")
        self.range_label.pack(fill="x", pady=4)
        self.cal_to.bind("<<CalendarSelected>>", lambda e: self._update_range())
        self._update_range()

        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        bar = tk.Frame(right, bg=BG)
        bar.pack(fill="x", pady=(0, 4))
        win95.button(bar, T("Generate"), self.generate, width=14).pack(side="left", padx=(0, 4))
        win95.button(bar, T("Reroll"), self.reroll).pack(side="left", padx=4)
        win95.button(bar, T("Edit..."), self.edit).pack(side="left", padx=4)
        win95.button(bar, T("Remove"), self.remove).pack(side="left", padx=4)
        win95.button(bar, T("Create files"), self.create, width=14,
                     font=win95.FONT_BOLD).pack(side="right")
        g = win95.group(right, T("Plan"))
        g.pack(fill="both", expand=True)
        cols = [(k, T(t)) for k, t in PLAN_COLUMNS]
        f, self.tree = win95.scrolled_tree(g, cols, PLAN_WIDTHS, height=20)
        f.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.edit())
        self.tree.bind("<Return>", lambda e: self.edit())
        self.tree.bind("<F2>", lambda e: self.edit())
        self.tree.bind("<Delete>", lambda e: self.remove())

    def set_range(self, a, b):
        for cal, d in ((self.cal_from, a), (self.cal_to, b)):
            cal.selection_set(d)
            cal.see(d)
        self._update_range()

    def _from_changed(self, _e=None):
        a = self.cal_from.selection_get()
        if self.cal_to.selection_get() < a:
            self.cal_to.selection_set(a)
            self.cal_to.see(a)
        self._update_range()

    def _update_range(self):
        a, b = self.cal_from.selection_get(), self.cal_to.selection_get()
        days = (b - a).days + 1
        self.range_label.config(text=f"{a:%d/%m/%Y} - {b:%d/%m/%Y}  ({max(days, 0)} {T('days')})")

    def generate(self):
        a, b = self.cal_from.selection_get(), self.cal_to.selection_get()
        if b < a:
            messagebox.showwarning(app_title(), T("'To' date is before 'From' date."), parent=self)
            return
        if (b - a).days > 366:
            messagebox.showwarning(app_title(), T("Period is longer than one year."), parent=self)
            return
        self.plan = generator.Planner(self.store).plan(a, b)
        self.show()
        if not self.plan:
            messagebox.showinfo(app_title(), T("No days in the period (check 'Days without "
                                               "permits' in Settings)."), parent=self)
        self.app.status.set(T("{n} permits planned. Check the list, then press 'Create files'.",
                              n=len(self.plan)))

    def show(self, replace=False):
        self.tree.delete(*self.tree.get_children())
        st = self.store
        numbers = generator.permit_numbers(st, self.plan, replace)
        for i, (p, no) in enumerate(zip(self.plan, numbers)):
            j = st.job(p["job_id"]) or {"title": p["job_id"]}
            d = generator.parse_date(p["date"])
            self.tree.insert("", "end", iid=str(i), values=(
                d.strftime("%d/%m/%Y"), no, j["title"], j.get("ra_no", ""),
                generator.issued_to_text(st, p["crew"]), short_name(st, p.get("pc")),
                short_name(st, p.get("transfer")), short_name(st, p.get("close")),
                short_name(st, p.get("loto"))))

    def _selected(self):
        return sorted(int(i) for i in self.tree.selection())

    def reroll(self):
        sel = self._selected()
        if not sel:
            messagebox.showinfo(app_title(), T("Select permits in the list to reroll."), parent=self)
            return
        planner = generator.Planner(self.store)
        for i in sel:
            planner.reroll(self.plan, i)
        self.show()
        for i in sel:
            self.tree.selection_add(str(i))

    def edit(self):
        sel = self._selected()
        if not sel:
            return
        permit = self.plan[sel[0]]
        d = PermitDialog(self.app, permit)
        if d.result and any(p is permit for p in self.plan):  # the plan may have changed
            i = next(i for i, p in enumerate(self.plan) if p is permit)
            self.plan[i] = d.result
            self.plan.sort(key=lambda p: p["date"])
            self.show()

    def remove(self):
        for i in reversed(self._selected()):
            del self.plan[i]
        self.show()

    def create(self):
        if not self.plan:
            messagebox.showinfo(app_title(), T("Nothing to create. Press 'Generate' first."),
                                parent=self)
            return
        if not self.app.ensure_output_dir() or not self.app.check_template(self):
            return
        bad = [(i, generator.check_permit(self.store, p)) for i, p in enumerate(self.plan)]
        bad = [(i, probs) for i, probs in bad if probs]
        if bad:
            self.tree.selection_set([str(i) for i, _ in bad])
            self.tree.see(str(bad[0][0]))
            lines = [f"{generator.parse_date(self.plan[i]['date']):%d/%m/%Y}: {', '.join(p)}"
                     for i, p in bad[:12]]
            messagebox.showwarning(app_title(), T("These plan rows cannot be printed (selected "
                                                  "in the list). Use Reroll or Edit...:")
                                   + "\n\n" + "\n".join(lines), parent=self)
            return
        dates = {p["date"] for p in self.plan}
        replace = False
        if any(h["date"] in dates for h in self.store.history):
            ans = messagebox.askyesnocancel(
                app_title(), T("History already has permits for some of these dates.\n\n"
                               "Yes - replace them (old files and history entries are removed)\n"
                               "No - keep both"), parent=self)
            if ans is None:
                return
            replace = ans
            self.show(replace)  # the numbers shown are the numbers printed
        plan = list(self.plan)

        def work(progress, cancelled):
            return docgen.write_permits(self.store, plan, replace_dates=replace,
                                        progress=progress, cancelled=cancelled)

        def done(result, error, cancelled):
            if error is not None:
                self.app.history_tab.show()
                messagebox.showerror(app_title(), f"{T('Could not create files:')}\n{error}",
                                     parent=self)
                return
            paths, warnings = result
            show_write_result(self.app, self, paths, warnings)
            written = {id(p) for p in plan[:len(paths)]}
            self.plan = [p for p in self.plan if id(p) not in written]  # cancelled: rest stays
            self.show()
            if cancelled:
                self.app.status.set(T("Cancelled: {n} of {total} files created",
                                      n=len(paths), total=len(plan)))
            elif self.store.settings.get("open_folder_after", True):
                open_path(self.store.settings["output_dir"])

        run_with_progress(self.app, self, app_title(), T("Creating permit files..."), work, done)


class ManualTab(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.form = PermitForm(self, app)
        self.form.pack(fill="both", expand=True, padx=4, pady=4)
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        win95.button(bar, T("Generate"), self.form.generate, width=14).pack(side="left")
        tk.Label(bar, text=T("(a job and crew for the date - like Auto generate)"),
                 fg=win95.DARK).pack(side="left", padx=8)
        win95.button(bar, T("Create file"), self.create, width=14,
                     font=win95.FONT_BOLD).pack(side="right")

    def create(self):
        try:
            p = self.form.get()
        except ValueError as e:
            messagebox.showwarning(app_title(), str(e), parent=self)
            return
        if not self.app.ensure_output_dir() or not self.app.check_template(self):
            return
        def work(progress, cancelled):
            return docgen.write_permits(self.app.store, [p], progress=progress, cancelled=cancelled)

        def done(result, error, cancelled):
            if error is not None:
                messagebox.showerror(app_title(), f"{T('Could not create file:')}\n{error}",
                                     parent=self)
                return
            paths, warnings = result
            if not paths:
                return
            show_write_result(self.app, self, paths, warnings)
            name = os.path.basename(paths[0])
            self.app.status.set(T("Created {name}", name=name))
            self.form.permit_no.delete(0, "end")
            if messagebox.askyesno(app_title(), T("Created:\n{name}\n\nOpen it now?", name=name),
                                   parent=self):
                open_path(paths[0])

        run_with_progress(self.app, self, app_title(), T("Creating permit files..."), work, done)


class HistoryTab(tk.Frame):
    COLS = [("date", "Date"), ("no", "No."), ("job", "Job"), ("crew", "Issued to"), ("file", "File")]

    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=4, pady=4)
        win95.button(bar, T("Open file"), self.open_file, width=14).pack(side="left", padx=(0, 4))
        win95.button(bar, T("Open folder"), self.open_folder, width=14).pack(side="left", padx=4)
        win95.button(bar, T("Delete entry"), self.delete, width=14).pack(side="left", padx=4)
        win95.button(bar, T("Recreate file"), self.recreate, width=14).pack(side="left", padx=4)
        win95.button(bar, T("Print (test)"), self.print_files, width=14).pack(side="left", padx=4)
        tk.Label(bar, text=T("History is used to keep jobs and crew different from day to day."),
                 fg=win95.DARK).pack(side="left", padx=8)
        cols = [(k, T(t)) for k, t in self.COLS]
        f, self.tree = win95.scrolled_tree(self, cols, [74, 40, 200, 300, 260], height=20)
        f.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.tree.bind("<Double-1>", lambda e: self.open_file())
        self.tree.bind("<Return>", lambda e: self.open_file())
        self.tree.bind("<Delete>", lambda e: self.delete())
        self.show()

    def show(self):
        st = self.app.store
        self.tree.delete(*self.tree.get_children())
        for i, h in reversed(list(enumerate(st.history))):
            j = st.job(h["job_id"]) or {"title": h["job_id"]}
            self.tree.insert("", "end", iid=str(i), values=(
                generator.parse_date(h["date"]).strftime("%d/%m/%Y"), h.get("permit_no") or "",
                j["title"], generator.issued_to_text(st, h["crew"]), h.get("file", "")))
        self.app.status.right.set(T("History: {n} permits", n=len(st.history)))

    def _sel(self):
        return sorted((int(i) for i in self.tree.selection()), reverse=True)

    def open_file(self):
        st = self.app.store
        for i in self._sel()[:1]:
            path = os.path.join(st.settings.get("output_dir", ""), st.history[i].get("file", ""))
            if os.path.isfile(path):
                open_path(path)
            else:
                messagebox.showinfo(app_title(), f"{T('File not found:')}\n{path}", parent=self)

    def open_folder(self):
        folder = self.app.store.settings.get("output_dir")
        if folder and os.path.isdir(folder):
            open_path(folder)

    def print_files(self):
        """Send the files of the selected permits to the default printer (test)."""
        st = self.app.store
        sel = sorted(self._sel())
        if not sel:
            messagebox.showinfo(app_title(), T("Select permits in the list."), parent=self)
            return
        folder = st.settings.get("output_dir", "")
        paths = [os.path.join(folder, st.history[i].get("file", "")) for i in sel]
        missing = [p for p in paths if not os.path.isfile(p)]
        paths = [p for p in paths if os.path.isfile(p)]
        if not paths:
            messagebox.showinfo(app_title(), f"{T('File not found:')}\n" + "\n".join(missing[:5]),
                                parent=self)
            return
        if not printing.can_print():
            messagebox.showwarning(app_title(), T("Printing is not available on this computer."),
                                   parent=self)
            return
        if not messagebox.askyesno(app_title(), T("Print {n} files on the default printer?\n"
                                                  "(test function: Word opens and prints each file)",
                                                  n=len(paths)), parent=self):
            return
        done = 0
        for p in paths:
            try:
                printing.print_file(p)
                done += 1
            except OSError as e:
                messagebox.showerror(app_title(), f"{os.path.basename(p)}:\n{e}", parent=self)
                break
        self.app.status.set(T("{n} files sent to the printer", n=done))

    def recreate(self):
        """Write the selected permits again with the current template (same No., same file)."""
        sel = self._sel()
        if not sel:
            messagebox.showinfo(app_title(), T("Select permits in the list."), parent=self)
            return
        if not self.app.ensure_output_dir() or not self.app.check_template(self):
            return
        if not messagebox.askyesno(app_title(), T("Write {n} files again with the same numbers?\n"
                                                  "The old files are overwritten.", n=len(sel)),
                                   parent=self):
            return
        entries = [self.app.store.history[i] for i in sorted(sel)]

        def work(progress, cancelled):
            return docgen.rewrite_files(self.app.store, entries, progress=progress,
                                        cancelled=cancelled)

        def done(result, error, cancelled):
            if error is not None:  # e.g. the file is open in Word
                messagebox.showerror(app_title(), f"{T('Could not create files:')}\n{error}",
                                     parent=self)
                return
            show_write_result(self.app, self, *result)

        run_with_progress(self.app, self, app_title(), T("Creating permit files..."), work, done)

    def delete(self):
        sel = self._sel()
        if not sel or not messagebox.askyesno(
                app_title(), T("Delete {n} entries from history?\n(Files are not deleted.)",
                               n=len(sel)), parent=self):
            return
        for i in sel:
            del self.app.store.history[i]
        storage.save("history", self.app.store.history)
        self.show()


# ======================================================================
# Data editors
# ======================================================================

def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "item"


def text_match(words, *texts):
    """Every word of the filter appears somewhere in the texts (case-insensitive)."""
    hay = " ".join(str(t) for t in texts).lower()
    return all(w in hay for w in words)


class ListEditor(tk.Toplevel):
    """Generic editor: sorted, filterable list of records on the left, fields on the right.

    field kinds: str, int, bool, codes (comma separated list), range (min-max), rank
    """

    def __init__(self, app, title, records, fields, label, id_from, on_save, hint="",
                 validate=None, new_record=None, sort_key=None):
        super().__init__(app)
        self.new_record = new_record  # callable returning field values of a "New" record
        self.sort_key = sort_key or (lambda r: label(r).lower())
        self.title(title)
        self.configure(bg=BG)
        self.transient(app)
        self.app = app
        self.records = copy.deepcopy(records)
        self.fields, self.label, self.id_from, self.on_save = fields, label, id_from, on_save
        self.validate = validate
        self.current = None  # index in self.records
        self.view = []       # record indices shown in the list, in list order

        left = win95.group(self, T("Records"))
        left.pack(side="left", fill="both", padx=6, pady=6)
        top = tk.Frame(left, bg=BG)
        top.pack(fill="x", pady=(0, 4))
        tk.Label(top, text=T("Filter:")).pack(side="left")
        self.filter = tk.Entry(top, width=24)
        self.filter.pack(side="left", padx=4, fill="x", expand=True)
        self.filter.bind("<KeyRelease>", lambda e: self._refresh_view())
        win95.button(top, "x", self._clear_filter, width=2).pack(side="left")
        self.count = tk.Label(left, anchor="w", fg=win95.DARK)
        self.count.pack(fill="x")
        lf = tk.Frame(left, bg=BG)
        lf.pack(fill="both", expand=True)
        self.lb = tk.Listbox(lf, width=40, height=24, exportselection=False, activestyle="none")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.lb.bind("<<ListboxSelect>>", self._select)
        self.lb.bind("<Delete>", lambda e: self.delete())
        b = tk.Frame(left, bg=BG)
        b.pack(fill="x", pady=(4, 0))
        win95.button(b, T("New"), self.new, width=8).pack(side="left")
        win95.button(b, T("Copy"), self.duplicate, width=8).pack(side="left", padx=4)
        win95.button(b, T("Delete"), self.delete, width=8).pack(side="left")

        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        form = win95.group(right, T("Details"))
        form.pack(fill="both", expand=True)
        self.widgets = {}
        ranks = [r["code"] for r in app.store.ranks]
        for row, (key, text, kind) in enumerate(fields):
            tk.Label(form, text=T(text) + ":").grid(row=row, column=0, sticky="nw", pady=2)
            if kind == "bool":
                v = tk.BooleanVar()
                w = tk.Checkbutton(form, variable=v)
                w.var = v
            elif kind == "rank":
                w = ttk.Combobox(form, values=ranks, width=12)
            else:
                w = tk.Entry(form, width=56 if kind in ("str", "codes") else 12)
            w.grid(row=row, column=1, sticky="w", padx=4, pady=2)
            self.widgets[key] = (w, kind)
        if hint:
            tk.Label(form, text=T(hint), justify="left", fg=win95.DARK, wraplength=440
                     ).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(8, 0))
        bar = tk.Frame(right, bg=BG)
        bar.pack(fill="x", pady=(8, 0))
        win95.button(bar, T("Cancel"), self.destroy).pack(side="right", padx=4)
        win95.button(bar, T("OK"), self.ok).pack(side="right", padx=4)
        win95.button(bar, T("Apply"), self.apply).pack(side="left")
        # Ctrl+... keys, see App._on_ctrl
        self.hotkeys = {"f": self.focus_filter, "n": self.new, "s": self.ok}

        self._refresh_view()
        if self.view:
            self._show(self.view[0])
        win95.center(self, app)
        self.grab_set()

    # --- list ---
    def _refresh_view(self):
        """Sort and filter the list; keep the current record highlighted."""
        words = self.filter.get().lower().split()
        idx = [i for i, r in enumerate(self.records)
               if not words or text_match(words, self.label(r), *r.values())]
        idx.sort(key=lambda i: self.sort_key(self.records[i]))
        self.view = idx
        self.lb.delete(0, "end")
        for i in idx:
            self.lb.insert("end", self.label(self.records[i]))
        self.count.config(text=T("{n} of {total}", n=len(idx), total=len(self.records)))
        if self.current in self.view:
            self._highlight(self.current)

    def _clear_filter(self):
        self.filter.delete(0, "end")
        self._refresh_view()

    def focus_filter(self):
        self.filter.focus_set()
        self.filter.select_range(0, "end")

    def _highlight(self, rec_index):
        """Exactly one highlighted row (Listbox.selection_set alone adds to the selection)."""
        self.lb.selection_clear(0, "end")
        if rec_index in self.view:
            row = self.view.index(rec_index)
            self.lb.selection_set(row)
            self.lb.activate(row)
            self.lb.see(row)

    def _select(self, _e=None):
        sel = self.lb.curselection()
        if not sel or sel[0] >= len(self.view):
            return
        target = self.view[sel[0]]
        if self.current is not None and self.current != target:
            if not self.apply():
                self._highlight(self.current)
                return
        self._show(target)

    def _show(self, rec_index):
        self.current = rec_index
        self._highlight(rec_index)
        rec = self.records[rec_index]
        for key, (w, kind) in self.widgets.items():
            val = rec.get(key)
            if kind == "bool":
                w.var.set(bool(val) if val is not None else True)
                continue
            if kind == "codes":
                text = ", ".join(val or [])
            elif kind == "range":
                text = f"{val[0]}-{val[1]}" if val else "0-0"
            else:
                text = "" if val is None else str(val)
            if kind == "rank":
                w.set(text)
            else:
                w.delete(0, "end")
                w.insert(0, text)

    # --- editing ---
    def _read(self):
        rec = {}
        for key, (w, kind) in self.widgets.items():
            if kind == "bool":
                rec[key] = w.var.get()
                continue
            text = w.get().strip()
            if kind == "int":
                try:
                    rec[key] = int(text)
                except ValueError:
                    raise ValueError(T("'{key}' must be a number", key=key)) from None
            elif kind == "codes":
                rec[key] = [c.strip() for c in text.replace(";", ",").split(",") if c.strip()]
            elif kind == "range":
                m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", text) or re.fullmatch(r"(\d+)()", text)
                if not m:
                    raise ValueError(T("'{key}' must look like 0-2", key=key))
                lo = int(m.group(1))
                hi = int(m.group(2) or lo)
                rec[key] = [min(lo, hi), max(lo, hi)]
            else:
                rec[key] = text
        return rec

    def apply(self):
        if self.current is None:
            return True
        try:
            rec = self._read()
        except ValueError as e:
            messagebox.showwarning(self.title(), str(e), parent=self)
            return False
        if "id" in rec and not rec["id"]:
            rec["id"] = slug(self.id_from(rec))
        if "id" in rec:
            ids = [r.get("id") for i, r in enumerate(self.records) if i != self.current]
            base, n = rec["id"], 2
            while rec["id"] in ids:
                rec["id"] = f"{base}_{n}"
                n += 1
        if "code" in rec and not rec["code"]:
            messagebox.showwarning(self.title(), T("Code must not be empty."), parent=self)
            return False
        old = self.records[self.current]
        changed = any(old.get(k) != v for k, v in rec.items())
        old.update(rec)
        if changed:
            self._refresh_view()  # the record may move to its place in the sorted list
        if changed and self.validate:
            notes = self.validate(old)
            if notes:
                messagebox.showwarning(self.title(), "\n\n".join(notes), parent=self)
        return True

    def _add(self, rec):
        if not self.apply():
            return
        self.records.append(rec)
        if self.filter.get():
            self.filter.delete(0, "end")  # the new record must be visible
        self.current = len(self.records) - 1
        self._refresh_view()
        self._show(self.current)
        first = next((w for w, kind in self.widgets.values() if kind == "str"), None)
        if first is not None:
            first.focus_set()

    def new(self):
        rec = {}
        for key, _t, kind in self.fields:
            rec[key] = {"bool": True, "codes": [], "range": [0, 0], "int": 0}.get(kind, "")
        if self.new_record:
            rec.update(self.new_record(self.records))
        self._add(rec)

    def duplicate(self):
        if self.current is None:
            return
        rec = copy.deepcopy(self.records[self.current])
        if "id" in rec:
            rec["id"] = ""
        self._add(rec)
        self.apply()

    def delete(self):
        if self.current is None:
            return
        if not messagebox.askyesno(self.title(), T("Delete this record?"), parent=self):
            return
        pos = self.view.index(self.current) if self.current in self.view else 0
        del self.records[self.current]
        self.current = None
        self._refresh_view()
        if self.view:
            self._show(self.view[min(pos, len(self.view) - 1)])

    def ok(self):
        if not self.apply():
            return
        self.on_save(sorted(self.records, key=self.sort_key))
        self.destroy()


# ======================================================================
# Settings
# ======================================================================

class SettingsDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        st = app.store
        s = st.settings
        self.title(T("Settings"))
        self.configure(bg=BG)
        self.transient(app)
        self.resizable(False, False)
        self.entries = {}
        self.code_entries = {}

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        # --- General ---
        g = self._page(nb, T("General"))
        tk.Label(g, text=T("Language:")).grid(row=0, column=0, sticky="w", pady=3)
        self.lang_map = {v: k for k, v in i18n.LANGUAGES.items()}
        self.lang = ttk.Combobox(g, state="readonly", values=list(self.lang_map), width=14)
        self.lang.set(i18n.LANGUAGES.get(s.get("language", "en"), "English"))
        self.lang.grid(row=0, column=1, sticky="w", padx=4)
        tk.Label(g, text=T("Interface font size:")).grid(row=1, column=0, sticky="w", pady=3)
        self.ui_font = ttk.Combobox(g, state="readonly", values=["8", "9", "10", "11"], width=5)
        self.ui_font.set(str(s.get("ui_font_size", 8)))
        self.ui_font.grid(row=1, column=1, sticky="w", padx=4)
        self._entry(g, 2, "ship_name", T("Ship name:"), 30)
        tk.Label(g, text=T("A.O. (Authorizing Officer):")).grid(row=3, column=0, sticky="w", pady=3)
        self.ao_map = {member_label(st, m): m["id"] for m in st.crew}
        self.ao = ttk.Combobox(g, state="readonly", values=list(self.ao_map), width=34)
        self.ao.grid(row=3, column=1, sticky="w", padx=4)
        for label, mid in self.ao_map.items():
            if mid == s.get("ao_id"):
                self.ao.set(label)
        self.sounds = tk.BooleanVar(value=bool(s.get("sounds", True)))
        tk.Checkbutton(g, text=T("Play sounds"), variable=self.sounds
                       ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        win95.button(g, T("Test"), lambda: sound.play("tada") if self.sounds.get() else None,
                     width=8).grid(row=4, column=1, sticky="e")
        self.splash = tk.BooleanVar(value=bool(s.get("splash", True)))
        tk.Checkbutton(g, text=T("Show the splash screen at start"), variable=self.splash
                       ).grid(row=5, column=0, columnspan=2, sticky="w")

        # --- Files ---
        f = self._page(nb, T("Files"))
        self.out = self._path_row(f, 0, T("Output folder:"), s.get("output_dir", ""), self._pick_out)
        self.tpl = self._path_row(f, 1, T("Word template:"), s.get("template_path", ""), self._pick_tpl)
        tk.Label(f, text=T("(empty = built-in template)"), fg=win95.DARK
                 ).grid(row=2, column=1, columnspan=2, sticky="w")
        self._entry(f, 3, "filename_pattern", T("File name pattern:"), 30)
        self._entry(f, 4, "filename_date_format", T("Date format in file name:"), 12)
        tk.Label(f, text=T("Fields: {date} {title} {ra} {no}.  Date: %Y-%m-%d, %d.%m.%Y ..."),
                 fg=win95.DARK).grid(row=5, column=0, columnspan=3, sticky="w")
        self.example = tk.Label(f, anchor="w")
        self.example.grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 0))
        for k in ("filename_pattern", "filename_date_format"):
            self.entries[k].bind("<KeyRelease>", lambda e: self._update_example())
        self.open_after = tk.BooleanVar(value=bool(s.get("open_folder_after", True)))
        tk.Checkbutton(f, text=T("Open the folder after creating files"), variable=self.open_after
                       ).grid(row=7, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self._update_example()

        # --- Permit ---
        p = self._page(nb, T("Permit"))
        self._entry(p, 0, "time_issue", T("Time permit issued (5):"), 8)
        self._entry(p, 1, "time_transfer", T("Time of transfer (6):"), 8)
        self._entry(p, 2, "time_close", T("Time permit closed (7):"), 8)
        tk.Label(p, text=T("Consecutive Permit No:")).grid(row=3, column=0, sticky="nw", pady=(6, 0))
        self.numbering = tk.StringVar(value=s.get("permit_numbering", "day"))
        nums = tk.Frame(p, bg=BG)
        nums.grid(row=3, column=1, sticky="w", pady=(6, 0))
        for value, text in (("day", "Day of the year: 285, or 285-1, 285-2 for several a day"),
                            ("sequential", "Running number (next number below)"),
                            ("blank", "Leave empty (written by pen)")):
            tk.Radiobutton(nums, text=T(text), variable=self.numbering, value=value
                           ).pack(anchor="w")
        self._entry(p, 4, "next_permit_no", T("Next permit number:"), 8)
        tk.Label(p, text=T("Sections 2 and 3, tick the boxes in the file:")
                 ).grid(row=5, column=0, sticky="w", pady=(8, 0))
        ticks = tk.Frame(p, bg=BG)
        ticks.grid(row=5, column=1, sticky="w", pady=(8, 0))
        self.tick_ao = tk.BooleanVar(value=bool(s.get("tick_ao", True)))
        self.tick_pc = tk.BooleanVar(value=bool(s.get("tick_pc", True)))
        tk.Checkbutton(ticks, text="A.O.", variable=self.tick_ao).pack(side="left")
        tk.Checkbutton(ticks, text="P.C.", variable=self.tick_pc).pack(side="left", padx=8)

        # --- Generation ---
        gen = self._page(nb, T("Generation"))
        self._entry(gen, 0, "permits_per_day", T("Permits per day:"), 8)
        self._entry(gen, 1, "no_repeat_days", T("Do not repeat a job within (days):"), 8)
        tk.Label(gen, text=T("Days without permits:")).grid(row=2, column=0, sticky="nw", pady=3)
        days = tk.Frame(gen, bg=BG)
        days.grid(row=2, column=1, sticky="w")
        skip = set(s.get("skip_weekdays") or [])
        self.skip_vars = []
        for i, d in enumerate(WEEKDAYS):
            v = tk.BooleanVar(value=i in skip)
            tk.Checkbutton(days, text=T(d), variable=v).pack(side="left")
            self.skip_vars.append(v)
        self._codes(gen, 3, "pc_supervisor_ranks",
                    T("P.C. when the job lead cannot be P.C. (take turns):"))
        self._codes(gen, 4, "loto_preferred_ranks", T("LOTO is applied first of all by:"))
        tk.Label(gen, text=T("Who may be P.C. or apply LOTO is set per rank in Data > Ranks."),
                 fg=win95.DARK).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # --- Print ---
        pr = self._page(nb, T("Print"))
        self.fit = tk.BooleanVar(value=bool(s.get("fit_one_line", True)))
        tk.Checkbutton(pr, text=T("Fit long text on one line (smaller font)"), variable=self.fit
                       ).grid(row=0, column=0, columnspan=2, sticky="w")
        self._entry(pr, 1, "min_font_size", T("Smallest font size, pt:"), 6)
        tk.Label(pr, text=T("The form must stay on one A4 page. Values are printed in Times New "
                            "Roman 9 pt;\na value that does not fit its line is printed smaller "
                            "instead of wrapping."), justify="left", fg=win95.DARK
                 ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        win95.button(bar, T("Defaults"), self.defaults).pack(side="left")
        win95.button(bar, T("Cancel"), self.destroy).pack(side="right", padx=4)
        win95.button(bar, T("OK"), self.ok).pack(side="right", padx=4)
        win95.center(self, app)
        self.grab_set()

    # --- helpers ---
    def _page(self, nb, title):
        outer = tk.Frame(nb, bg=BG)
        nb.add(outer, text=title)
        inner = tk.Frame(outer, bg=BG, padx=10, pady=10)
        inner.pack(fill="both", expand=True)
        return inner

    def _entry(self, master, row, key, text, width):
        tk.Label(master, text=text).grid(row=row, column=0, sticky="w", pady=3)
        e = tk.Entry(master, width=width)
        e.insert(0, str(self.app.store.settings.get(key, "")))
        e.grid(row=row, column=1, sticky="w", padx=4)
        self.entries[key] = e
        return e

    def _codes(self, master, row, key, text):
        tk.Label(master, text=text).grid(row=row, column=0, sticky="w", pady=3)
        e = tk.Entry(master, width=20)
        e.insert(0, ", ".join(self.app.store.settings.get(key) or []))
        e.grid(row=row, column=1, sticky="w", padx=4)
        self.code_entries[key] = e

    def _path_row(self, master, row, text, value, cmd):
        tk.Label(master, text=text).grid(row=row, column=0, sticky="w", pady=3)
        e = tk.Entry(master, width=52)
        e.insert(0, value)
        e.grid(row=row, column=1, sticky="w", padx=4)
        win95.button(master, T("Browse..."), cmd, width=10).grid(row=row, column=2)
        return e

    def _update_example(self):
        try:
            name = self.entries["filename_pattern"].get().format(
                date=dt.date.today().strftime(self.entries["filename_date_format"].get() or "%Y-%m-%d"),
                title="ME Fuel Valves Overhaul", ra="RA-001", no="15")
            self.example.config(text=f"{T('Example:')} {name}.docx", fg="black")
        except Exception as e:  # noqa: BLE001 - shown to the user
            self.example.config(text=str(e), fg="#800000")

    def _pick_out(self):
        d = filedialog.askdirectory(parent=self, initialdir=self.out.get() or None)
        if d:
            self.out.delete(0, "end")
            self.out.insert(0, d)

    def _pick_tpl(self):
        f = filedialog.askopenfilename(parent=self, filetypes=[("Word", "*.docx")])
        if f:
            self.tpl.delete(0, "end")
            self.tpl.insert(0, f)

    def defaults(self):
        if not messagebox.askyesno(T("Settings"), T("Reset all settings to defaults "
                                                    "(folders are kept)?"), parent=self):
            return
        s = self.app.store.settings
        keep = {k: s.get(k) for k in ("output_dir", "template_path", "next_permit_no", "ao_id",
                                      "ship_name")}
        s.clear()
        s.update(storage.DEFAULT_SETTINGS)
        s.update(keep)
        storage.save("settings", s)
        self.destroy()
        self.app.rebuild()

    def ok(self):
        s = self.app.store.settings
        new = {k: e.get().strip() for k, e in self.entries.items()}
        warn = lambda text: messagebox.showwarning(T("Settings"), text, parent=self)  # noqa: E731
        try:
            for k in ("permits_per_day", "no_repeat_days", "next_permit_no"):
                new[k] = int(new[k])
        except ValueError:
            warn(T("Numbers expected for per day / repeat / permit no."))
            return
        try:
            new["min_font_size"] = float(new["min_font_size"].replace(",", "."))
            if not 5 <= new["min_font_size"] <= 9:
                raise ValueError
        except ValueError:
            warn(T("Smallest font size must be a number between 5 and 9."))
            return
        for k in ("time_issue", "time_transfer", "time_close"):
            if not re.fullmatch(r"\d{1,2}:\d{2}", new[k]):
                warn(T("Time must look like 08:00 ({key}).", key=k))
                return
        try:
            dt.date.today().strftime(new["filename_date_format"])
            new["filename_pattern"].format(date="", title="", ra="", no="")
        except Exception as e:  # noqa: BLE001 - any bad pattern: {x}, {date.year}, {0} ...
            warn(T("Wrong file name pattern: {e}", e=e))
            return
        tpl = self.tpl.get().strip()
        if tpl and not os.path.isfile(tpl):
            warn(T("Template not found: {path}", path=tpl))
            return
        st = self.app.store
        codes = {}
        for key, e in self.code_entries.items():
            codes[key] = [c.strip().upper() for c in e.get().replace(";", ",").split(",") if c.strip()]
        known = {r["code"].upper(): r for r in st.ranks}
        sup = codes.get("pc_supervisor_ranks", [])
        bad = [c for c in sup if c not in known or not known[c].get("can_pc")]
        if not sup or bad:
            warn(T("'P.C. when the job lead cannot be P.C.' needs ranks that may be P.C.: {ok}",
                   ok=", ".join(r["code"] for r in st.ranks if r.get("can_pc"))))
            return
        bad = [c for c in codes.get("loto_preferred_ranks", []) if c not in known]
        if bad:
            warn(T("Unknown rank: {codes}", codes=", ".join(bad)))
            return
        codes = {k: [known[c]["code"] for c in v] for k, v in codes.items()}
        old_look = (s.get("language"), s.get("ui_font_size"))
        s.update(new)
        s["output_dir"] = self.out.get().strip()
        s["template_path"] = tpl
        s["permit_numbering"] = self.numbering.get()
        s["tick_ao"] = self.tick_ao.get()
        s["tick_pc"] = self.tick_pc.get()
        s.update(codes)
        s["open_folder_after"] = self.open_after.get()
        s["fit_one_line"] = self.fit.get()
        s["skip_weekdays"] = [i for i, v in enumerate(self.skip_vars) if v.get()]
        s["language"] = self.lang_map.get(self.lang.get(), "en")
        s["ui_font_size"] = int(self.ui_font.get())
        s["sounds"] = self.sounds.get()
        s["splash"] = self.splash.get()
        sound.enabled = s["sounds"]
        s["ao_id"] = self.ao_map.get(self.ao.get(), s.get("ao_id"))
        storage.save("settings", s)
        self.destroy()
        if (s["language"], s["ui_font_size"]) != old_look:
            self.app.rebuild()
        else:
            self.app.refresh()


# ======================================================================
# Main window
# ======================================================================

SPLASH_STEPS = [(0.0, "Loading settings..."), (0.25, "Loading crew list..."),
                (0.5, "Loading jobs..."), (0.75, "Checking Word template..."),
                (0.95, "Starting...")]


class App(tk.Tk):
    def __init__(self, splash=None):
        super().__init__()
        self.withdraw()  # shown after the splash screen
        self.store = storage.Store()
        s = self.store.settings
        sound.enabled = bool(s.get("sounds", True))
        i18n.set_language(s.get("language", "en"))
        win95.apply_style(self, int(s.get("ui_font_size", 8)))
        self.geometry("1100x680")
        self.minsize(900, 600)
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self._set_icon()
        show = s.get("splash", True) if splash is None else splash
        sound.play("startup")
        if show:
            win95.Splash(self, "Permit to Work", T("Generator  -  Engine Department"),
                         T("Version {v}", v=__version__),
                         [(at, T(text)) for at, text in SPLASH_STEPS],
                         icon=self.icons.get(64), duration=2000, on_done=self._show,
                         footer=f"\u00a9 {dt.date.today().year}  Daily Permit to Work")
            self.after(60, self.build)  # build the hidden window while the splash runs
        else:
            self.build()
            self._show()

    # --- keyboard ---
    def _bind_keys(self):
        self.bind_all("<Control-KeyPress>", self._on_ctrl)  # replaces: no double calls after rebuild
        labels = {"cut": T("Cut"), "copy": T("Copy (clipboard)"), "paste": T("Paste"),
                  "all": T("Select all")}
        self.bind_all("<Button-3>", lambda e: win95.context_menu(e, labels))
        self.bind("<F1>", lambda e: self.shortcuts())
        self.bind("<F5>", lambda e: self._on_tab(0, self.auto_tab.generate))

    def _on_tab(self, tab, action):
        self.notebook.select(tab)
        action()
        return "break"

    def _print(self):
        self.notebook.select(2)
        self.history_tab.print_files()

    def _on_ctrl(self, event):
        """Ctrl+letter, the same key with the Russian layout (Ctrl+Ф = Ctrl+A)."""
        key = win95.key_letter(event)
        if not key:
            return None
        w = self.focus_get()
        if key in ("c", "v", "x"):
            return "break" if win95.edit_key(w, key, event.keysym) else None
        if key == "a":
            return "break" if win95.select_all(w) else None
        top = w.winfo_toplevel() if w is not None else self
        if top is not self:
            action = getattr(top, "hotkeys", {}).get(key)
            if action:
                action()
                return "break"
            return None
        tab = self.notebook.index("current")
        actions = {
            "g": lambda: self._on_tab(0, self.auto_tab.generate),
            "r": lambda: self._on_tab(0, self.auto_tab.reroll),
            "e": lambda: self._on_tab(0, self.auto_tab.edit),
            "s": (self.auto_tab.create if tab == 0 else self.manual_tab.create if tab == 1
                  else lambda: None),
            "f": lambda: self._on_tab(1, self.manual_tab.form.focus_filter),
            "p": self._print,
            "o": self.history_tab.open_folder,
            "q": self.quit_app,
            "1": lambda: self.notebook.select(0),
            "2": lambda: self.notebook.select(1),
            "3": lambda: self.notebook.select(2),
        }
        if key in actions:
            actions[key]()
            return "break"
        return None

    def shortcuts(self):
        messagebox.showinfo(T("Keyboard shortcuts"), T(
            "Ctrl+A - select all (lists, text fields)\n"
            "Ctrl+C / Ctrl+V / Ctrl+X - copy / paste / cut (lists: rows for Excel)\n"
            "Right mouse button - Copy / Paste menu\n"
            "Shift / Ctrl + click - select several rows\n"
            "F5 or Ctrl+G - generate the plan\n"
            "Ctrl+R - reroll selected rows\n"
            "Enter, F2 or Ctrl+E - edit the selected row\n"
            "Delete - remove the selected rows\n"
            "Ctrl+S - create files (Auto) / create file (Manual)\n"
            "Ctrl+F - job filter (Manual) / filter in the editors\n"
            "Ctrl+N - new record (editors), Ctrl+S - OK (editors)\n"
            "Ctrl+P - print selected files (History, test)\n"
            "Ctrl+O - open the output folder\n"
            "Ctrl+1 / 2 / 3 - Auto generate / Manual / History\n"
            "Ctrl+Q - exit"), parent=self)

    def _set_icon(self):
        """Window / taskbar icon (icons/ptw_*.png, icons/ptw.ico for Windows)."""
        self.icons = {}
        for size in (16, 32, 48, 64):
            try:
                self.icons[size] = tk.PhotoImage(file=storage.resource("icons", f"ptw_{size}.png"))
            except tk.TclError:
                pass
        if self.icons:
            self.iconphoto(True, *self.icons.values())
        if sys.platform.startswith("win"):
            try:
                self.iconbitmap(default=storage.resource("icons", "ptw.ico"))
            except tk.TclError:
                pass

    def _show(self):
        self.deiconify()
        self.lift()
        self.after(200, self._first_start)

    def quit_app(self):
        """Exit with the closing sound (the window disappears first)."""
        self.withdraw()
        self.update()
        sound.play("shutdown", wait=True)
        self.destroy()

    def build(self):
        s = self.store.settings
        i18n.set_language(s.get("language", "en"))
        win95.apply_style(self, int(s.get("ui_font_size", 8)))
        self.title(app_title())
        self._menu()
        win95.Banner(self, app_title(), T("Daily Permit to Work, Engine Department")).pack(fill="x")
        self.status = win95.StatusBar(self)
        self.status.pack(side="bottom", fill="x")
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=6)
        self.auto_tab = AutoTab(self.notebook, self)
        self.manual_tab = ManualTab(self.notebook, self)
        self.history_tab = HistoryTab(self.notebook, self)
        self.notebook.add(self.auto_tab, text=T("Auto generate"))
        self.notebook.add(self.manual_tab, text=T("Manual"))
        self.notebook.add(self.history_tab, text=T("History"))
        self.status.set(T("Ready. Choose the period and press 'Generate'."))
        self._bind_keys()

    def rebuild(self):
        """Recreate the window after a language or font change, keeping the plan."""
        plan = self.auto_tab.plan
        rng = (self.auto_tab.cal_from.selection_get(), self.auto_tab.cal_to.selection_get())
        tab = self.notebook.index("current")
        for w in self.winfo_children():
            w.destroy()
        self.build()
        self.auto_tab.plan = plan
        self.auto_tab.set_range(*rng)
        self.auto_tab.show()
        self.notebook.select(tab)

    def _menu(self):
        m = tk.Menu(self)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label=T("Open output folder"), accelerator="Ctrl+O",
                      command=lambda: self.history_tab.open_folder())
        f.add_command(label=T("Print selected files (test)"), accelerator="Ctrl+P",
                      command=self._print)
        f.add_separator()
        f.add_command(label=T("Exit"), accelerator="Ctrl+Q", command=self.quit_app)
        m.add_cascade(label=T("File"), menu=f, underline=0)
        d = tk.Menu(m, tearoff=0)
        d.add_command(label=T("Jobs..."), command=self.edit_jobs)
        d.add_command(label=T("Crew..."), command=self.edit_crew)
        d.add_command(label=T("Ranks..."), command=self.edit_ranks)
        d.add_separator()
        d.add_command(label=T("Load default jobs list..."), command=self.load_default_jobs)
        m.add_cascade(label=T("Data"), menu=d, underline=0)
        o = tk.Menu(m, tearoff=0)
        o.add_command(label=T("Settings..."), command=lambda: SettingsDialog(self))
        m.add_cascade(label=T("Options"), menu=o, underline=0)
        h = tk.Menu(m, tearoff=0)
        h.add_command(label=T("Keyboard shortcuts"), accelerator="F1", command=self.shortcuts)
        h.add_command(label=T("Check for updates"), command=self.check_updates)
        h.add_command(label=T("Open log folder"), command=lambda: open_path(ptwlog.LOG_DIR))
        h.add_separator()
        h.add_command(label=T("About"), command=self.about)
        m.add_cascade(label=T("Help"), menu=h, underline=0)
        self.config(menu=m)

    def _first_start(self):
        s = self.store.settings
        if not s.get("output_dir") or not s.get("ship_name"):
            messagebox.showinfo(app_title(), T("Welcome!\n\nPlease enter the ship name and choose "
                                               "the folder where permits will be saved "
                                               "(Options > Settings)."), parent=self)
            SettingsDialog(self)

    def check_template(self, parent):
        """Warn (once per session) when the Word template lacks fields of this version."""
        tpl = storage.template_path(self.store.settings)
        missing = docgen.template_missing(tpl)
        if not missing or getattr(self, "_tpl_warned", None) == (tpl, tuple(missing)):
            return True
        self._tpl_warned = (tpl, tuple(missing))
        return messagebox.askyesno(
            app_title(), T("The Word template has no fields for: {fields}.\n{path}\n\n"
                           "These values will not be printed. Use the built-in template "
                           "(Options > Settings > Files, Word template empty).\n\n"
                           "Create the files anyway?",
                           fields=", ".join("{{%s}}" % k for k in missing), path=tpl),
            parent=parent)

    def ensure_output_dir(self):
        if self.store.settings.get("output_dir"):
            return True
        messagebox.showwarning(app_title(), T("Output folder is not set."), parent=self)
        SettingsDialog(self)
        return bool(self.store.settings.get("output_dir"))

    def refresh(self):
        self.manual_tab.form.refresh()
        self.auto_tab.show()
        self.history_tab.show()

    # --- editors ---
    def _saver(self, name):
        def save(records):
            setattr(self.store, name, records)
            storage.save(name, records)
            self.refresh()
        return save

    def edit_jobs(self):
        fields = [("id", "ID", "str"), ("title", "Title (file name)", "str"),
                  ("location", "Location", "str"), ("plant", "Plant / Equipment", "str"),
                  ("work", "Work to be done", "str"), ("ra_no", "Risk Assessment No", "str"),
                  ("lead_ranks", "Responsible ranks", "codes"),
                  ("officer_ranks", "Extra officers ranks", "codes"),
                  ("officers", "Extra officers count", "range"),
                  ("rating_ranks", "Ratings ranks", "codes"),
                  ("ratings", "Ratings count", "range"),
                  ("pc_ranks", "P.C. ranks (if the lead cannot be P.C.)", "codes"),
                  ("group", "Group (same filter / purifier: not on close days)", "str"),
                  ("loto", "LOTO usually needed (hint only)", "bool"), ("active", "Active", "bool")]
        hint = ("Responsible ranks: one of them leads the job, e.g. 2E. If the lead cannot be P.C.\n"
                "(4E, 5E), a P.C. from 'P.C. ranks' is added - empty = Settings > Generation.\n"
                "Counts are 'min-max', e.g. 0-1 or 1-2. Ranks are comma separated: MM, FITTR.\n"
                "Keep Location / Plant / Work short - the form has one line for each.")

        def validate(j):
            return fit_warnings(self.store, {"LOCATION": j.get("location", ""),
                                             "PLANT": j.get("plant", ""),
                                             "WORK": j.get("work", ""),
                                             "RA_NO": j.get("ra_no", "")})
        ListEditor(self, T("Jobs"), self.store.jobs, fields,
                   lambda j: f"{','.join(j.get('lead_ranks', []))[:7]:<8} {j.get('title', '')}",
                   lambda j: j.get("title", ""), self._saver("jobs"), hint, validate,
                   new_record=lambda recs: {"loto": False, "ratings": [1, 1]},
                   sort_key=lambda j: (self.store.rank((j.get("lead_ranks") or [""])[0])["order"],
                                       j.get("title", "").lower()))

    def edit_crew(self):
        fields = [("id", "ID", "str"), ("rank", "Rank", "rank"),
                  ("first_name", "First name", "str"), ("last_name", "Last name", "str"),
                  ("title", "Rank title (optional)", "str"), ("active", "On board", "bool")]
        hint = ("Rank title overrides the rank name in signatures, e.g. 'Asst. Second Engineer'.\n"
                "Untick 'On board' when a crew member signs off - history is kept.")

        def validate(m):
            if not m.get("first_name"):
                return []
            sign = f"{m.get('title') or self.store.rank(m.get('rank'))['full']} / " \
                   f"{m['first_name']} {m.get('last_name', '')}"
            return fit_warnings(self.store, {"PC": sign})
        ListEditor(self, T("Crew"), self.store.crew, fields,
                   lambda m: f"{m.get('rank', ''):<6} {m.get('first_name', '')} {m.get('last_name', '')}"
                   + ("" if m.get("active", True) else "  " + T("(off)")),
                   lambda m: f"{m.get('last_name', '')} {m.get('first_name', '')}",
                   self._saver("crew"), hint, validate,
                   sort_key=lambda m: (self.store.rank(m.get("rank", ""))["order"],
                                       m.get("last_name", "").lower()))

    def edit_ranks(self):
        fields = [("code", "Code", "str"), ("short", "Short (issued to)", "str"),
                  ("full", "Full (signatures)", "str"), ("officer", "Officer", "bool"),
                  ("can_pc", "Can sign as P.C. (sections 5-7)", "bool"),
                  ("can_loto", "Can apply LOTO", "bool"),
                  ("order", "Order (seniority)", "int")]
        # a new rank may NOT sign as P.C. or apply LOTO until you tick it (PSC)
        ListEditor(self, T("Ranks"), self.store.ranks, fields,
                   lambda r: f"{r.get('code', ''):<6} {r.get('full', '')}",
                   lambda r: r.get("code", ""), self._saver("ranks"),
                   new_record=lambda recs: {"officer": False, "can_pc": False, "can_loto": False,
                                            "order": max([r.get("order", 0) for r in recs] or [0]) + 1},
                   sort_key=lambda r: (r.get("order", 99), r.get("code", "")))

    def load_default_jobs(self):
        try:
            defaults = storage.default_records("jobs")
        except OSError as e:
            messagebox.showerror(app_title(), str(e), parent=self)
            return
        ans = messagebox.askyesnocancel(
            app_title(), T("Default list: {n} jobs.\n\nYes - replace your list with it\n"
                           "No - only add the jobs you do not have yet", n=len(defaults)),
            parent=self)
        if ans is None:
            return
        have = {j["id"] for j in self.store.jobs}
        added = sum(1 for j in defaults if j["id"] not in have)
        if ans:
            # keep a copy of the user's list: data/jobs_backup_<date>.json
            storage.save(f"jobs_backup_{dt.datetime.now():%Y%m%d_%H%M%S}", self.store.jobs)
            jobs = defaults
        else:
            jobs = self.store.jobs + [j for j in defaults if j["id"] not in have]
        self._saver("jobs")(jobs)
        self.store.reload()
        self.refresh()
        messagebox.showinfo(app_title(), T("Jobs list updated: {n} jobs ({added} new).",
                                           n=len(jobs), added=added), parent=self)

    def about(self):
        """About box with the version and the update check."""
        dlg = tk.Toplevel(self)
        dlg.title(T("About"))
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self)
        body = tk.Frame(dlg, bg=BG, padx=14, pady=12)
        body.pack()
        if self.icons.get(48):
            tk.Label(body, image=self.icons[48]).grid(row=0, column=0, rowspan=3, sticky="n", padx=(0, 12))
        tk.Label(body, text=app_title(), font=win95.FONT_BOLD).grid(row=0, column=1, sticky="w")
        tk.Label(body, text=T("Version {v}", v=__version__)).grid(row=1, column=1, sticky="w")
        tk.Label(body, justify="left", text=T("Generates daily Permit to Work forms\nfrom the Word "
                                               "template with rotating jobs and crew.")
                 + f"\n\n{T('Data folder:')}\n{storage.DATA_DIR}\n{T('Log files:')}\n{ptwlog.LOG_DIR}"
                 ).grid(row=2, column=1, sticky="w", pady=(6, 0))
        bar = tk.Frame(dlg, bg=BG)
        bar.pack(pady=(0, 10))
        win95.button(bar, T("Check for updates"), lambda: self.check_updates(dlg), width=20
                     ).pack(side="left", padx=4)
        win95.button(bar, T("Open log folder"), lambda: open_path(ptwlog.LOG_DIR), width=16
                     ).pack(side="left", padx=4)
        win95.button(bar, T("OK"), dlg.destroy).pack(side="left", padx=4)
        win95.center(dlg, self)
        dlg.grab_set()

    def check_updates(self, parent=None):
        from . import updater
        parent = parent or self
        repo = self.store.settings.get("update_repo") or updater.DEFAULT_REPO
        try:
            rel = updater.latest_release(repo)
        except updater.UpdateError as e:
            ptwlog.log.info("update check: %s", e)
            messagebox.showwarning(T("Check for updates"),
                                   T("Could not check for updates:\n{e}", e=e), parent=parent)
            return
        ptwlog.log.info("update check: latest %s, running %s", rel["version"], __version__)
        if not updater.is_newer(rel):
            messagebox.showinfo(T("Check for updates"),
                                T("You have the latest version ({v}).", v=__version__), parent=parent)
            return
        if not updater.can_self_update():
            if messagebox.askyesno(T("Check for updates"),
                                   T("Version {new} is available (you have {v}).\n"
                                     "Open the download page?", new=rel["version"], v=__version__),
                                   parent=parent):
                open_path(rel["page"])
            return
        if not messagebox.askyesno(T("Check for updates"),
                                   T("Version {new} is available (you have {v}).\n\n"
                                     "Download it and restart the program now?\n"
                                     "Your data, templates and history are kept.",
                                     new=rel["version"], v=__version__), parent=parent):
            return

        def work(progress, cancelled):
            return updater.download(rel, progress, cancelled)

        def done(path, error, cancelled):
            if error is not None:
                if not cancelled:
                    messagebox.showerror(T("Check for updates"), str(error), parent=parent)
                return
            try:
                updater.install_and_restart(path)
            except OSError as e:
                ptwlog.error("update install failed", True)
                messagebox.showerror(T("Check for updates"), str(e), parent=parent)
                return
            ptwlog.log.info("updated to %s, restarting", rel["version"])
            self.destroy()

        run_with_progress(self, parent, T("Check for updates"),
                          T("Downloading version {new}...", new=rel["version"]), work, done)

    def report_callback_exception(self, exc, val, tb):
        """An error in a button / menu: write it to the log and tell the user."""
        ptwlog.error("Error in the window", (exc, val, tb))
        try:
            messagebox.showerror(app_title(), T("An error occurred:\n{e}\n\nDetails are in the log:\n{path}",
                                                e=val, path=os.path.join(ptwlog.LOG_DIR, "ptw.log")),
                                 parent=self)
        except Exception:  # noqa: BLE001 - never fail while reporting a failure
            pass

    def _heartbeat(self):
        ptwlog.heartbeat()
        self.after(1000, self._heartbeat)


def main():
    ptwlog.setup()
    ptwlog.start_watchdog()
    try:
        from . import updater
        updater.cleanup_old()
        app = App()
        app._heartbeat()
        app.mainloop()
        ptwlog.log.info("---- exit")
    except Exception:
        ptwlog.error("The program stopped with an error", True)
        raise
