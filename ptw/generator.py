"""Choosing jobs and crew for each day so that permits vary."""
import datetime as dt
import random

LOOKBACK_DAYS = 60
# weight factor for jobs whose lead led a permit N days ago
LEAD_PENALTY = {1: 0.1, 2: 0.4}


def parse_date(s):
    return dt.date.fromisoformat(s) if isinstance(s, str) else s


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


# ---------- text for the form ----------

def issued_to_text(store, ids, compact=False):
    parts = []
    for mid in ids:
        m = store.member(mid)
        if m:
            rank = m["rank"] if compact else store.rank(m["rank"])["short"]
            parts.append(f"{rank} {m['first_name'].upper()}")
    return ", ".join(parts)


def sign_text(store, member_id):
    m = store.member(member_id) if member_id else None
    if not m:
        return ""
    title = m.get("title") or store.rank(m["rank"])["full"]
    return f"{title} / {m['first_name']} {m['last_name']}"


def loto_text(store, member_id):
    """Short form for the narrow LOTO column: 'AEO Abhijith Remesan'."""
    m = store.member(member_id) if member_id else None
    return f"{m['rank']} {m['first_name']} {m['last_name']}" if m else ""


def sort_by_rank(store, ids):
    def key(mid):
        m = store.member(mid)
        return store.rank(m["rank"])["order"] if m else 99
    return sorted(ids, key=key)


def supervisor_ranks(store, job=None):
    """Ranks that become P.C. when the job lead cannot be P.C. (2E, 3E by default)."""
    return list((job or {}).get("pc_ranks") or store.settings.get("pc_supervisor_ranks") or [])


def pc_candidates(store, crew_ids, lead=None, sup_ranks=None):
    """Team members who sign as P.C., lead first, then by seniority.

    When the lead cannot be P.C. (4E cadet, 5E), only the supervisor ranks
    (2E / 3E) sign - not e.g. an AEO helping on a mechanical job."""
    pcs = sort_by_rank(store, [i for i in crew_ids if store.can_pc(i)])
    if lead and lead in crew_ids and not store.can_pc(lead) and sup_ranks:
        sup = [i for i in pcs if store.member(i)["rank"] in sup_ranks]
        pcs = sup or pcs
    if lead in pcs:
        pcs = [lead] + [i for i in pcs if i != lead]
    return pcs


def default_roles(store, crew_ids, lead=None, sup_ranks=None):
    """Who signs sections 5, 6 and 7 - only ranks allowed to be P.C. (2E, 3E, ETO...).

    One of them other than the lead accepts the permit (5) and hands it over (6);
    the lead (or the most senior) closes it (7). With one P.C. he signs 5 and 7
    and section 6 stays empty.
    """
    pcs = pc_candidates(store, crew_ids, lead, sup_ranks)
    if not pcs:
        return "", "", ""
    pc = pcs[-1]
    transfer = pcs[-2] if len(pcs) >= 2 else ""
    return pc, transfer, pcs[0]


def loto_candidates(store):
    """Everybody on board who may apply LOTO, preferred ranks (ETO / AEO) first."""
    pref = store.settings.get("loto_preferred_ranks") or []
    ms = [m for m in store.crew if m.get("active", True) and store.can_loto(m["id"])]
    ms.sort(key=lambda m: (m["rank"] not in pref, pref.index(m["rank"]) if m["rank"] in pref
                           else 0, store.rank(m["rank"])["order"]))
    return [m["id"] for m in ms]


def pick_loto(store, crew_ids, pc=""):
    """Default LOTO person: the electrician (ETO / AEO) if on board, else the P.C."""
    cands = loto_candidates(store)
    pref = set(store.settings.get("loto_preferred_ranks") or [])
    for mid in cands:
        if store.member(mid)["rank"] in pref:
            return mid
    if pc and pc in cands:
        return pc
    for mid in crew_ids:
        if mid in cands:
            return mid
    return cands[0] if cands else ""


def permit_numbers(store, permits, replace_dates=False):
    """Consecutive permit numbers for a batch (permits that already have one keep it).

    "day": day of the year - 285, or 285-1, 285-2 ... when there are several that day.
    "sequential": next_permit_no, +1 each.  "blank": empty (written by pen).
    """
    s = store.settings
    mode = s.get("permit_numbering", "day")
    if mode == "sequential":
        n = int(s.get("next_permit_no", 1))
        out = []
        for p in permits:
            if p.get("permit_no"):
                out.append(p["permit_no"])
            else:
                out.append(str(n))
                n += 1
        return out
    if mode != "day":
        return [p.get("permit_no") or "" for p in permits]
    def suffix(no, doy):
        """'285' -> 1, '285-3' -> 3, anything else -> 0."""
        no = str(no or "")
        if no == str(doy):
            return 1
        if no.startswith(f"{doy}-") and no[len(str(doy)) + 1:].isdigit():
            return int(no[len(str(doy)) + 1:])
        return 0

    out = []
    used = {}   # date -> highest suffix already taken
    count = {}  # date -> permits that day (history + batch)
    for d in {p["date"] for p in permits}:
        doy = parse_date(d).timetuple().tm_yday
        olds = [] if replace_dates else [h.get("permit_no") for h in store.history if h["date"] == d]
        mine = [p.get("permit_no") for p in permits if p["date"] == d and p.get("permit_no")]
        used[d] = max([suffix(n, doy) for n in olds + mine] or [0])
        count[d] = len(olds) + sum(1 for p in permits if p["date"] == d)
    for p in permits:
        d = p["date"]
        if p.get("permit_no"):
            out.append(p["permit_no"])
            continue
        doy = parse_date(d).timetuple().tm_yday
        if count[d] == 1 and used[d] == 0:
            out.append(str(doy))
            used[d] = 1
        else:
            used[d] += 1
            out.append(f"{doy}-{used[d]}")
    return out


