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
    "ship_name": "MSC Alix 3",
    "template_path": "",
    "output_dir": "",
    "ao_id": "ce",
    "time_issue": "08:00",
    "time_transfer": "12:00",
    "time_close": "20:00",
    "permits_per_day": 1,
    "no_repeat_days": 7,
    "auto_number": False,
    "next_permit_no": 1,
    "filename_pattern": "{date} {title}",
    "filename_date_format": "%Y-%m-%d",
    "fit_one_line": True,
    "min_font_size": 6.5,
    "language": "en",
    "ui_font_size": 8,
    "open_folder_after": True,
    "skip_weekdays": [],
}


def _path(name):
    return os.path.join(DATA_DIR, name + ".json")


def ensure_data():
    """Copy bundled default data files on first start (exe build)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    for name in ("ranks", "crew", "jobs"):
        dst = _path(name)
        src = os.path.join(BUNDLE_DIR, "data", name + ".json")
        if not os.path.exists(dst) and os.path.exists(src) and src != dst:
            shutil.copy(src, dst)
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
    s = dict(DEFAULT_SETTINGS)
    s.update(load("settings", {}) or {})
    return s


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

    def save_all(self):
        for name in ("ranks", "crew", "jobs", "settings", "history"):
            save(name, getattr(self, name))

    def rank(self, code):
        for r in self.ranks:
            if r["code"] == code:
                return r
        return {"code": code, "short": code, "full": code, "officer": False, "order": 99}

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
