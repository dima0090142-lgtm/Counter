"""Main window of the Permit to Work generator."""
import copy
import datetime as dt
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from tkcalendar import Calendar, DateEntry

from . import docgen, generator, storage, win95
from .win95 import BG

APP_TITLE = "Permit to Work Generator"


def open_path(path):
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def member_label(store, m):
    return f"{m['rank']:<6} {m['first_name']} {m['last_name']}"


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

        top = win95.group(self, "Permit")
        top.pack(fill="x", padx=4, pady=4)
        tk.Label(top, text="Date:").grid(row=0, column=0, sticky="w")
        self.date = DateEntry(top, width=12, **win95.calendar_options())
        self.date.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        win95.fix_calendar_arrows(self.date)
        tk.Label(top, text="Permit No:").grid(row=0, column=2, sticky="w", padx=(16, 0))
        self.permit_no = tk.Entry(top, width=8)
        self.permit_no.grid(row=0, column=3, sticky="w", padx=4)
        tk.Label(top, text="(empty = auto / blank)", fg=win95.DARK).grid(row=0, column=4, sticky="w")

        tk.Label(top, text="Job:").grid(row=1, column=0, sticky="w")
        self.job = ttk.Combobox(top, state="readonly", width=48)
        self.job.grid(row=1, column=1, columnspan=4, sticky="we", padx=4, pady=2)
        self.job.bind("<<ComboboxSelected>>", lambda e: self._show_job())

        self.info = tk.Label(top, justify="left", anchor="w", relief="sunken", bd=2,
                             bg=win95.WHITE, padx=4, pady=2, height=4)
        self.info.grid(row=2, column=0, columnspan=5, sticky="we", pady=4)
        top.columnconfigure(4, weight=1)

        mid = tk.Frame(self, bg=BG)
        mid.pack(fill="both", expand=True)
        crew_box = win95.group(mid, "Crew taking part")
        crew_box.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.crew_frame = tk.Frame(crew_box, bg=BG)
        self.crew_frame.pack(fill="both", expand=True)
        win95.button(crew_box, "Auto-pick crew", self.auto_crew, width=14).pack(anchor="w", pady=(4, 0))

        roles = win95.group(mid, "Signatures")
        roles.pack(side="left", fill="y", padx=4, pady=4)
        self.roles = {}
        for i, (key, text) in enumerate((("pc", "5) P.C. (accepts permit):"),
                                         ("transfer", "6) Transferred to:"),
                                         ("close", "7) P.C. (closes permit):"))):
            tk.Label(roles, text=text).grid(row=i * 2, column=0, sticky="w")
            cb = ttk.Combobox(roles, state="readonly", width=30)
            cb.grid(row=i * 2 + 1, column=0, sticky="w", pady=(0, 6))
            self.roles[key] = cb
        self.ao_label = tk.Label(roles, anchor="w", fg=win95.DARK)
        self.ao_label.grid(row=6, column=0, sticky="w")
        self.refresh()

    # --- data ---
    def refresh(self):
        s = self.store.settings
        self.jobs = [j for j in self.store.jobs if j.get("active", True)]
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
            tk.Checkbutton(self.crew_frame, text=member_label(self.store, m), variable=v,
                           anchor="w", command=self._crew_changed
                           ).grid(row=i % per_col, column=i // per_col, sticky="w", padx=(0, 12))
            self.check_vars[m["id"]] = v
        ao = self.store.member(s.get("ao_id"))
        self.ao_label.config(text="A.O.: " + (generator.sign_text(self.store, ao["id"]) if ao else "(not set)"))
        self._update_role_lists()

    def _show_job(self):
        j = self.current_job()
        if not j:
            self.info.config(text="")
            return
        self.info.config(text=f"Location:  {j['location']}\nPlant:  {j['plant']}\n"
                              f"Work:  {j['work']}\nRisk Assessment:  {j.get('ra_no', '')}")

    def current_job(self):
        i = self.job.current()
        return self.jobs[i] if 0 <= i < len(self.jobs) else None

    def selected_crew(self):
        ids = [k for k, v in self.check_vars.items() if v.get()]
        return generator.sort_by_rank(self.store, ids)

    def _update_role_lists(self, keep=True):
        ids = self.selected_crew()
        self.role_ids = {"": ""}
        for i in ids:
            self.role_ids[generator.sign_text(self.store, i)] = i
        for cb in self.roles.values():
            cur = cb.get()
            cb["values"] = list(self.role_ids)
            if not keep or cur not in self.role_ids:
                cb.set("")

    def _crew_changed(self):
        self._update_role_lists()
        self.set_roles(*generator.default_roles(self.store, self.selected_crew()))

    def set_roles(self, pc, transfer, close):
        for key, mid in (("pc", pc), ("transfer", transfer), ("close", close)):
            self.roles[key].set(generator.sign_text(self.store, mid) if mid else "")

    def auto_crew(self):
        j = self.current_job()
        if not j:
            messagebox.showwarning(APP_TITLE, "Select a job first.", parent=self)
            return
        planner = generator.Planner(self.store)
        day = self.date.get_date()
        planner.load_history(day + dt.timedelta(days=1))
        crew = planner.make_crew(j, day)
        for k, v in self.check_vars.items():
            v.set(k in crew)
        self._update_role_lists()
        self.set_roles(*generator.default_roles(self.store, crew))

    # --- in / out ---
    def set(self, permit):
        self.date.set_date(generator.parse_date(permit["date"]))
        ids = [j["id"] for j in self.jobs]
        if permit["job_id"] in ids:
            self.job.current(ids.index(permit["job_id"]))
        self._show_job()
        for k, v in self.check_vars.items():
            v.set(k in permit["crew"])
        self._update_role_lists(keep=False)
        self.set_roles(permit.get("pc"), permit.get("transfer"), permit.get("close"))
        self.permit_no.delete(0, "end")
        if permit.get("permit_no"):
            self.permit_no.insert(0, str(permit["permit_no"]))

    def get(self):
        j = self.current_job()
        if not j:
            raise ValueError("Select a job.")
        crew = self.selected_crew()
        if not crew:
            raise ValueError("Select at least one crew member.")
        # keep the chosen closing P.C. (the lead) first in "issued to"
        close = self.role_ids.get(self.roles["close"].get(), "")
        if close in crew:
            crew = [close] + [c for c in crew if c != close]
        no = self.permit_no.get().strip()
        return {"date": self.date.get_date().isoformat(), "job_id": j["id"], "crew": crew,
                "pc": self.role_ids.get(self.roles["pc"].get(), ""),
                "transfer": self.role_ids.get(self.roles["transfer"].get(), ""),
                "close": close, "permit_no": no or None}


class PermitDialog(tk.Toplevel):
    def __init__(self, app, permit):
        super().__init__(app)
        self.title("Edit permit")
        self.configure(bg=BG)
        self.transient(app)
        self.result = None
        self.form = PermitForm(self, app)
        self.form.pack(fill="both", expand=True, padx=4, pady=4)
        self.form.set(permit)
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=8)
        win95.button(bar, "Cancel", self.destroy).pack(side="right", padx=4)
        win95.button(bar, "OK", self.ok).pack(side="right", padx=4)
        win95.center(self, app)
        self.grab_set()
        self.wait_window()

    def ok(self):
        try:
            self.result = self.form.get()
        except ValueError as e:
            messagebox.showwarning(APP_TITLE, str(e), parent=self)
            return
        self.destroy()


