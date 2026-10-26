"""Core logic for the Smart Healthcare Project Management System.

Database access, validation, change control, CPM scheduling, delay impact,
Earned Value Management (EVM), alerts and risk ranking. No UI code here.
"""
import os
import sqlite3
from datetime import date, datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "healthcare_pm.db")
SCHEMA_PATH = os.path.join(BASE, "schema.sql")
ONE = timedelta(days=1)


class ValidationError(ValueError):
    """Raised when user input or a business rule check fails."""


# ----------------------------------------------------------------- database
def connect(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn, seed=False):
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    if seed and conn.execute("SELECT COUNT(*) FROM charter").fetchone()[0] == 0:
        seed_sample_data(conn)


def reset_db(conn):
    conn.execute("PRAGMA foreign_keys = OFF")
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for t in tables:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    init_db(conn, seed=True)


# --------------------------------------------------------------- validation
def _text(v, name, required=True):
    v = (v or "").strip() if isinstance(v, str) or v is None else str(v).strip()
    if required and not v:
        raise ValidationError(f"{name} is required.")
    return v


def _num(v, name, lo=None, hi=None, integer=False):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be a number.")
    if x != x or x in (float("inf"), float("-inf")):
        raise ValidationError(f"{name} must be a finite number.")
    if lo is not None and x < lo:
        raise ValidationError(f"{name} must be at least {lo:g}.")
    if hi is not None and x > hi:
        raise ValidationError(f"{name} must be at most {hi:g}.")
    if integer:
        if x != int(x):
            raise ValidationError(f"{name} must be a whole number.")
        return int(x)
    return x


def parse_date(v, name="Date"):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"{name} must be a valid date (YYYY-MM-DD).")


def _commit(conn):
    conn.commit()


# ------------------------------------------------- 1. charter, plan, status
def get_charter(conn):
    return dict(conn.execute("SELECT * FROM charter WHERE id=1").fetchone())


def save_charter(conn, name, objectives, stakeholders, scope_boundaries,
                 budget, start_date, deadline, manager):
    name = _text(name, "Project name")
    objectives = _text(objectives, "Objectives")
    stakeholders = _text(stakeholders, "Stakeholders")
    scope_boundaries = _text(scope_boundaries, "Scope boundaries")
    budget = _num(budget, "Approved budget", lo=1)
    s, e = parse_date(start_date, "Start date"), parse_date(deadline, "Deadline")
    if e <= s:
        raise ValidationError("Deadline must be after the start date.")
    conn.execute(
        """UPDATE charter SET name=?, objectives=?, stakeholders=?, scope_boundaries=?,
           approved_budget=?, start_date=?, deadline=?, manager=? WHERE id=1""",
        (name, objectives, stakeholders, scope_boundaries, budget,
         s.isoformat(), e.isoformat(), _text(manager, "Manager", False)))
    _commit(conn)


def get_plan(conn):
    return dict(conn.execute("SELECT * FROM plan WHERE id=1").fetchone())


def save_plan(conn, scope_plan, schedule_plan, cost_plan, quality_plan):
    for v, n in ((scope_plan, "Scope plan"), (schedule_plan, "Schedule plan"),
                 (cost_plan, "Cost plan"), (quality_plan, "Quality plan")):
        _text(v, n)
    conn.execute("UPDATE plan SET scope_plan=?, schedule_plan=?, cost_plan=?, quality_plan=? WHERE id=1",
                 (scope_plan.strip(), schedule_plan.strip(), cost_plan.strip(), quality_plan.strip()))
    _commit(conn)


def set_status_date(conn, d):
    d = parse_date(d, "Status date")
    ch = get_charter(conn)
    if d < parse_date(ch["start_date"]):
        raise ValidationError("Status date cannot be before the project start date.")
    conn.execute("UPDATE charter SET status_date=? WHERE id=1", (d.isoformat(),))
    _commit(conn)


def set_project_status(conn, status):
    if status not in ("Initiating", "Planning", "Executing", "Monitoring", "Closed"):
        raise ValidationError("Invalid project status.")
    if status == "Closed":
        raise ValidationError("Use the Closure tab to close the project.")
    conn.execute("UPDATE charter SET status=?, closed=0 WHERE id=1", (status,))
    _commit(conn)


def get_thresholds(conn):
    t = {"cpi_warn": 0.95, "spi_warn": 0.95, "critical": 0.85}
    for r in conn.execute("SELECT key, value FROM settings"):
        t[r["key"]] = r["value"]
    return t


def set_thresholds(conn, cpi_warn, spi_warn, critical):
    cpi_warn = _num(cpi_warn, "CPI warning threshold", 0.1, 1.5)
    spi_warn = _num(spi_warn, "SPI warning threshold", 0.1, 1.5)
    critical = _num(critical, "Critical threshold", 0.1, 1.5)
    if critical > min(cpi_warn, spi_warn):
        raise ValidationError("Critical threshold must not exceed the warning thresholds.")
    for k, v in (("cpi_warn", cpi_warn), ("spi_warn", spi_warn), ("critical", critical)):
        conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))
    _commit(conn)


