"""JSON storage for ranks, crew, jobs, settings and history."""
import json
import os
import shutil
import sys

if getattr(sys, "frozen", False):
    # PyInstaller exe: data lives next to the exe, defaults are bundled inside
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BUNDLE_DIR = APP_DIR

DATA_DIR = os.path.join(APP_DIR, "data")
DEFAULT_TEMPLATE = os.path.join(APP_DIR, "templates", "ptw_template.docx")

DEFAULT_SETTINGS = {
    "ship_name": "",
    "template_path": "",
    "output_dir": "",
    "ao_id": "ce",
    "time_issue": "08:00",
    "time_transfer": "12:00",
    "time_close": "20:00",
    "permits_per_day": 1,
    "no_repeat_days": 7,
    "permit_numbering": "day",   # day (285, 285-1, 285-2) / sequential / blank
    "next_permit_no": 1,
    "filename_pattern": "{date} {title}",
    "filename_date_format": "%Y-%m-%d",
    "fit_one_line": True,
    "min_font_size": 6.5,
    "language": "en",
    "ui_font_size": 8,
    "open_folder_after": True,
    "skip_weekdays": [],
    "sounds": True,
    "splash": True,
    "tick_ao": True,             # tick the A.O. boxes of sections 2 and 3
    "tick_pc": True,             # tick the P.C. boxes of sections 2 and 3
    "pc_supervisor_ranks": ["2E", "3E"],  # P.C. when the job lead cannot be P.C.
    "loto_preferred_ranks": ["ETO", "AEO"],
}

# who may sign as P.C. (sections 5-7) and apply LOTO, for rank files made before
# these flags existed
RANK_FLAGS = {"CE": (False, True), "2E": (True, True), "3E": (True, True),
              "ETO": (True, True), "AEO": (True, True)}


def _path(name):
    return os.path.join(DATA_DIR, name + ".json")


def default_path(name):
    """Bundled default list (defaults/<name>.json), never changed by the program."""
    for base in (BUNDLE_DIR, APP_DIR):
        p = os.path.join(base, "defaults", name + ".json")
        if os.path.exists(p):
            return p
    return os.path.join(APP_DIR, "defaults", name + ".json")


def default_records(name):
    with open(default_path(name), encoding="utf-8") as f:
        return json.load(f)


def ensure_data():
    """Create the working data files from the defaults on first start."""
    os.makedirs(DATA_DIR, exist_ok=True)
    for name in ("ranks", "crew", "jobs"):
        dst = _path(name)
        src = default_path(name)
        if not os.path.exists(dst) and os.path.exists(src):
            shutil.copy(src, dst)
    snd_src = os.path.join(BUNDLE_DIR, "sounds")
    snd_dst = os.path.join(APP_DIR, "sounds")
    if os.path.isdir(snd_src) and snd_src != snd_dst:
        os.makedirs(snd_dst, exist_ok=True)
        for f in os.listdir(snd_src):
            if not os.path.exists(os.path.join(snd_dst, f)):
                shutil.copy(os.path.join(snd_src, f), snd_dst)
    tpl_dir = os.path.dirname(DEFAULT_TEMPLATE)
    src_tpl = os.path.join(BUNDLE_DIR, "templates", "ptw_template.docx")
    if not os.path.exists(DEFAULT_TEMPLATE) and os.path.exists(src_tpl):
        os.makedirs(tpl_dir, exist_ok=True)
        shutil.copy(src_tpl, DEFAULT_TEMPLATE)


def load(name, default=None):
    try:
        with open(_path(name), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(name, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = _path(name) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _path(name))


def load_settings():
    saved = load("settings", {}) or {}
    s = dict(DEFAULT_SETTINGS)
    s.update(saved)
    if "permit_numbering" not in saved:  # settings from version 1.2
        s["permit_numbering"] = "sequential" if saved.get("auto_number") else "day"
    s.pop("auto_number", None)
    return s


def resource(*parts):
    """A file shipped with the program (icons): bundle first, then the program folder."""
    for base in (BUNDLE_DIR, APP_DIR):
        p = os.path.join(base, *parts)
        if os.path.exists(p):
            return p
    return os.path.join(APP_DIR, *parts)


def template_path(settings):
    return settings.get("template_path") or DEFAULT_TEMPLATE


class Store:
    """In-memory copy of all data files."""

    def __init__(self):
        ensure_data()
        self.reload()

    def reload(self):
        self.ranks = load("ranks", [])
        self.crew = load("crew", [])
        self.jobs = load("jobs", [])
        self.settings = load_settings()
        self.history = load("history", [])
        for r in self.ranks:
            pc, loto = RANK_FLAGS.get(r["code"], (False, False))
            r.setdefault("can_pc", pc)
            r.setdefault("can_loto", loto)
        for j in self.jobs:
            j.setdefault("loto", False)
            j.setdefault("pc_ranks", [])

    def save_all(self):
        for name in ("ranks", "crew", "jobs", "settings", "history"):
            save(name, getattr(self, name))

    def rank(self, code):
        for r in self.ranks:
            if r["code"] == code:
                return r
        return {"code": code, "short": code, "full": code, "officer": False, "order": 99,
                "can_pc": False, "can_loto": False}

    def can_pc(self, member_id):
        m = self.member(member_id)
        return bool(m and self.rank(m["rank"]).get("can_pc"))

    def can_loto(self, member_id):
        m = self.member(member_id)
        return bool(m and self.rank(m["rank"]).get("can_loto"))

    def member(self, member_id):
        for m in self.crew:
            if m["id"] == member_id:
                return m
        return None

    def job(self, job_id):
        for j in self.jobs:
            if j["id"] == job_id:
                return j
        return None