# ======================================================================
# Tabs
# ======================================================================

PLAN_COLUMNS = [("date", "Date"), ("job", "Job"), ("ra", "RA No"), ("crew", "Issued to"),
                ("pc", "P.C. (5)"), ("transfer", "Transfer (6)"), ("close", "Close (7)")]
PLAN_WIDTHS = [72, 170, 52, 250, 76, 76, 76]


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
        g1 = win95.group(left, "From")
        g1.pack(fill="x")
        self.cal_from = Calendar(g1, selectmode="day", year=today.year, month=today.month,
                                 day=today.day, **win95.calendar_options())
        self.cal_from.pack()
        win95.fix_calendar_arrows(self.cal_from)
        g2 = win95.group(left, "To")
        g2.pack(fill="x", pady=(6, 0))
        end = today + dt.timedelta(days=6)
        self.cal_to = Calendar(g2, selectmode="day", year=end.year, month=end.month,
                               day=end.day, **win95.calendar_options())
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
        win95.button(bar, "Generate", self.generate).pack(side="left", padx=(0, 4))
        win95.button(bar, "Reroll", self.reroll).pack(side="left", padx=4)
        win95.button(bar, "Edit...", self.edit).pack(side="left", padx=4)
        win95.button(bar, "Remove", self.remove).pack(side="left", padx=4)
        win95.button(bar, "Create files", self.create, width=14,
                     font=win95.FONT_BOLD).pack(side="right")
        g = win95.group(right, "Plan")
        g.pack(fill="both", expand=True)
        f, self.tree = win95.scrolled_tree(g, PLAN_COLUMNS, PLAN_WIDTHS, height=20)
        f.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.edit())

    def _from_changed(self, _e=None):
        a = self.cal_from.selection_get()
        if self.cal_to.selection_get() < a:
            self.cal_to.selection_set(a)
            self.cal_to.see(a)
        self._update_range()

    def _update_range(self):
        a, b = self.cal_from.selection_get(), self.cal_to.selection_get()
        days = (b - a).days + 1
        self.range_label.config(text=f"{a:%d/%m/%Y} - {b:%d/%m/%Y}  ({max(days, 0)} days)")

    def generate(self):
        a, b = self.cal_from.selection_get(), self.cal_to.selection_get()
        if b < a:
            messagebox.showwarning(APP_TITLE, "'To' date is before 'From' date.", parent=self)
            return
        if (b - a).days > 366:
            messagebox.showwarning(APP_TITLE, "Period is longer than one year.", parent=self)
            return
        self.plan = generator.Planner(self.store).plan(a, b)
        self.show()
        self.app.status.set(f"{len(self.plan)} permits planned. Check the list, then press 'Create files'.")

    def show(self):
        self.tree.delete(*self.tree.get_children())
        st = self.store
        for i, p in enumerate(self.plan):
            j = st.job(p["job_id"]) or {"title": p["job_id"]}
            d = generator.parse_date(p["date"])
            self.tree.insert("", "end", iid=str(i), values=(
                d.strftime("%d/%m/%Y"), j["title"], j.get("ra_no", ""),
                generator.issued_to_text(st, p["crew"]), short_name(st, p.get("pc")),
                short_name(st, p.get("transfer")), short_name(st, p.get("close"))))

    def _selected(self):
        return sorted(int(i) for i in self.tree.selection())

    def reroll(self):
        sel = self._selected()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Select permits in the list to reroll.", parent=self)
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
            messagebox.showinfo(APP_TITLE, "Nothing to create. Press 'Generate' first.", parent=self)
            return
        if not self.app.ensure_output_dir():
            return
        dates = {p["date"] for p in self.plan}
        replace = False
        if any(h["date"] in dates for h in self.store.history):
            ans = messagebox.askyesnocancel(
                APP_TITLE, "History already has permits for some of these dates.\n\n"
                "Yes - replace them in history\nNo - keep both", parent=self)
            if ans is None:
                return
            replace = ans
        try:
            paths = docgen.write_permits(self.store, self.plan, replace_dates=replace)
        except Exception as e:  # show any problem to the user, nothing is lost
            messagebox.showerror(APP_TITLE, f"Could not create files:\n{e}", parent=self)
            return
        self.app.history_tab.show()
        self.app.status.set(f"{len(paths)} files created in {self.store.settings['output_dir']}")
        if messagebox.askyesno(APP_TITLE, f"{len(paths)} permits created.\n\nOpen the folder?",
                               parent=self):
            open_path(self.store.settings["output_dir"])
        self.plan = []
        self.show()


