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


def pc_candidates(store, crew_ids, lead=None):
    """Team members allowed to sign as P.C., lead first, then by seniority."""
    pcs = sort_by_rank(store, [i for i in crew_ids if store.can_pc(i)])
    if lead in pcs:
        pcs = [lead] + [i for i in pcs if i != lead]
    return pcs


def default_roles(store, crew_ids, lead=None):
    """Who signs sections 5, 6 and 7 - only ranks allowed to be P.C. (2E, 3E, ETO...).

    The most junior of them accepts the permit (5) and hands it over to the next
    one (6); the lead (or the most senior) closes it (7). With one P.C. he signs
    5 and 7 and section 6 stays empty.
    """
    pcs = pc_candidates(store, crew_ids, lead)
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
    dates = {p["date"] for p in permits}
    existing = {d: 0 if replace_dates else sum(1 for h in store.history if h["date"] == d)
                for d in dates}
    batch = {d: sum(1 for p in permits if p["date"] == d) for d in dates}
    seen = {d: 0 for d in dates}
    out = []
    for p in permits:
        d = p["date"]
        seen[d] += 1
        if p.get("permit_no"):
            out.append(p["permit_no"])
            continue
        doy = parse_date(d).timetuple().tm_yday
        total = existing[d] + batch[d]
        out.append(str(doy) if total == 1 else f"{doy}-{existing[d] + seen[d]}")
    return out


# ---------- automatic plan ----------

class Planner:
    def __init__(self, store, rng=None):
        self.store = store
        self.rng = rng or random.Random()
        self.entries = []  # history + plan: dicts with date, job_id, crew

    def load_history(self, start):
        lo = start - dt.timedelta(days=LOOKBACK_DAYS)
        self.entries = [h for h in self.store.history
                        if lo <= parse_date(h["date"]) < start]

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

    def _pc_load(self, member_id, day):
        """How often the member signed as P.C. recently (for 2E / 3E taking turns)."""
        total = 0.0
        for e in self.entries:
            if member_id in (e.get("pc"), e.get("close")):
                age = (day - parse_date(e["date"])).days
                if 0 <= age <= LOOKBACK_DAYS:
                    total += 1.0 / (1 + age / 7)
        return total

    def _pick(self, ranks, count, day, exclude, busy, load=None):
        load = load or self._load
        pool = [m["id"] for m in self._active_members(ranks) if m["id"] not in exclude]
        free = [i for i in pool if i not in busy]
        if len(free) >= count:
            pool = free
        self.rng.shuffle(pool)
        pool.sort(key=lambda i: load(i, day))
        return pool[:count]

    def _last_used(self, job_id, before):
        dates = [parse_date(e["date"]) for e in self.entries
                 if e["job_id"] == job_id and parse_date(e["date"]) < before]
        return max(dates) if dates else None

    def _choose_job(self, day, used_today):
        s = self.store.settings
        jobs = [j for j in self.store.jobs
                if j.get("active", True) and j["id"] not in used_today
                and self._active_members(j.get("lead_ranks", []))]
        if not jobs:
            return None
        # who led the work yesterday / the day before: give others a turn
        recent_leads = {}
        for e in self.entries:
            age = (day - parse_date(e["date"])).days
            if e["crew"] and age in LEAD_PENALTY:
                lead = e.get("lead") or e["crew"][0]
                recent_leads[lead] = min(recent_leads.get(lead, 1.0), LEAD_PENALTY[age])
        ages, weights = [], []
        for j in jobs:
            last = self._last_used(j["id"], day)
            age = (day - last).days if last else LOOKBACK_DAYS
            leads = [m["id"] for m in self._active_members(j.get("lead_ranks", []))]
            factor = max(recent_leads.get(m, 1.0) for m in leads)
            ages.append(age)
            weights.append(age * factor)
        fresh = [(j, w) for j, a, w in zip(jobs, ages, weights) if a > s["no_repeat_days"]]
        if not fresh:  # every job was done recently: take the oldest ones
            oldest = max(ages)
            fresh = [(j, w) for j, a, w in zip(jobs, ages, weights) if a == oldest]
        js, ws = zip(*fresh)
        return self.rng.choices(js, weights=ws, k=1)[0]

    def make_team(self, job, day, busy=()):
        """Crew, lead, signatures and LOTO person for one job on one day."""
        busy = set(busy)
        lead = self._pick(job.get("lead_ranks", []), 1, day, set(), busy)
        team = list(lead)
        lo, hi = job.get("officers", [0, 0])
        n = self.rng.randint(lo, hi)
        team += self._pick(job.get("officer_ranks", []), n, day, set(team), busy)
        lo, hi = job.get("ratings", [0, 0])
        n = self.rng.randint(lo, hi)
        team += self._pick(job.get("rating_ranks", []), n, day, set(team), busy)
        if team and not any(self.store.can_pc(i) for i in team):
            # e.g. 4E (cadet) leads the work: 2E / 3E take turns as P.C.
            ranks = job.get("pc_ranks") or self.store.settings.get("pc_supervisor_ranks") or []
            team += self._pick(ranks, 1, day, set(team), busy, load=self._pc_load)
        lead_id = team[0] if team else ""
        crew = sort_by_rank(self.store, team)
        pc, transfer, close = default_roles(self.store, crew, lead_id)
        loto = pick_loto(self.store, crew, pc) if job.get("loto") else ""
        return {"crew": crew, "lead": lead_id, "pc": pc, "transfer": transfer,
                "close": close, "loto": loto}

    def make_crew(self, job, day, busy=()):
        return self.make_team(job, day, busy)["crew"]

    def make_permit(self, day, used_today=(), busy=()):
        job = self._choose_job(day, set(used_today))
        if job is None:
            return None
        return {"date": day.isoformat(), "job_id": job["id"], **self.make_team(job, day, busy)}

    def plan(self, start, end):
        self.load_history(start)
        result = []
        per_day = max(1, int(self.store.settings.get("permits_per_day", 1)))
        skip = set(self.store.settings.get("skip_weekdays") or [])
        for day in daterange(start, end):
            if day.weekday() in skip:
                continue
            used, busy = set(), set()
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
        """Replace one permit of a plan with a new random one."""
        day = parse_date(plan[index]["date"])
        others = [p for i, p in enumerate(plan) if i != index]
        self.load_history(parse_date(plan[0]["date"]))
        self.entries += others
        same_day = [p for p in others if p["date"] == plan[index]["date"]]
        used = {p["job_id"] for p in same_day} | {plan[index]["job_id"]}
        busy = {c for p in same_day for c in p["crew"]}
        new = self.make_permit(day, used, busy) or self.make_permit(day, used - {plan[index]["job_id"]}, busy)
        if new:
            plan[index] = new
        return plan