def check_permit(store, p):
    """Problems that must stop a permit from being written (empty list = OK)."""
    problems = []
    if not store.job(p.get("job_id")):
        problems.append("job not in the list")
    crew = p.get("crew") or []
    if not crew or any(store.member(i) is None for i in crew):
        problems.append("crew member missing")
    for role in ("pc", "close"):
        if not p.get(role):
            problems.append("no P.C.")
            break
    for role in ("pc", "transfer", "close"):
        mid = p.get(role)
        if mid and (mid not in crew or not store.can_pc(mid)):
            problems.append(f"{mid} cannot sign as P.C.")
    if p.get("loto") and not store.can_loto(p["loto"]):
        problems.append(f"{p['loto']} cannot apply LOTO")
    return sorted(set(problems))


# ---------- automatic plan ----------

class Planner:
    def __init__(self, store, rng=None):
        self.store = store
        self.rng = rng or random.Random()
        self.entries = []  # history + plan: dicts with date, job_id, crew

    def load_history(self, start, end=None):
        """Permits from LOOKBACK_DAYS before start up to the end of the plan (and the
        no-repeat window after it), so that permits already made count too."""
        lo = start - dt.timedelta(days=LOOKBACK_DAYS)
        hi = (end or start) + dt.timedelta(days=int(self.store.settings.get("no_repeat_days", 7)))
        self.entries = [h for h in self.store.history if lo <= parse_date(h["date"]) <= hi]

    def _active_members(self, ranks):
        return [m for m in self.store.crew if m.get("active", True) and m["rank"] in ranks]

    def _load(self, member_id, day):
        """Weighted count of recent permits: recent days count more."""
        total = 0.0
        for e in self.entries:
            if member_id in e["crew"]:
                age = (day - parse_date(e["date"])).days
                if 0 <= age <= LOOKBACK_DAYS:
                    total += 1.0 / (1 + age / 7)
        return total

    def _pc_turn(self, member_id, day):
        """For 2E / 3E taking turns as P.C.: the one whose last P.C. signature is
        older goes first (ties: fewer recent signatures)."""
        last, total = None, 0.0
        for e in self.entries:
            if member_id in (e.get("pc"), e.get("close")):
                age = (day - parse_date(e["date"])).days
                if 0 <= age <= LOOKBACK_DAYS:
                    total += 1.0 / (1 + age / 7)
                    last = age if last is None else min(last, age)
        return (-(LOOKBACK_DAYS + 1 if last is None else last), total)

    def _pick(self, ranks, count, day, exclude, busy, load=None):
        load = load or self._load
        pool = [m["id"] for m in self._active_members(ranks) if m["id"] not in exclude]
        free = [i for i in pool if i not in busy]
        if len(free) >= count:
            pool = free
        self.rng.shuffle(pool)
        pool.sort(key=lambda i: load(i, day))
        return pool[:count]

    def _group(self, job_id):
        j = self.store.job(job_id) or {}
        return j.get("group") or job_id

    def _dates_by_key(self):
        """{job id or group: [day ordinals]}, rebuilt when entries were added."""
        if getattr(self, "_idx_len", None) != len(self.entries):
            idx = {}
            for e in self.entries:
                o = parse_date(e["date"]).toordinal()
                jid = e.get("job_id")
                idx.setdefault(("job", jid), []).append(o)
                idx.setdefault(("group", self._group(jid)), []).append(o)
            self._idx, self._idx_len = idx, len(self.entries)
        return self._idx

    def _gap(self, job, day):
        """Days to the nearest permit of the same job (or job group), before or after."""
        idx = self._dates_by_key()
        key = ("group", job["group"]) if job.get("group") else ("job", job["id"])
        dates = idx.get(key)
        if not dates:
            return LOOKBACK_DAYS
        o = day.toordinal()
        return min(abs(o - d) for d in dates)

    def _can_get_pc(self, job):
        if any(self.store.can_pc(m["id"]) for m in self._active_members(job.get("lead_ranks", []))):
            return True
        ranks = supervisor_ranks(self.store, job)
        return any(self.store.can_pc(m["id"]) for m in self._active_members(ranks)) or \
            any(self.store.can_pc(m["id"]) for m in self.store.crew if m.get("active", True))

    def _choose_job(self, day, used_today, busy=()):
        s = self.store.settings
        jobs = [j for j in self.store.jobs
                if j.get("active", True) and j["id"] not in used_today
                and self._active_members(j.get("lead_ranks", [])) and self._can_get_pc(j)]
        if not jobs:
            return None
        busy = set(busy)
        # who led the work yesterday / the day before: give others a turn
        recent_leads = {}
        for e in self.entries:
            age = (day - parse_date(e["date"])).days
            if e["crew"] and age in LEAD_PENALTY:
                lead = e.get("lead") or e["crew"][0]
                recent_leads[lead] = min(recent_leads.get(lead, 1.0), LEAD_PENALTY[age])
        gaps, weights = [], []
        for j in jobs:
            gap = self._gap(j, day)
            leads = [m["id"] for m in self._active_members(j.get("lead_ranks", []))]
            factor = max(recent_leads.get(m, 1.0) for m in leads)
            if busy and all(m in busy for m in leads):
                factor *= 0.05  # second permit of the day: prefer another lead
            gaps.append(gap)
            weights.append(max(gap, 1) * factor)
        fresh = [(j, w) for j, g, w in zip(jobs, gaps, weights) if g > s["no_repeat_days"]]
        if not fresh:  # every job was done recently: take the longest-ago ones
            far = max(gaps)
            fresh = [(j, w) for j, g, w in zip(jobs, gaps, weights) if g == far]
        js, ws = zip(*fresh)
        return self.rng.choices(js, weights=ws, k=1)[0]

    def make_team(self, job, day, busy=()):
        """Crew, lead and signatures for one job on one day (LOTO stays empty)."""
        busy = set(busy)
        lead = self._pick(job.get("lead_ranks", []), 1, day, set(), busy)
        team = list(lead)
        lo, hi = job.get("officers", [0, 0])
        n = self.rng.randint(lo, hi)
        team += self._pick(job.get("officer_ranks", []), n, day, set(team), busy)
        lo, hi = job.get("ratings", [0, 0])
        n = self.rng.randint(lo, hi)
        team += self._pick(job.get("rating_ranks", []), n, day, set(team), busy)
        sup = supervisor_ranks(self.store, job)
        if team and not self.store.can_pc(team[0]):
            # e.g. 4E (cadet) leads the work: 2E / 3E take turns as P.C.
            if not any(self.store.can_pc(i) and self.store.member(i)["rank"] in sup for i in team):
                pcs = [m["rank"] for m in self.store.crew
                       if m.get("active", True) and self.store.can_pc(m["id"]) and m["rank"] in sup]
                if not pcs:  # supervisor ranks not on board: anybody who may be P.C.
                    pcs = [m["rank"] for m in self.store.crew
                           if m.get("active", True) and self.store.can_pc(m["id"])]
                team += self._pick(sorted(set(pcs)), 1, day, set(team), busy, load=self._pc_turn)
        lead_id = team[0] if team else ""
        crew = sort_by_rank(self.store, team)
        pc, transfer, close = default_roles(self.store, crew, lead_id, sup)
        # LOTO stays empty: the user ticks it himself (Edit... / Manual)
        return {"crew": crew, "lead": lead_id, "pc": pc, "transfer": transfer,
                "close": close, "loto": ""}

    def make_crew(self, job, day, busy=()):
        return self.make_team(job, day, busy)["crew"]

    def make_permit(self, day, used_today=(), busy=()):
        job = self._choose_job(day, set(used_today), busy)
        if job is None:
            return None
        return {"date": day.isoformat(), "job_id": job["id"], **self.make_team(job, day, busy)}

    def _day_start(self, day, exclude=None):
        """Jobs and people already used on this day (history or other plan rows)."""
        same = [e for e in self.entries if e["date"] == day.isoformat() and e is not exclude]
        return {e["job_id"] for e in same}, {c for e in same for c in e["crew"]}

    def plan(self, start, end):
        self.load_history(start, end)
        result = []
        per_day = max(1, int(self.store.settings.get("permits_per_day", 1)))
        skip = set(self.store.settings.get("skip_weekdays") or [])
        for day in daterange(start, end):
            if day.weekday() in skip:
                continue
            used, busy = self._day_start(day)
            for _ in range(per_day):
                p = self.make_permit(day, used, busy)
                if p is None:
                    break
                used.add(p["job_id"])
                busy.update(p["crew"])
                self.entries.append(p)
                result.append(p)
        return result

    def reroll(self, plan, index):
        """Replace one permit of a plan with a new random one (same rules as plan())."""
        day = parse_date(plan[index]["date"])
        dates = [parse_date(p["date"]) for p in plan]
        self.load_history(min(dates), max(dates))
        old = plan[index]
        self.entries += [p for i, p in enumerate(plan) if i != index]
        used, busy = self._day_start(day)
        used.add(old["job_id"])
        new = self.make_permit(day, used, busy) or self.make_permit(day, used - {old["job_id"]}, busy)
        if new:
            plan[index] = new
        return plan
