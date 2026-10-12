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

from . import __version__, docgen, generator, i18n, sound, storage, win95
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
    return win95.calendar_options("ru_RU" if i18n.language() == "ru" else "en_GB")


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

        tk.Label(top, text=T("Job:")).grid(row=1, column=0, sticky="w")
        self.job = ttk.Combobox(top, state="readonly", width=48, height=25)
        self.job.grid(row=1, column=1, columnspan=4, sticky="we", padx=4, pady=2)
        self.job.bind("<<ComboboxSelected>>", lambda e: self._job_changed())

        self.info = tk.Label(top, justify="left", anchor="w", relief="sunken", bd=2,
                             bg=win95.WHITE, padx=4, pady=2, height=4)
        self.info.grid(row=2, column=0, columnspan=5, sticky="we", pady=4)
        top.columnconfigure(4, weight=1)

        mid = tk.Frame(self, bg=BG)
        mid.pack(fill="both", expand=True)
        crew_box = win95.group(mid, T("Crew taking part"))
        crew_box.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.crew_frame = tk.Frame(crew_box, bg=BG)
        self.crew_frame.pack(fill="both", expand=True)
        win95.button(crew_box, T("Auto-pick crew"), self.auto_crew, width=18).pack(anchor="w", pady=(4, 0))

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
        self.jobs = sorted((j for j in self.store.jobs if j.get("active", True)),
                           key=lambda j: j["title"].lower())
        self.job["values"] = [f"{j['title']}   [{j.get('ra_no', '')}]" for j in self.jobs]
        for w in self.crew_frame.winfo_children():
            w.destroy()
        old = {k for k, v in self.check_vars.items() if v.get()}
        self.check_vars = {}
        members = [m for m in self.store.crew
                   if m.get("active", True) and m["id"] != s.get("ao_id")]
        members.sort(key=lambda m: self.store.rank(m["rank"])["order"])
        per_col = max(1, (len(members) + 1) // 2)
        for i, m in enumerate(members):
            v = tk.BooleanVar(value=m["id"] in old)
            mark = "  (P.C.)" if self.store.can_pc(m["id"]) else ""
            tk.Checkbutton(self.crew_frame, text=member_label(self.store, m) + mark, variable=v,
                           anchor="w", command=self._crew_changed
                           ).grid(row=i % per_col, column=i // per_col, sticky="w", padx=(0, 12))
            self.check_vars[m["id"]] = v
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
        loto = "   LOTO: " + (T("yes") if j.get("loto") else T("no"))
        self.info.config(text=f"{T('Location')}:  {j['location']}\n{T('Plant')}:  {j['plant']}\n"
                              f"{T('Work')}:  {j['work']}\nRisk Assessment:  {j.get('ra_no', '')}"
                              + loto)

    def _job_changed(self):
        self._show_job()
        j = self.current_job()
        if j is not None:
            self.loto_var.set(bool(j.get("loto")))
            self._loto_toggled()

    def current_job(self):
        i = self.job.current()
        return self.jobs[i] if 0 <= i < len(self.jobs) else None

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
        self.set_roles(*generator.default_roles(self.store, crew, self.lead))
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
        self.loto_var.set(bool(team["loto"]))
        self.loto.set(generator.sign_text(self.store, team["loto"]) if team["loto"] else "")
        self._loto_toggled()

    # --- in / out ---
    def set(self, permit):
        self.date.set_date(generator.parse_date(permit["date"]))
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


def show_write_result(app, parent, paths, warnings):
    """Status line, warnings about long text, offer to open the folder."""
    s = app.store
    app.history_tab.show()
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
        end = today + dt.timedelta(days=6)
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

    def show(self):
        self.tree.delete(*self.tree.get_children())
        st = self.store
        numbers = generator.permit_numbers(st, self.plan)
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
        d = PermitDialog(self.app, self.plan[sel[0]])
        if d.result:
            self.plan[sel[0]] = d.result
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
        if not self.app.ensure_output_dir():
            return
        dates = {p["date"] for p in self.plan}
        replace = False
        if any(h["date"] in dates for h in self.store.history):
            ans = messagebox.askyesnocancel(
                app_title(), T("History already has permits for some of these dates.\n\n"
                               "Yes - replace them in history\nNo - keep both"), parent=self)
            if ans is None:
                return
            replace = ans
        try:
            paths, warnings = docgen.write_permits(self.store, self.plan, replace_dates=replace)
        except Exception as e:  # show any problem to the user, nothing is lost
            messagebox.showerror(app_title(), f"{T('Could not create files:')}\n{e}", parent=self)
            return
        show_write_result(self.app, self, paths, warnings)
        self.plan = []
        self.show()
        if self.store.settings.get("open_folder_after", True):
            open_path(self.store.settings["output_dir"])


class ManualTab(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.form = PermitForm(self, app)
        self.form.pack(fill="both", expand=True, padx=4, pady=4)
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        win95.button(bar, T("Create file"), self.create, width=14,
                     font=win95.FONT_BOLD).pack(side="right")

    def create(self):
        try:
            p = self.form.get()
        except ValueError as e:
            messagebox.showwarning(app_title(), str(e), parent=self)
            return
        if not self.app.ensure_output_dir():
            return
        try:
            paths, warnings = docgen.write_permits(self.app.store, [p])
        except Exception as e:  # show any problem to the user
            messagebox.showerror(app_title(), f"{T('Could not create file:')}\n{e}", parent=self)
            return
        show_write_result(self.app, self, paths, warnings)
        name = os.path.basename(paths[0])
        self.app.status.set(T("Created {name}", name=name))
        self.form.permit_no.delete(0, "end")
        if messagebox.askyesno(app_title(), T("Created:\n{name}\n\nOpen it now?", name=name),
                               parent=self):
            open_path(paths[0])


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
        tk.Label(bar, text=T("History is used to keep jobs and crew different from day to day."),
                 fg=win95.DARK).pack(side="left", padx=8)
        cols = [(k, T(t)) for k, t in self.COLS]
        f, self.tree = win95.scrolled_tree(self, cols, [74, 40, 200, 300, 260], height=20)
        f.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.tree.bind("<Double-1>", lambda e: self.open_file())
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


class ListEditor(tk.Toplevel):
    """Generic editor: list of records on the left, fields on the right.

    field kinds: str, int, bool, codes (comma separated list), range (min-max), rank
    """

    def __init__(self, app, title, records, fields, label, id_from, on_save, hint="",
                 validate=None):
        super().__init__(app)
        self.title(title)
        self.configure(bg=BG)
        self.transient(app)
        self.app = app
        self.records = copy.deepcopy(records)
        self.fields, self.label, self.id_from, self.on_save = fields, label, id_from, on_save
        self.validate = validate
        self.current = None

        left = win95.group(self, T("Records"))
        left.pack(side="left", fill="both", padx=6, pady=6)
        lf = tk.Frame(left, bg=BG)
        lf.pack(fill="both", expand=True)
        self.lb = tk.Listbox(lf, width=38, height=24, exportselection=False, activestyle="none")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.lb.bind("<<ListboxSelect>>", self._select)
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

        self._fill_list()
        if self.records:
            self._highlight(0)
            self._select()
        win95.center(self, app)
        self.grab_set()

    def _fill_list(self):
        self.lb.delete(0, "end")
        for r in self.records:
            self.lb.insert("end", self.label(r))

    def _highlight(self, index):
        """Exactly one highlighted row (Listbox.selection_set alone adds to the selection)."""
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(index)
        self.lb.activate(index)
        self.lb.see(index)

    def _select(self, _e=None):
        sel = self.lb.curselection()
        if not sel:
            return
        target = sel[0]
        if self.current is not None and self.current != target:
            if not self.apply():
                self._highlight(self.current)
                return
        self._highlight(target)
        self.current = target
        rec = self.records[self.current]
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
        selected = self.lb.curselection()
        self.lb.delete(self.current)
        self.lb.insert(self.current, self.label(old))
        if not selected or selected[0] == self.current:  # re-selecting would add a 2nd row
            self._highlight(self.current)
        if changed and self.validate:
            notes = self.validate(old)
            if notes:
                messagebox.showwarning(self.title(), "\n\n".join(notes), parent=self)
        return True

    def _add(self, rec):
        if not self.apply():
            return
        self.records.append(rec)
        self.lb.insert("end", self.label(rec))
        self.current = None
        self._highlight(len(self.records) - 1)
        self._select()

    def new(self):
        rec = {}
        for key, _t, kind in self.fields:
            rec[key] = {"bool": True, "codes": [], "range": [0, 0], "int": 0}.get(kind, "")
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
        del self.records[self.current]
        self.current = None
        self._fill_list()
        if self.records:
            self._highlight(0)
            self._select()

    def ok(self):
        if not self.apply():
            return
        self.on_save(self.records)
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
        except (ValueError, KeyError, IndexError) as e:
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
        except (ValueError, KeyError, IndexError) as e:
            warn(T("Wrong file name pattern: {e}", e=e))
            return
        tpl = self.tpl.get().strip()
        if tpl and not os.path.isfile(tpl):
            warn(T("Template not found: {path}", path=tpl))
            return
        old_look = (s.get("language"), s.get("ui_font_size"))
        s.update(new)
        s["output_dir"] = self.out.get().strip()
        s["template_path"] = tpl
        s["permit_numbering"] = self.numbering.get()
        s["tick_ao"] = self.tick_ao.get()
        s["tick_pc"] = self.tick_pc.get()
        for key, e in self.code_entries.items():
            s[key] = [c.strip() for c in e.get().replace(";", ",").split(",") if c.strip()]
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
        f.add_command(label=T("Open output folder"), command=lambda: self.history_tab.open_folder())
        f.add_separator()
        f.add_command(label=T("Exit"), command=self.quit_app)
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
                  ("loto", "LOTO (isolation) needed", "bool"), ("active", "Active", "bool")]
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
                   lambda j: j.get("title", ""), self._saver("jobs"), hint, validate)

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
                   self._saver("crew"), hint, validate)

    def edit_ranks(self):
        fields = [("code", "Code", "str"), ("short", "Short (issued to)", "str"),
                  ("full", "Full (signatures)", "str"), ("officer", "Officer", "bool"),
                  ("can_pc", "Can sign as P.C. (sections 5-7)", "bool"),
                  ("can_loto", "Can apply LOTO", "bool"),
                  ("order", "Order (seniority)", "int")]
        ListEditor(self, T("Ranks"), self.store.ranks, fields,
                   lambda r: f"{r.get('code', ''):<6} {r.get('full', '')}",
                   lambda r: r.get("code", ""), self._saver("ranks"))

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
        if ans:
            jobs = defaults
        else:
            have = {j["id"] for j in self.store.jobs}
            jobs = self.store.jobs + [j for j in defaults if j["id"] not in have]
        added = len(jobs) - (0 if ans else len(self.store.jobs))
        self._saver("jobs")(jobs)
        self.store.reload()
        self.refresh()
        messagebox.showinfo(app_title(), T("Jobs list updated: {n} jobs ({added} new).",
                                           n=len(jobs), added=added if not ans else len(jobs)),
                            parent=self)

    def about(self):
        messagebox.showinfo(T("About"), f"{app_title()}\n\n"
                            + T("Generates daily Permit to Work forms\nfrom the Word template "
                                "with rotating jobs and crew.")
                            + f"\n\n{T('Data folder:')}\n{storage.DATA_DIR}", parent=self)


def main():
    app = App()
    app.mainloop()
