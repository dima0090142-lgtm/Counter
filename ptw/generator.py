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


def sort_by_rank(store, ids):
    def key(mid):
        m = store.member(mid)
        return store.rank(m["rank"])["order"] if m else 99
    return sorted(ids, key=key)


def default_roles(store, crew_ids):
    """Who signs sections 5, 6 and 7.

    Officers in the team (lead first): the most junior accepts the permit (5),
    then hands over to the next one (6), the lead closes the permit (7).
    With one officer he signs 5 and 7, section 6 stays empty.
    """
    officers = [i for i in crew_ids
                if store.member(i) and store.rank(store.member(i)["rank"]).get("officer")]
    if not officers:
        officers = list(crew_ids)
    if not officers:
        return "", "", ""
    pc = officers[-1]
    transfer = officers[-2] if len(officers) >= 2 else ""
    close = officers[0]
    return pc, transfer, close


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

    def _pick(self, ranks, count, day, exclude, busy):
        pool = [m["id"] for m in self._active_members(ranks) if m["id"] not in exclude]
        free = [i for i in pool if i not in busy]
        if len(free) >= count:
            pool = free
        self.rng.shuffle(pool)
        pool.sort(key=lambda i: self._load(i, day))
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
                lead = e["crew"][0]
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

    def make_crew(self, job, day, busy=()):
        busy = set(busy)
        lead = self._pick(job.get("lead_ranks", []), 1, day, set(), busy)
        team = list(lead)
        lo, hi = job.get("officers", [0, 0])
        n = self.rng.randint(lo, hi)
        team += self._pick(job.get("officer_ranks", []), n, day, set(team), busy)
        lo, hi = job.get("ratings", [0, 0])
        n = self.rng.randint(lo, hi)
        team += self._pick(job.get("rating_ranks", []), n, day, set(team), busy)
        # lead stays first, the rest by rank order
        return team[:1] + sort_by_rank(self.store, team[1:])

    def make_permit(self, day, used_today=(), busy=()):
        job = self._choose_job(day, set(used_today))
        if job is None:
            return None
        crew = self.make_crew(job, day, busy)
        pc, transfer, close = default_roles(self.store, crew)
        return {"date": day.isoformat(), "job_id": job["id"], "crew": crew,
                "pc": pc, "transfer": transfer, "close": close}

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