class ManualTab(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        self.form = PermitForm(self, app)
        self.form.pack(fill="both", expand=True, padx=4, pady=4)
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        win95.button(bar, "Create file", self.create, width=14,
                     font=win95.FONT_BOLD).pack(side="right")

    def create(self):
        try:
            p = self.form.get()
        except ValueError as e:
            messagebox.showwarning(APP_TITLE, str(e), parent=self)
            return
        if not self.app.ensure_output_dir():
            return
        try:
            path = docgen.write_permits(self.app.store, [p])[0]
        except Exception as e:  # show any problem to the user
            messagebox.showerror(APP_TITLE, f"Could not create file:\n{e}", parent=self)
            return
        self.app.history_tab.show()
        self.app.status.set(f"Created {os.path.basename(path)}")
        self.form.permit_no.delete(0, "end")
        if messagebox.askyesno(APP_TITLE, f"Created:\n{os.path.basename(path)}\n\nOpen it now?",
                               parent=self):
            open_path(path)


class HistoryTab(tk.Frame):
    COLS = [("date", "Date"), ("no", "No"), ("job", "Job"), ("crew", "Issued to"), ("file", "File")]

    def __init__(self, master, app):
        super().__init__(master, bg=BG)
        self.app = app
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=4, pady=4)
        win95.button(bar, "Open file", self.open_file).pack(side="left", padx=(0, 4))
        win95.button(bar, "Open folder", self.open_folder).pack(side="left", padx=4)
        win95.button(bar, "Delete entry", self.delete).pack(side="left", padx=4)
        tk.Label(bar, text="History is used to keep jobs and crew different from day to day.",
                 fg=win95.DARK).pack(side="left", padx=8)
        f, self.tree = win95.scrolled_tree(self, self.COLS, [74, 40, 200, 300, 260], height=20)
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
        self.app.status.right.set(f"History: {len(st.history)} permits")

    def _sel(self):
        return sorted((int(i) for i in self.tree.selection()), reverse=True)

    def open_file(self):
        st = self.app.store
        for i in self._sel()[:1]:
            path = os.path.join(st.settings.get("output_dir", ""), st.history[i].get("file", ""))
            if os.path.isfile(path):
                open_path(path)
            else:
                messagebox.showinfo(APP_TITLE, f"File not found:\n{path}", parent=self)

    def open_folder(self):
        folder = self.app.store.settings.get("output_dir")
        if folder and os.path.isdir(folder):
            open_path(folder)

    def delete(self):
        sel = self._sel()
        if not sel or not messagebox.askyesno(
                APP_TITLE, f"Delete {len(sel)} entries from history?\n(Files are not deleted.)",
                parent=self):
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

    def __init__(self, app, title, records, fields, label, id_from, on_save, hint=""):
        super().__init__(app)
        self.title(title)
        self.configure(bg=BG)
        self.transient(app)
        self.app = app
        self.records = copy.deepcopy(records)
        self.fields, self.label, self.id_from, self.on_save = fields, label, id_from, on_save
        self.current = None

        left = win95.group(self, "Records")
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
        win95.button(b, "New", self.new, width=8).pack(side="left")
        win95.button(b, "Copy", self.duplicate, width=8).pack(side="left", padx=4)
        win95.button(b, "Delete", self.delete, width=8).pack(side="left")

        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        form = win95.group(right, "Details")
        form.pack(fill="both", expand=True)
        self.widgets = {}
        ranks = [r["code"] for r in app.store.ranks]
        for row, (key, text, kind) in enumerate(fields):
            tk.Label(form, text=text + ":").grid(row=row, column=0, sticky="nw", pady=2)
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
            tk.Label(form, text=hint, justify="left", fg=win95.DARK, wraplength=420
                     ).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(8, 0))
        bar = tk.Frame(right, bg=BG)
        bar.pack(fill="x", pady=(8, 0))
        win95.button(bar, "Cancel", self.destroy).pack(side="right", padx=4)
        win95.button(bar, "OK", self.ok).pack(side="right", padx=4)
        win95.button(bar, "Apply", self.apply).pack(side="left")

        self._fill_list()
        if self.records:
            self.lb.selection_set(0)
            self._select()
        win95.center(self, app)
        self.grab_set()

    def _fill_list(self):
        self.lb.delete(0, "end")
        for r in self.records:
            self.lb.insert("end", self.label(r))

    def _select(self, _e=None):
        sel = self.lb.curselection()
        if not sel:
            return
        if self.current is not None and self.current != sel[0]:
            if not self.apply(silent=True):
                self.lb.selection_clear(0, "end")
                self.lb.selection_set(self.current)
                return
        self.current = sel[0]
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
                    raise ValueError(f"'{key}' must be a number") from None
            elif kind == "codes":
                rec[key] = [c.strip() for c in text.replace(";", ",").split(",") if c.strip()]
            elif kind == "range":
                m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", text) or re.fullmatch(r"(\d+)()", text)
                if not m:
                    raise ValueError(f"'{key}' must look like 0-2")
                lo = int(m.group(1))
                hi = int(m.group(2) or lo)
                rec[key] = [min(lo, hi), max(lo, hi)]
            else:
                rec[key] = text
        return rec

    def apply(self, silent=False):
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
            messagebox.showwarning(self.title(), "Code must not be empty.", parent=self)
            return False
        self.records[self.current].update(rec)
        self.lb.delete(self.current)
        self.lb.insert(self.current, self.label(self.records[self.current]))
        self.lb.selection_set(self.current)
        return True

    def _add(self, rec):
        if not self.apply(silent=True):
            return
        self.records.append(rec)
        self.lb.insert("end", self.label(rec))
        self.current = None
        self.lb.selection_clear(0, "end")
        self.lb.selection_set("end")
        self.lb.see("end")
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
        self.apply(silent=True)

    def delete(self):
        if self.current is None:
            return
        if not messagebox.askyesno(self.title(), "Delete this record?", parent=self):
            return
        del self.records[self.current]
        self.current = None
        self._fill_list()
        if self.records:
            self.lb.selection_set(0)
            self._select()

    def ok(self):
        if not self.apply(silent=True):
            return
        self.on_save(self.records)
        self.destroy()


