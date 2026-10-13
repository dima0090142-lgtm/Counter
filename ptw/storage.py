"""JSON storage for ranks, crew, jobs, settings and history."""
import hashlib
import json
import os
import re
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

DATA_VERSION = 3  # 1.3: AE instead of DG, LOTO / P.C. flags, job groups

# files shipped by older versions: replaced by the new ones when the user did not
# change them (md5 of the file)
OLD_TEMPLATE_MD5 = {"37c3979155cffde49596da4bdf263d54", "786226cd7645c860dea91d312ef33458"}
OLD_SOUND_MD5 = {"ee7a23fbbfd05f593573a13bbe485b3a", "c5bc6e8e15539ad75a8900cdd401e515",
                 "f8123d590658e00bc32c6bd54c24d9a4", "7f035dc8c5a48eaaae0f5fd8dc96a3ff",
                 "2e1a66de72014e1b9422585850bd715d", "17bbab2e55d1567ccc8bbf04da85504f"}

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


def md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()  # noqa: S324 - file identity only


def _backup(path, suffix):
    """path.ext -> path_<suffix>.ext (kept if it exists already)."""
    base, ext = os.path.splitext(path)
    dst = f"{base}_{suffix}{ext}"
    if not os.path.exists(dst):
        shutil.copy(path, dst)
    return dst


def ensure_data():
    """Create the working data files from the defaults on first start and replace
    template / sounds of older versions that the user did not change.

    Returns the names of the data files created now (a fresh installation)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    fresh = set()
    for name in ("ranks", "crew", "jobs"):
        dst = _path(name)
        src = default_path(name)
        if not os.path.exists(dst) and os.path.exists(src):
            shutil.copy(src, dst)
            fresh.add(name)
    snd_src = os.path.join(BUNDLE_DIR, "sounds")
    snd_dst = os.path.join(APP_DIR, "sounds")
    if os.path.isdir(snd_src) and os.path.abspath(snd_src) != os.path.abspath(snd_dst):
        os.makedirs(snd_dst, exist_ok=True)
        for f in os.listdir(snd_src):
            dst = os.path.join(snd_dst, f)
            if not os.path.exists(dst) or md5(dst) in OLD_SOUND_MD5:
                shutil.copy(os.path.join(snd_src, f), dst)
    tpl_dir = os.path.dirname(DEFAULT_TEMPLATE)
    src_tpl = os.path.join(BUNDLE_DIR, "templates", "ptw_template.docx")
    if os.path.exists(src_tpl) and os.path.abspath(src_tpl) != os.path.abspath(DEFAULT_TEMPLATE):
        if not os.path.exists(DEFAULT_TEMPLATE):
            os.makedirs(tpl_dir, exist_ok=True)
            shutil.copy(src_tpl, DEFAULT_TEMPLATE)
        elif md5(DEFAULT_TEMPLATE) in OLD_TEMPLATE_MD5:  # unchanged template of v1.0-1.2
            _backup(DEFAULT_TEMPLATE, "old")
            shutil.copy(src_tpl, DEFAULT_TEMPLATE)
    return fresh


def dg_to_ae(text):
    """Diesel generator -> Auxiliary engine (renamed in 1.3)."""
    text = re.sub(r"\bDG\b", "AE", text)
    return text.replace("Diesel generator", "Auxiliary engine").replace("D/G", "A/E")


JOB_DEFAULT_FIELDS = ("title", "location", "plant", "work", "ra_no", "lead_ranks",
                      "officer_ranks", "officers", "rating_ranks", "ratings")


def migrate_jobs(jobs, history):
    """Bring a v1.2 job list up to date, keeping what the user changed.

    - dg_* jobs become the new ae_* jobs (history follows the new id);
    - a field still equal to the old default gets the new default (3E for STP ...);
    - loto / pc_ranks / group are taken from the new defaults;
    - jobs that are new in this version are added.
    Returns (jobs, history, changed)."""
    try:
        with open(default_path(os.path.join("upgrade", "jobs_v1.2")), encoding="utf-8") as f:
            old_defaults = {j["id"]: j for j in json.load(f)}
        new_defaults = {j["id"]: j for j in default_records("jobs")}
    except (OSError, ValueError):
        return jobs, history, False
    idmap = {}
    for j in jobs:
        oid = j["id"]
        nid = "ae_" + oid[3:] if oid.startswith("dg_") and "ae_" + oid[3:] in new_defaults else oid
        old, new = old_defaults.get(oid), new_defaults.get(nid)
        if nid != oid:
            j["id"] = nid
            idmap[oid] = nid
        for k in JOB_DEFAULT_FIELDS:
            if new is not None and old is not None and j.get(k) == old.get(k):
                j[k] = new[k]
            elif nid != oid and isinstance(j.get(k), str):
                j[k] = dg_to_ae(j[k])
        for k, empty in (("loto", False), ("pc_ranks", []), ("group", "")):
            if k not in j:
                j[k] = new[k] if new is not None and k in new else empty
    have = {j["id"] for j in jobs}
    for jid, new in new_defaults.items():
        if jid not in have and jid not in old_defaults and jid not in idmap.values():
            jobs.append(dict(new))
    for h in history:
        if h.get("job_id") in idmap:
            h["job_id"] = idmap[h["job_id"]]
    return jobs, history, True


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
    # settings from version 1.2: the consecutive number is now the day of the year
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
        self.fresh = ensure_data()
        self.reload()
        self._upgrade()

    def _upgrade(self):
        """One-time update of the data of an older version (backups kept in data/)."""
        s = self.settings
        if int(s.get("data_version", 0)) >= DATA_VERSION:
            return
        raw = load("jobs", []) or []  # as saved (reload() fills missing keys)
        if "jobs" not in self.fresh and raw and not all("loto" in j for j in raw):
            # job list of v1.2: back up, then update it
            _backup(_path("jobs"), "backup_v1.2")
            if os.path.exists(_path("history")):
                _backup(_path("history"), "backup_v1.2")
            jobs, history, _ = migrate_jobs(raw, load("history", []) or [])
            save("jobs", jobs)
            save("history", history)
        s["data_version"] = DATA_VERSION
        save("settings", s)
        keep = dict(s)
        self.reload()
        self.settings.update(keep)

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
            j.setdefault("group", "")

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