def add_team_member(conn, name, role, responsibilities=""):
    name, role = _text(name, "Name"), _text(role, "Role")
    if conn.execute("SELECT 1 FROM team WHERE lower(name)=lower(?)", (name,)).fetchone():
        raise ValidationError("A team member with this name already exists.")
    conn.execute("INSERT INTO team(name, role, responsibilities) VALUES(?,?,?)",
                 (name, role, _text(responsibilities, "Responsibilities", False)))
    _commit(conn)


def delete_team_member(conn, member_id):
    n = conn.execute("SELECT COUNT(*) FROM activities WHERE assignee_id=?", (member_id,)).fetchone()[0]
    if n:
        raise ValidationError(f"Cannot remove: member is assigned to {n} activities. Reassign them first.")
    conn.execute("DELETE FROM team WHERE id=?", (member_id,))
    _commit(conn)


def add_milestone(conn, name, due_date, activity_id=None):
    name = _text(name, "Milestone name")
    due = parse_date(due_date, "Due date")
    ch = get_charter(conn)
    if due < parse_date(ch["start_date"]):
        raise ValidationError("Milestone cannot be due before the project start date.")
    conn.execute("INSERT INTO milestones(name, due_date, activity_id) VALUES(?,?,?)",
                 (name, due.isoformat(), activity_id))
    _commit(conn)


def set_milestone_achieved(conn, milestone_id, achieved):
    m = conn.execute("SELECT * FROM milestones WHERE id=?", (milestone_id,)).fetchone()
    if not m:
        raise ValidationError("Milestone not found.")
    if achieved and m["activity_id"]:
        pct = conn.execute("SELECT percent_complete FROM activities WHERE id=?", (m["activity_id"],)).fetchone()[0]
        if pct < 100:
            raise ValidationError("Linked activity is not 100% complete, so the milestone cannot be marked achieved.")
    conn.execute("UPDATE milestones SET achieved=? WHERE id=?", (1 if achieved else 0, milestone_id))
    _commit(conn)


def closure_blockers(conn):
    b = []
    n = conn.execute("SELECT COUNT(*) FROM change_requests WHERE status='Pending'").fetchone()[0]
    if n:
        b.append(f"{n} pending change request(s)")
    n = conn.execute("SELECT COUNT(*) FROM defects WHERE severity='Critical' AND status IN ('Open','In Progress')").fetchone()[0]
    if n:
        b.append(f"{n} unresolved critical defect(s)")
    snap = snapshot(conn)
    n = sum(1 for a in snap["in_scope"] if a["percent_complete"] < 100)
    if n:
        b.append(f"{n} in-scope activity(ies) not 100% complete")
    return b


def close_project(conn, notes):
    notes = _text(notes, "Closure notes / lessons learned")
    blockers = closure_blockers(conn)
    if blockers:
        raise ValidationError("Cannot close project: " + "; ".join(blockers) + ".")
    conn.execute("UPDATE charter SET closed=1, status='Closed', closure_notes=? WHERE id=1", (notes,))
    _commit(conn)


# ---------------------------------------------------- 2. scope management
def add_requirement(conn, title, description, priority):
    title = _text(title, "Title")
    if priority not in ("High", "Medium", "Low"):
        raise ValidationError("Priority must be High, Medium or Low.")
    n = conn.execute("SELECT COALESCE(MAX(id),0)+1 FROM requirements").fetchone()[0]
    conn.execute("INSERT INTO requirements(code,title,description,priority,status) VALUES(?,?,?,?, 'Proposed')",
                 (f"R{n}", title, _text(description, "Description", False), priority))
    _commit(conn)


def update_requirement(conn, req_id, title, description, priority):
    title = _text(title, "Title")
    if priority not in ("High", "Medium", "Low"):
        raise ValidationError("Priority must be High, Medium or Low.")
    conn.execute("UPDATE requirements SET title=?, description=?, priority=? WHERE id=?",
                 (title, _text(description, "Description", False), priority, req_id))
    refresh_wbs(conn)


def set_requirement_status(conn, req_id, status):
    if status not in ("Proposed", "Approved", "Rejected"):
        raise ValidationError("Invalid requirement status.")
    pending = conn.execute("SELECT 1 FROM change_requests WHERE requirement_id=? AND status='Pending'", (req_id,)).fetchone()
    if pending and status in ("Approved", "Rejected"):
        raise ValidationError("This requirement has a pending change request. Decide it through the change request so cost and schedule stay consistent.")
    if status == "Rejected":
        n = conn.execute("SELECT COUNT(*) FROM activities WHERE requirement_id=?", (req_id,)).fetchone()[0]
        if n:
            raise ValidationError(f"Cannot reject: {n} activity(ies) are linked to this requirement. Delete or relink them first.")
    if status == "Proposed":
        started = conn.execute("SELECT COUNT(*) FROM activities WHERE requirement_id=? AND (percent_complete>0 OR actual_cost>0)", (req_id,)).fetchone()[0]
        if started:
            raise ValidationError("Cannot move a requirement with recorded progress back to Proposed.")
    conn.execute("UPDATE requirements SET status=? WHERE id=?", (status, req_id))
    refresh_wbs(conn)