class SettingsDialog(tk.Toplevel):
    FIELDS = [
        ("ship_name", "Ship name"),
        ("time_issue", "Time permit issued (5)"),
        ("time_transfer", "Time of transfer (6)"),
        ("time_close", "Time permit closed (7)"),
        ("permits_per_day", "Permits per day"),
        ("no_repeat_days", "Do not repeat a job within (days)"),
        ("next_permit_no", "Next permit number"),
        ("filename_pattern", "File name pattern"),
        ("filename_date_format", "Date format in file name"),
    ]

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        st = app.store
        self.title("Settings")
        self.configure(bg=BG)
        self.transient(app)
        self.resizable(False, False)

        paths = win95.group(self, "Files")
        paths.pack(fill="x", padx=8, pady=6)
        self.out = self._path_row(paths, 0, "Output folder:", st.settings.get("output_dir", ""), self._pick_out)
        self.tpl = self._path_row(paths, 1, "Word template:", st.settings.get("template_path", ""), self._pick_tpl)
        tk.Label(paths, text=f"(empty template = built-in {storage.DEFAULT_TEMPLATE})",
                 fg=win95.DARK).grid(row=2, column=1, columnspan=2, sticky="w")

        g = win95.group(self, "Permit")
        g.pack(fill="x", padx=8, pady=6)
        tk.Label(g, text="A.O. (Authorizing Officer):").grid(row=0, column=0, sticky="w", pady=2)
        self.ao_map = {member_label(st, m): m["id"] for m in st.crew}
        self.ao = ttk.Combobox(g, state="readonly", values=list(self.ao_map), width=34)
        self.ao.grid(row=0, column=1, sticky="w", padx=4)
        for label, mid in self.ao_map.items():
            if mid == st.settings.get("ao_id"):
                self.ao.set(label)
        self.entries = {}
        for i, (key, text) in enumerate(self.FIELDS, start=1):
            tk.Label(g, text=text + ":").grid(row=i, column=0, sticky="w", pady=2)
            e = tk.Entry(g, width=24 if "filename" in key or key == "ship_name" else 8)
            e.insert(0, str(st.settings.get(key, "")))
            e.grid(row=i, column=1, sticky="w", padx=4)
            self.entries[key] = e
        self.auto = tk.BooleanVar(value=bool(st.settings.get("auto_number")))
        tk.Checkbutton(g, text="Number permits automatically", variable=self.auto
                       ).grid(row=len(self.FIELDS) + 1, column=0, columnspan=2, sticky="w")
        tk.Label(g, text="File name: {date} {title} {ra} {no}.  Date: %Y-%m-%d, %d.%m.%Y ...",
                 fg=win95.DARK).grid(row=len(self.FIELDS) + 2, column=0, columnspan=2, sticky="w")

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=8, pady=8)
        win95.button(bar, "Cancel", self.destroy).pack(side="right", padx=4)
        win95.button(bar, "OK", self.ok).pack(side="right", padx=4)
        win95.center(self, app)
        self.grab_set()

    def _path_row(self, master, row, text, value, cmd):
        tk.Label(master, text=text).grid(row=row, column=0, sticky="w", pady=2)
        e = tk.Entry(master, width=52)
        e.insert(0, value)
        e.grid(row=row, column=1, sticky="w", padx=4)
        win95.button(master, "Browse...", cmd, width=9).grid(row=row, column=2)
        return e

    def _pick_out(self):
        d = filedialog.askdirectory(parent=self, initialdir=self.out.get() or None)
        if d:
            self.out.delete(0, "end")
            self.out.insert(0, d)

    def _pick_tpl(self):
        f = filedialog.askopenfilename(parent=self, filetypes=[("Word document", "*.docx")])
        if f:
            self.tpl.delete(0, "end")
            self.tpl.insert(0, f)

    def ok(self):
        s = self.app.store.settings
        new = {k: e.get().strip() for k, e in self.entries.items()}
        try:
            for k in ("permits_per_day", "no_repeat_days", "next_permit_no"):
                new[k] = int(new[k])
        except ValueError:
            messagebox.showwarning("Settings", "Numbers expected for per day / repeat / permit no.",
                                   parent=self)
            return
        for k in ("time_issue", "time_transfer", "time_close"):
            if not re.fullmatch(r"\d{1,2}:\d{2}", new[k]):
                messagebox.showwarning("Settings", f"Time must look like 08:00 ({k}).", parent=self)
                return
        try:
            dt.date.today().strftime(new["filename_date_format"])
            new["filename_pattern"].format(date="", title="", ra="", no="")
        except (ValueError, KeyError, IndexError) as e:
            messagebox.showwarning("Settings", f"Wrong file name pattern: {e}", parent=self)
            return
        s.update(new)
        s["output_dir"] = self.out.get().strip()
        s["template_path"] = self.tpl.get().strip()
        s["auto_number"] = self.auto.get()
        s["ao_id"] = self.ao_map.get(self.ao.get(), s.get("ao_id"))
        storage.save("settings", s)
        self.app.refresh()
        self.destroy()


# ======================================================================
# Main window
# ======================================================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        win95.apply_style(self)
        self.store = storage.Store()
        self.geometry("1100x680")
        self.minsize(900, 600)
        self._menu()

        win95.Banner(self, APP_TITLE, f"{self.store.settings.get('ship_name', '')}  -  "
                     "Daily Permit to Work, Engine Department").pack(fill="x")
        self.status = win95.StatusBar(self)
        self.status.pack(side="bottom", fill="x")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.auto_tab = AutoTab(nb, self)
        self.manual_tab = ManualTab(nb, self)
        self.history_tab = HistoryTab(nb, self)
        nb.add(self.auto_tab, text="Auto generate")
        nb.add(self.manual_tab, text="Manual")
        nb.add(self.history_tab, text="History")
        self.status.set("Ready. Choose the period and press 'Generate'.")
        self.after(200, self._first_start)

    def _menu(self):
        m = tk.Menu(self)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Open output folder", command=self.history_tab_open_folder)
        f.add_separator()
        f.add_command(label="Exit", command=self.destroy)
        m.add_cascade(label="File", menu=f, underline=0)
        d = tk.Menu(m, tearoff=0)
        d.add_command(label="Jobs...", command=self.edit_jobs)
        d.add_command(label="Crew...", command=self.edit_crew)
        d.add_command(label="Ranks...", command=self.edit_ranks)
        m.add_cascade(label="Data", menu=d, underline=0)
        o = tk.Menu(m, tearoff=0)
        o.add_command(label="Settings...", command=lambda: SettingsDialog(self))
        m.add_cascade(label="Options", menu=o, underline=0)
        h = tk.Menu(m, tearoff=0)
        h.add_command(label="About", command=self.about)
        m.add_cascade(label="Help", menu=h, underline=0)
        self.config(menu=m)

    def history_tab_open_folder(self):
        self.history_tab.open_folder()

    def _first_start(self):
        if not self.store.settings.get("output_dir"):
            messagebox.showinfo(APP_TITLE, "Welcome!\n\nPlease choose the folder where permits "
                                "will be saved (Options > Settings).", parent=self)
            SettingsDialog(self)

    def ensure_output_dir(self):
        if self.store.settings.get("output_dir"):
            return True
        messagebox.showwarning(APP_TITLE, "Output folder is not set.", parent=self)
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
                  ("ratings", "Ratings count", "range"), ("active", "Active", "bool")]
        hint = ("Responsible ranks: one of them leads the job and closes the permit, e.g. 2E.\n"
                "Counts are 'min-max', e.g. 0-1 or 1-2. Ranks are comma separated: MM, FITTR.\n"
                "Keep Location / Plant / Work short - the form has one line for each.")
        ListEditor(self, "Jobs", self.store.jobs, fields,
                   lambda j: f"{','.join(j.get('lead_ranks', []))[:7]:<8} {j.get('title', '')}",
                   lambda j: j.get("title", ""), self._saver("jobs"), hint)

    def edit_crew(self):
        fields = [("id", "ID", "str"), ("rank", "Rank", "rank"),
                  ("first_name", "First name", "str"), ("last_name", "Last name", "str"),
                  ("title", "Rank title (optional)", "str"), ("active", "On board", "bool")]
        hint = ("Rank title overrides the rank name in signatures, e.g. 'Asst. Second Engineer'.\n"
                "Untick 'On board' when a crew member signs off - history is kept.")
        ListEditor(self, "Crew", self.store.crew, fields,
                   lambda m: f"{m.get('rank', ''):<6} {m.get('first_name', '')} {m.get('last_name', '')}"
                   + ("" if m.get("active", True) else "  (off)"),
                   lambda m: f"{m.get('last_name', '')} {m.get('first_name', '')}",
                   self._saver("crew"), hint)

    def edit_ranks(self):
        fields = [("code", "Code", "str"), ("short", "Short (issued to)", "str"),
                  ("full", "Full (signatures)", "str"), ("officer", "Officer (can sign as P.C.)", "bool"),
                  ("order", "Order (seniority)", "int")]
        ListEditor(self, "Ranks", self.store.ranks, fields,
                   lambda r: f"{r.get('code', ''):<6} {r.get('full', '')}",
                   lambda r: r.get("code", ""), self._saver("ranks"))

    def about(self):
        messagebox.showinfo("About", f"{APP_TITLE}\n\nGenerates daily Permit to Work forms\n"
                            "from the Word template with rotating jobs and crew.\n\n"
                            f"Data folder:\n{storage.DATA_DIR}", parent=self)


def main():
    app = App()
    app.mainloop()