def refresh_wbs(conn):
    """Rebuild the hierarchical WBS: Project > Deliverable (approved requirement) > Work Package (activity)."""
    conn.execute("UPDATE activities SET wbs_id=NULL")
    conn.execute("DELETE FROM wbs")
    ch = get_charter(conn)

    def ins(code, name, parent, kind, req):
        return conn.execute("INSERT INTO wbs(code,name,parent_id,level_type,requirement_id) VALUES(?,?,?,?,?)",
                            (code, name, parent, kind, req)).lastrowid

    root = ins("1", ch["name"], None, "Project", None)
    reqs = conn.execute("SELECT * FROM requirements WHERE status='Approved' ORDER BY id").fetchall()
    for i, r in enumerate(reqs, 1):
        d = ins(f"1.{i}", r["title"], root, "Deliverable", r["id"])
        for j, a in enumerate(conn.execute("SELECT id,name FROM activities WHERE requirement_id=? ORDER BY id", (r["id"],)), 1):
            w = ins(f"1.{i}.{j}", a["name"], d, "Work Package", r["id"])
            conn.execute("UPDATE activities SET wbs_id=? WHERE id=?", (w, a["id"]))
    _commit(conn)


def submit_change_request(conn, title, requirement_id, justification, cost_impact, weeks):
    title = _text(title, "Title")
    justification = _text(justification, "Justification")
    cost = _num(cost_impact, "Cost impact", lo=0)
    weeks = _num(weeks, "Schedule impact (weeks)", lo=0, hi=104)
    if requirement_id:
        r = conn.execute("SELECT status FROM requirements WHERE id=?", (requirement_id,)).fetchone()
        if not r:
            raise ValidationError("Linked requirement not found.")
        if r["status"] == "Approved":
            raise ValidationError("Linked requirement is already approved.")
        if conn.execute("SELECT 1 FROM change_requests WHERE requirement_id=? AND status='Pending'", (requirement_id,)).fetchone():
            raise ValidationError("A pending change request already exists for this requirement.")
        if r["status"] == "Rejected":
            conn.execute("UPDATE requirements SET status='Proposed' WHERE id=?", (requirement_id,))
    conn.execute("""INSERT INTO change_requests(title,requirement_id,justification,cost_impact,schedule_impact_weeks,status,submitted_on)
                    VALUES(?,?,?,?,?, 'Pending', ?)""",
                 (title, requirement_id or None, justification, cost, weeks, date.today().isoformat()))
    _commit(conn)


def _get_cr(conn, cr_id):
    cr = conn.execute("SELECT * FROM change_requests WHERE id=?", (cr_id,)).fetchone()
    if not cr:
        raise ValidationError("Change request not found.")
    if cr["status"] != "Pending":
        raise ValidationError(f"Only pending change requests can be decided (this one is {cr['status']}).")
    return cr


def approve_change_request(conn, cr_id):
    cr = _get_cr(conn, cr_id)
    if not (cr["justification"] or "").strip():
        raise ValidationError("A change request without justification cannot be approved.")
    if cr["requirement_id"]:
        conn.execute("UPDATE requirements SET status='Approved' WHERE id=?", (cr["requirement_id"],))
    conn.execute("UPDATE change_requests SET status='Approved', decided_on=? WHERE id=?",
                 (date.today().isoformat(), cr_id))
    refresh_wbs(conn)


def reject_change_request(conn, cr_id):
    cr = _get_cr(conn, cr_id)
    if cr["requirement_id"]:
        conn.execute("UPDATE requirements SET status='Rejected' WHERE id=? AND status='Proposed'", (cr["requirement_id"],))
    conn.execute("UPDATE change_requests SET status='Rejected', decided_on=? WHERE id=?",
                 (date.today().isoformat(), cr_id))
    _commit(conn)


# ----------------------------------------- 3. activities and dependencies
def add_activity(conn, name, requirement_id, assignee_id, duration, cost):
    name = _text(name, "Activity name")
    dur = _num(duration, "Duration (days)", lo=1, hi=1000, integer=True)
    cost = _num(cost, "Planned cost", lo=0)
    r = conn.execute("SELECT status FROM requirements WHERE id=?", (requirement_id,)).fetchone()
    if not r:
        raise ValidationError("Every activity must be linked to a requirement.")
    if r["status"] == "Rejected":
        raise ValidationError("Cannot add an activity for a rejected requirement.")
    if assignee_id and not conn.execute("SELECT 1 FROM team WHERE id=?", (assignee_id,)).fetchone():
        raise ValidationError("Assignee not found.")
    conn.execute("INSERT INTO activities(name,requirement_id,assignee_id,duration_days,planned_cost) VALUES(?,?,?,?,?)",
                 (name, requirement_id, assignee_id or None, dur, cost))
    refresh_wbs(conn)


def delete_activity(conn, activity_id):
    a = conn.execute("SELECT percent_complete, actual_cost FROM activities WHERE id=?", (activity_id,)).fetchone()
    if not a:
        raise ValidationError("Activity not found.")
    if a["percent_complete"] > 0 or a["actual_cost"] > 0:
        raise ValidationError("Cannot delete an activity that has recorded progress or cost.")
    conn.execute("DELETE FROM activities WHERE id=?", (activity_id,))
    refresh_wbs(conn)


def _reachable(conn, start, target):
    """True if `target` can be reached from `start` following predecessor links."""
    seen, stack = set(), [start]
    while stack:
        n = stack.pop()
        if n == target:
            return True
        if n in seen:
            continue
        seen.add(n)
        stack += [r[0] for r in conn.execute("SELECT predecessor_id FROM dependencies WHERE activity_id=?", (n,))]
    return False


def add_dependency(conn, activity_id, predecessor_id):
    if activity_id == predecessor_id:
        raise ValidationError("An activity cannot depend on itself.")
    for i in (activity_id, predecessor_id):
        if not conn.execute("SELECT 1 FROM activities WHERE id=?", (i,)).fetchone():
            raise ValidationError("Activity not found.")
    if conn.execute("SELECT 1 FROM dependencies WHERE activity_id=? AND predecessor_id=?", (activity_id, predecessor_id)).fetchone():
        raise ValidationError("This dependency already exists.")
    if _reachable(conn, predecessor_id, activity_id):
        raise ValidationError("This dependency would create a circular chain.")
    conn.execute("INSERT INTO dependencies(activity_id, predecessor_id) VALUES(?,?)", (activity_id, predecessor_id))
    _commit(conn)


def remove_dependency(conn, activity_id, predecessor_id):
    conn.execute("DELETE FROM dependencies WHERE activity_id=? AND predecessor_id=?", (activity_id, predecessor_id))
    _commit(conn)


def update_progress(conn, activity_id, percent, actual_cost, delay_days):
    a = conn.execute("""SELECT a.*, r.status AS req_status FROM activities a
                        JOIN requirements r ON r.id=a.requirement_id WHERE a.id=?""", (activity_id,)).fetchone()
    if not a:
        raise ValidationError("Activity not found.")
    pct = _num(percent, "Percent complete", 0, 100)
    cost = _num(actual_cost, "Actual cost", lo=0)
    delay = _num(delay_days, "Delay (days)", lo=0, hi=1000, integer=True)
    if a["req_status"] != "Approved" and (pct > 0 or cost > 0):
        raise ValidationError("This activity belongs to an unapproved requirement; it is outside the approved scope, so progress and cost cannot be recorded.")
    if pct >= 100:
        n = conn.execute("""SELECT COUNT(*) FROM defects WHERE activity_id=? AND severity='Critical'
                            AND status IN ('Open','In Progress')""", (activity_id,)).fetchone()[0]
        if n:
            raise ValidationError(f"Cannot mark 100% complete: {n} unresolved critical defect(s) are linked to this activity.")
    conn.execute("UPDATE activities SET percent_complete=?, actual_cost=?, delay_days=? WHERE id=?",
                 (pct, cost, delay, activity_id))
    _commit(conn)


# --------------------------------------------------------- 5. quality, risk
def add_defect(conn, title, severity, assignee_id, activity_id):
    title = _text(title, "Defect title")
    if severity not in ("Critical", "Major", "Minor"):
        raise ValidationError("Severity must be Critical, Major or Minor.")
    if not assignee_id:
        raise ValidationError("A defect must be assigned to a team member.")
    conn.execute("INSERT INTO defects(title,severity,assignee_id,activity_id,status,reported_on) VALUES(?,?,?,?, 'Open', ?)",
                 (title, severity, assignee_id, activity_id or None, date.today().isoformat()))
    if severity == "Critical" and activity_id:
        # consistency: an activity with a new critical defect can no longer be 100% complete
        conn.execute("UPDATE activities SET percent_complete=MIN(percent_complete, 95) WHERE id=?", (activity_id,))
    _commit(conn)


def update_defect_status(conn, defect_id, status):
    if status not in ("Open", "In Progress", "Resolved", "Closed"):
        raise ValidationError("Invalid defect status.")
    if not conn.execute("SELECT 1 FROM defects WHERE id=?", (defect_id,)).fetchone():
        raise ValidationError("Defect not found.")
    conn.execute("UPDATE defects SET status=? WHERE id=?", (status, defect_id))
    _commit(conn)


def add_check_item(conn, deliverable, item):
    conn.execute("INSERT INTO checklist(deliverable,item) VALUES(?,?)",
                 (_text(deliverable, "Deliverable"), _text(item, "Checklist item")))
    _commit(conn)


def record_inspection(conn, item_id, result, notes, on_date):
    if result not in ("Pending", "Pass", "Fail"):
        raise ValidationError("Result must be Pending, Pass or Fail.")
    d = parse_date(on_date, "Inspection date")
    notes = (notes or "").strip()
    if result == "Fail" and not notes:
        raise ValidationError("Notes are required when an inspection fails.")
    conn.execute("UPDATE checklist SET result=?, notes=?, inspected_on=? WHERE id=?",
                 (result, notes, d.isoformat() if result != "Pending" else None, item_id))
    _commit(conn)


def add_risk(conn, description, likelihood, impact, preventive, corrective):
    conn.execute("INSERT INTO risks(description,likelihood,impact,preventive_action,corrective_action) VALUES(?,?,?,?,?)",
                 (_text(description, "Risk description"),
                  _num(likelihood, "Likelihood", 1, 5, True), _num(impact, "Impact", 1, 5, True),
                  _text(preventive, "Preventive action"), _text(corrective, "Corrective action")))
    _commit(conn)


def risk_level(score):
    return "High" if score >= 15 else "Medium" if score >= 8 else "Low"


def risk_ranking(conn):
    rows = [dict(r) for r in conn.execute("SELECT * FROM risks")]
    for r in rows:
        r["score"] = r["likelihood"] * r["impact"]
        r["level"] = risk_level(r["score"])
    rows.sort(key=lambda r: (-r["score"], -r["impact"], r["id"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


# ------------------------------------------------ scheduling (CPM-style)
def topo_order(ids, deps):
    preds = {i: [] for i in ids}
    succs = {i: [] for i in ids}
    for a, p in deps:
        if a in preds and p in preds:
            preds[a].append(p)
            succs[p].append(a)
    indeg = {i: len(preds[i]) for i in ids}
    queue = sorted(i for i in ids if indeg[i] == 0)
    order = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for s in sorted(succs[n]):
            indeg[s] -= 1
            if indeg[s] == 0:
                queue.append(s)
    if len(order) != len(ids):
        raise ValidationError("Circular dependency detected in the schedule.")
    return order, preds, succs


def schedule(activities, deps, project_start):
    """Forward pass for planned (baseline) and forecast (with delays) dates, backward pass for float."""
    start0 = parse_date(project_start)
    acts = {a["id"]: a for a in activities}
    if not acts:
        return {"items": {}, "planned_end": None, "forecast_end": None}
    order, preds, succs = topo_order(list(acts), deps)
    res = {}
    for i in order:
        a = acts[i]
        dur, delay = int(a["duration_days"]), int(a.get("delay_days") or 0)
        ps = max((res[p]["planned_end"] for p in preds[i]), default=start0 - ONE) + ONE
        fs = max((res[p]["forecast_end"] for p in preds[i]), default=start0 - ONE) + ONE
        pe = ps + timedelta(days=dur - 1)
        fe = fs + timedelta(days=dur + delay - 1)
        res[i] = dict(planned_start=ps, planned_end=pe, forecast_start=fs, forecast_end=fe,
                      slip_days=(fe - pe).days, start_slip=(fs - ps).days, direct_delay=delay)
    planned_end = max(r["planned_end"] for r in res.values())
    forecast_end = max(r["forecast_end"] for r in res.values())
    late_start = {}
    for i in reversed(order):
        a = acts[i]
        length = int(a["duration_days"]) + int(a.get("delay_days") or 0)
        lf = min((late_start[s] - ONE for s in succs[i]), default=forecast_end)
        late_start[i] = lf - timedelta(days=length - 1)
        res[i]["float_days"] = (late_start[i] - res[i]["forecast_start"]).days
        res[i]["critical"] = res[i]["float_days"] == 0
    for i in order:  # dependants pushed back by this activity's delay
        if res[i]["direct_delay"] > 0 or res[i]["slip_days"] > 0:
            seen, stack = set(), list(succs[i])
            while stack:
                n = stack.pop()
                if n not in seen:
                    seen.add(n)
                    stack += succs[n]
            res[i]["affected"] = sorted(n for n in seen if res[n]["start_slip"] > 0)
        else:
            res[i]["affected"] = []
    return {"items": res, "planned_end": planned_end, "forecast_end": forecast_end}


# ------------------------------------------------------------------- EVM
def evm_calc(scoped, items, status_date, th):
    bac = pv = ev = ac = 0.0
    rows = []
    for a in scoped:
        s = items[a["id"]]
        planned_pct = min(max(((status_date - s["planned_start"]).days + 1) / a["duration_days"], 0), 1)
        pv_i = a["planned_cost"] * planned_pct
        ev_i = a["planned_cost"] * a["percent_complete"] / 100
        ac_i = a["actual_cost"]
        cpi_i = ev_i / ac_i if ac_i > 0 else None
        rows.append(dict(id=a["id"], name=a["name"], bac=a["planned_cost"], pv=pv_i, ev=ev_i, ac=ac_i,
                         cpi=cpi_i, spi=ev_i / pv_i if pv_i > 0 else None,
                         over_budget=bool(ac_i > a["planned_cost"] or (cpi_i is not None and cpi_i < th["cpi_warn"]))))
        bac += a["planned_cost"]; pv += pv_i; ev += ev_i; ac += ac_i
    cpi = ev / ac if ac > 0 else None
    spi = ev / pv if pv > 0 else None
    eac = bac / cpi if cpi else bac
    return dict(bac=bac, pv=pv, ev=ev, ac=ac, cpi=cpi, spi=spi, cv=ev - ac, sv=ev - pv,
                eac=eac, etc=eac - ac, vac=bac - eac,
                percent_complete=(ev / bac * 100) if bac else 0.0, rows=rows)


def snapshot(conn, status_date=None, extra_req_ids=()):
    """Full project state. `extra_req_ids` simulates approving requirements (used for change impact preview)."""
    ch = get_charter(conn)
    status = parse_date(status_date or ch["status_date"], "Status date")
    extra = set(extra_req_ids)
    approved = {r[0] for r in conn.execute("SELECT id FROM requirements WHERE status='Approved'")} | extra
    acts = [dict(r) for r in conn.execute(
        """SELECT a.*, t.name AS assignee, r.code AS req_code, r.status AS req_status
           FROM activities a JOIN requirements r ON r.id=a.requirement_id
           LEFT JOIN team t ON t.id=a.assignee_id ORDER BY a.id""")]
    deps = [(r[0], r[1]) for r in conn.execute("SELECT activity_id, predecessor_id FROM dependencies")]
    scoped = [a for a in acts if a["requirement_id"] in approved]
    sched = schedule(scoped, deps, ch["start_date"])
    crs = [r for r in conn.execute("SELECT * FROM change_requests")
           if r["status"] == "Approved" or (r["status"] == "Pending" and r["requirement_id"] in extra)]
    budget = ch["approved_budget"] + sum(r["cost_impact"] for r in crs)
    deadline = parse_date(ch["deadline"]) + timedelta(days=round(7 * sum(r["schedule_impact_weeks"] for r in crs)))
    th = get_thresholds(conn)
    ev = evm_calc(scoped, sched["items"], status, th)
    return dict(charter=ch, status_date=status, in_scope=scoped, excluded=[a for a in acts if a["requirement_id"] not in approved],
                items=sched["items"], planned_end=sched["planned_end"], forecast_end=sched["forecast_end"],
                budget=budget, deadline=deadline, base_budget=ch["approved_budget"],
                base_deadline=parse_date(ch["deadline"]), evm=ev, thresholds=th,
                n_requirements=len(approved), n_work_packages=len(scoped))


def delayed_activities(snap):
    out = []
    names = {a["id"]: a["name"] for a in snap["in_scope"]}
    final_slip = (snap["forecast_end"] - snap["planned_end"]).days if snap["forecast_end"] else 0
    for a in snap["in_scope"]:
        s = snap["items"][a["id"]]
        if s["slip_days"] > 0:
            out.append(dict(id=a["id"], name=a["name"], type="Direct delay" if s["direct_delay"] > 0 else "Knock-on delay",
                            direct_delay=s["direct_delay"], slip_days=s["slip_days"],
                            planned_end=s["planned_end"], forecast_end=s["forecast_end"],
                            affected=", ".join(f"A{i} {names[i]}" for i in s["affected"]) or "none",
                            project_slip=final_slip))
    return out


def alerts(conn, snap):
    th, e, out = snap["thresholds"], snap["evm"], []
    for label, val, key in (("CPI", e["cpi"], "cpi_warn"), ("SPI", e["spi"], "spi_warn")):
        if val is None:
            continue
        kind = "cost overrun" if label == "CPI" else "schedule deviation"
        if val < th["critical"]:
            out.append(("critical", f"{label} is {val:.2f}, below the critical threshold {th['critical']:.2f} ({kind})."))
        elif val < th[key]:
            out.append(("warning", f"{label} is {val:.2f}, below the warning threshold {th[key]:.2f} ({kind})."))
    if snap["forecast_end"] and snap["forecast_end"] > snap["deadline"]:
        d = (snap["forecast_end"] - snap["deadline"]).days
        out.append(("critical", f"Forecast finish {snap['forecast_end']} is {d} day(s) after the deadline {snap['deadline']}."))
    if e["bac"] > snap["budget"]:
        out.append(("critical", f"Planned cost of in-scope work (PKR {e['bac']:,.0f}) exceeds the approved budget (PKR {snap['budget']:,.0f})."))
    if e["ac"] > snap["budget"]:
        out.append(("critical", "Actual cost already exceeds the approved budget."))
    elif e["eac"] > snap["budget"]:
        out.append(("warning", f"Estimate at completion (PKR {e['eac']:,.0f}) exceeds the approved budget (PKR {snap['budget']:,.0f})."))
    n = conn.execute("SELECT COUNT(*) FROM defects WHERE severity='Critical' AND status IN ('Open','In Progress')").fetchone()[0]
    if n:
        out.append(("critical", f"{n} unresolved critical defect(s)."))
    n = conn.execute("SELECT COUNT(*) FROM change_requests WHERE status='Pending'").fetchone()[0]
    if n:
        out.append(("info", f"{n} change request(s) awaiting a decision."))
    return out


# --------------------------------------------------------------- sample data
def seed_sample_data(conn):
    c = conn
    c.execute("""INSERT INTO charter(id,name,objectives,stakeholders,scope_boundaries,approved_budget,start_date,
                 deadline,status_date,manager,status) VALUES(1,?,?,?,?,?,?,?,?,?,?)""",
              ("Smart Healthcare Project Management and Monitoring System",
               "Deliver one system for five hospitals covering patient appointments, laboratory reports, doctor schedules, online consultations and billing, within 16 weeks and PKR 5,000,000.",
               "Hospital management (sponsor), doctors, lab technicians, billing staff, patients, development company, QA team.",
               "In scope: appointments, lab reports, doctor schedules, online consultations, billing. Out of scope until approved by change request: AI diagnosis, mobile app, insurance integration.",
               5_000_000, "2026-07-06", "2026-10-25", "2026-09-14", "Ayesha Khan", "Monitoring"))
    c.execute("INSERT INTO plan(id,scope_plan,schedule_plan,cost_plan,quality_plan) VALUES(1,?,?,?,?)",
              ("Scope is baselined from approved requirements. New requirements enter scope only through an approved change request.",
               "16 weeks starting 6 July 2026. Activities are sequenced by finish-to-start dependencies; delays are tracked weekly.",
               "Budget PKR 5,000,000 (PKR 400,000 reserve above planned activity cost). Cost tracked with EVM; warning at CPI/SPI below 0.95.",
               "Every deliverable passes a checklist inspection. No release with unresolved critical defects."))
    c.executemany("INSERT INTO settings(key,value) VALUES(?,?)", [("cpi_warn", 0.95), ("spi_warn", 0.95), ("critical", 0.85)])
    team = [("Ayesha Khan", "Project Manager", "Planning, tracking, change control, stakeholder reporting"),
            ("Hamza Ali", "Backend Developer", "Appointment, billing and integration services"),
            ("Sara Malik", "Backend Developer", "Lab reports, doctor schedule and consultation services"),
            ("Usman Tariq", "Frontend Developer", "UI/UX design and appointment screens"),
            ("Mehwish Noor", "Frontend Developer", "Lab and billing screens"),
            ("Bilal Ahmed", "Database Developer", "Schema design, performance and data integrity"),
            ("Fatima Zahra", "QA Engineer", "Test planning, inspections, defect verification")]
    c.executemany("INSERT INTO team(name,role,responsibilities) VALUES(?,?,?)", team)
    reqs = [("R1", "Project foundation and design", "Requirements, architecture, database and UI design", "High", "Approved"),
            ("R2", "Patient appointment management", "Online and front desk booking with conflict prevention", "High", "Approved"),
            ("R3", "Laboratory report management", "Order, record and publish lab reports", "High", "Approved"),
            ("R4", "Doctor schedules and online consultation", "Doctor availability and video consultations", "High", "Approved"),
            ("R5", "Hospital billing", "Invoices, payments and reports", "Medium", "Approved"),
            ("R6", "Integration, testing and deployment", "System integration, QA and go live", "High", "Approved"),
            ("R7", "AI-based preliminary diagnosis", "Symptom based preliminary diagnosis for doctors", "Medium", "Proposed"),
            ("R8", "Mobile application", "Patient mobile app for booking and reports", "Medium", "Proposed")]
    c.executemany("INSERT INTO requirements(code,title,description,priority,status) VALUES(?,?,?,?,?)", reqs)
    # (name, req, assignee, duration, cost, actual, pct, delay)
    acts = [("Requirements gathering and SRS", 1, 1, 10, 300_000, 310_000, 100, 0),
            ("System architecture design", 1, 2, 7, 250_000, 250_000, 100, 0),
            ("Database schema design", 1, 6, 8, 200_000, 210_000, 100, 0),
            ("UI/UX design", 1, 4, 10, 250_000, 260_000, 100, 0),
            ("Appointment module (backend)", 2, 2, 22, 600_000, 680_000, 100, 4),
            ("Lab reports module (backend)", 3, 3, 15, 500_000, 520_000, 100, 0),
            ("Doctor schedule and consultation (backend)", 4, 3, 15, 450_000, 470_000, 100, 0),
            ("Billing module (backend)", 5, 2, 12, 400_000, 420_000, 100, 0),
            ("Web frontend: appointments and doctors", 2, 4, 28, 450_000, 300_000, 60, 8),
            ("Web frontend: labs and billing", 3, 5, 15, 350_000, 360_000, 100, 0),
            ("System integration", 6, 2, 12, 300_000, 0, 0, 0),
            ("System testing", 6, 7, 14, 300_000, 0, 0, 0),
            ("UAT and deployment", 6, 1, 10, 250_000, 0, 0, 0),
            ("AI diagnosis model development", 7, 3, 14, 300_000, 0, 0, 0),
            ("AI module integration and clinical validation", 7, 2, 28, 150_000, 0, 0, 0),
            ("Mobile app development", 8, 4, 21, 250_000, 0, 0, 0),
            ("Mobile app integration and release", 8, 5, 21, 100_000, 0, 0, 0)]
    c.executemany("""INSERT INTO activities(name,requirement_id,assignee_id,duration_days,planned_cost,actual_cost,percent_complete,delay_days)
                     VALUES(?,?,?,?,?,?,?,?)""", acts)
    deps = [(2, 1), (3, 1), (4, 1), (5, 2), (5, 3), (6, 2), (6, 3), (7, 6), (8, 5), (9, 4), (9, 5), (10, 4), (10, 6),
            (11, 7), (11, 8), (11, 9), (11, 10), (12, 11), (13, 12), (13, 15), (13, 17),
            (14, 3), (15, 14), (15, 11), (16, 4), (16, 5), (17, 16), (17, 11)]
    c.executemany("INSERT INTO dependencies(activity_id,predecessor_id) VALUES(?,?)", deps)
    c.executemany("INSERT INTO milestones(name,due_date,activity_id,achieved) VALUES(?,?,?,?)",
                  [("SRS approved", "2026-07-15", 1, 1), ("Design complete", "2026-07-25", 4, 1),
                   ("Backend complete", "2026-08-26", 8, 1), ("Integration complete", "2026-09-23", 11, 0),
                   ("UAT and go live", "2026-10-17", 13, 0)])
    c.executemany("""INSERT INTO change_requests(title,requirement_id,justification,cost_impact,schedule_impact_weeks,status,submitted_on)
                     VALUES(?,?,?,?,?, 'Pending', ?)""",
                  [("Add AI-based preliminary diagnosis module", 7,
                    "Hospital management wants faster triage and reduced doctor workload.", 450_000, 2, "2026-09-01"),
                   ("Add patient mobile application", 8,
                    "Patients need mobile access to appointments and lab reports.", 350_000, 1, "2026-09-03")])
    c.executemany("INSERT INTO defects(title,severity,assignee_id,activity_id,status,reported_on) VALUES(?,?,?,?,?,?)",
                  [("Double booking possible when two receptionists book the same slot", "Critical", 4, 9, "In Progress", "2026-09-08"),
                   ("Patient record lost on concurrent edit", "Critical", 6, 11, "Open", "2026-09-10"),
                   ("Billing total rounding error", "Major", 2, 8, "Resolved", "2026-08-20"),
                   ("Lab report PDF export fails for long reports", "Major", 3, 6, "In Progress", "2026-09-05"),
                   ("Label misaligned on billing screen", "Minor", 5, 10, "Open", "2026-09-09"),
                   ("Typo on appointment confirmation", "Minor", 4, 9, "Closed", "2026-08-30")])
    c.executemany("INSERT INTO checklist(deliverable,item,result,notes,inspected_on) VALUES(?,?,?,?,?)",
                  [("SRS document", "Requirements traceable to hospital needs", "Pass", "", "2026-07-15"),
                   ("Appointment module", "Prevents double booking", "Fail", "Slot conflict under concurrent bookings", "2026-09-08"),
                   ("Appointment module", "Confirmation messages sent", "Pass", "", "2026-09-08"),
                   ("Patient records", "Records saved without data loss", "Fail", "Lost update on concurrent edit", "2026-09-10"),
                   ("Lab reports", "Reports linked to correct patient ID", "Pass", "", "2026-09-05"),
                   ("Billing module", "Invoice totals computed correctly", "Pass", "", "2026-08-26"),
                   ("Billing module", "UI follows approved mockups", "Pending", "", None),
                   ("Security", "Role based access verified", "Pending", "", None)])
    c.executemany("INSERT INTO risks(description,likelihood,impact,preventive_action,corrective_action,status) VALUES(?,?,?,?,?,?)",
                  [("Scope creep from hospital management", 4, 4, "Enforce change control board and written approval", "Re-baseline schedule and budget after approval", "Occurred"),
                   ("Critical defects in scheduling and patient records", 4, 5, "Peer reviews and automated regression tests", "Dedicated bug fix sprint and extra QA hours", "Occurred"),
                   ("Key developer unavailable", 2, 4, "Pair programming and documentation", "Reassign work and use contract developer", "Open"),
                   ("Budget overrun from rework", 3, 4, "Weekly EVM review with thresholds", "Use cost reserve or request budget change", "Open"),
                   ("Patient data privacy breach", 2, 5, "Encryption and role based access", "Incident response plan and notification", "Open"),
                   ("Integration delays across five hospital systems", 3, 3, "Early interface agreements and mock services", "Add integration engineer, phase rollout", "Open"),
                   ("Doctors do not trust AI diagnosis output", 3, 4, "Clinical validation with doctors", "Limit to advisory mode", "Open"),
                   ("Hospital staff resist new system", 2, 3, "Training sessions and champions", "Extra on site support", "Open")])
    c.commit()
    refresh_wbs(c)
