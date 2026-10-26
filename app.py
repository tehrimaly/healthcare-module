"""Smart Healthcare Project Management System: Streamlit GUI.
Run with:  streamlit run app.py
"""
import sqlite3
import textwrap
from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import pm_core as pm
from pm_core import ValidationError

st.set_page_config(page_title="Healthcare PM System", layout="wide")


# ------------------------------------------------------------------ helpers
def money(x):
    return f"PKR {x:,.0f}"


def ratio(x):
    return "n/a" if x is None else f"{x:.2f}"


def flash(kind, msg):
    st.session_state["_flash"] = (kind, msg)


def show_flash():
    f = st.session_state.pop("_flash", None)
    if f:
        getattr(st, f[0])(f[1])


def act(fn, *args, ok="Saved.", **kw):
    """Run a core action, show validation/database errors, refresh on success."""
    try:
        fn(*args, **kw)
    except ValidationError as e:
        st.error(str(e))
        return False
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return False
    flash("success", ok)
    st.rerun()


def table(rows, cols=None, rename=None):
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No records yet.")
        return
    if cols:
        df = df[cols]
    if rename:
        df = df.rename(columns=rename)
    st.dataframe(df, hide_index=True)


def plot(fig):
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


def team_map(conn):
    return {r["id"]: f"{r['name']} ({r['role']})" for r in conn.execute("SELECT * FROM team ORDER BY id")}


def req_map(conn, statuses=None):
    q = "SELECT * FROM requirements ORDER BY id"
    return {r["id"]: f"{r['code']} {r['title']} [{r['status']}]" for r in conn.execute(q)
            if not statuses or r["status"] in statuses}


def act_map(conn):
    return {r["id"]: f"A{r['id']} {r['name']}" for r in conn.execute("SELECT id,name FROM activities ORDER BY id")}


def progress_form(conn, key):
    acts = [dict(r) for r in conn.execute("SELECT * FROM activities ORDER BY id")]
    if not acts:
        return
    names = act_map(conn)
    sel = st.selectbox("Activity", list(names), format_func=names.get, key=f"{key}_sel")
    a = next(x for x in acts if x["id"] == sel)
    with st.form(f"{key}_form"):
        c1, c2, c3 = st.columns(3)
        pct = c1.number_input("Percent complete", 0.0, 100.0, float(a["percent_complete"]), 5.0, key=f"{key}_p{sel}")
        cost = c2.number_input("Actual cost (PKR)", 0.0, value=float(a["actual_cost"]), step=10000.0, key=f"{key}_c{sel}")
        delay = c3.number_input("Delay (days)", 0, value=int(a["delay_days"]), step=1, key=f"{key}_d{sel}")
        if st.form_submit_button("Update progress"):
            act(pm.update_progress, conn, sel, pct, cost, delay, ok="Progress updated.")


# --------------------------------------------------------------- dashboard
def page_dashboard(conn, snap):
    ch, e = snap["charter"], snap["evm"]
    st.subheader(ch["name"])
    st.caption(f"Status: {ch['status']}   |   Status date: {snap['status_date']}   |   Manager: {ch['manager']}")
    c = st.columns(4)
    c[0].metric("Progress (earned value)", f"{e['percent_complete']:.1f}%")
    c[1].metric("Forecast finish", str(snap["forecast_end"]), f"{(snap['forecast_end'] - snap['deadline']).days:+d} days vs deadline", delta_color="inverse")
    c[2].metric("Budget", money(snap["budget"]), f"EAC {money(e['eac'])}", delta_color="off")
    pending = conn.execute("SELECT COUNT(*) FROM change_requests WHERE status='Pending'").fetchone()[0]
    c[3].metric("Pending change requests", pending)
    delayed = pm.delayed_activities(snap)
    crit = conn.execute("""SELECT d.id, d.title, d.status, t.name AS assignee, d.activity_id FROM defects d
                           LEFT JOIN team t ON t.id=d.assignee_id
                           WHERE d.severity='Critical' AND d.status IN ('Open','In Progress')""").fetchall()
    c = st.columns(4)
    c[0].metric("Delayed activities", len(delayed))
    c[1].metric("Unresolved critical defects", len(crit))
    c[2].metric("CPI", ratio(e["cpi"]))
    c[3].metric("SPI", ratio(e["spi"]))
    st.markdown("**Alerts**")
    for level, msg in pm.alerts(conn, snap):
        {"critical": st.error, "warning": st.warning, "info": st.info}[level](msg)
    a, b = st.columns(2)
    with a:
        st.markdown("**Delayed activities**")
        table(delayed, ["id", "name", "type", "slip_days", "forecast_end"],
              {"id": "ID", "name": "Activity", "type": "Type", "slip_days": "Slip (days)", "forecast_end": "Forecast end"})
        st.markdown("**Pending change requests**")
        table([dict(r) for r in conn.execute("SELECT id,title,cost_impact,schedule_impact_weeks FROM change_requests WHERE status='Pending'")],
              rename={"id": "ID", "title": "Title", "cost_impact": "Cost impact", "schedule_impact_weeks": "Weeks"})
    with b:
        st.markdown("**Unresolved critical defects**")
        table([dict(r) for r in crit], ["id", "title", "status", "assignee"], {"id": "ID", "title": "Defect", "status": "Status", "assignee": "Assigned to"})
        st.markdown("**Budget status**")
        table([dict(Item="Approved budget (incl. approved changes)", Amount=money(snap["budget"])),
               dict(Item="Planned cost of in-scope work (BAC)", Amount=money(e["bac"])),
               dict(Item="Actual cost to date (AC)", Amount=money(e["ac"])),
               dict(Item="Estimate at completion (EAC)", Amount=money(e["eac"])),
               dict(Item="Remaining budget", Amount=money(snap["budget"] - e["ac"]))])
    report = [f"# Project report: {ch['name']}", f"Status date: {snap['status_date']}", "",
              f"Progress: {e['percent_complete']:.1f}%", f"Forecast finish: {snap['forecast_end']} (deadline {snap['deadline']})",
              f"Budget: {money(snap['budget'])}, AC {money(e['ac'])}, EAC {money(e['eac'])}",
              f"CPI {ratio(e['cpi'])}, SPI {ratio(e['spi'])}", f"Pending change requests: {pending}",
              f"Delayed activities: {len(delayed)}", f"Unresolved critical defects: {len(crit)}", "", "Alerts:"]
    report += [f"- [{l}] {m}" for l, m in pm.alerts(conn, snap)]
    st.download_button("Download report (Markdown)", "\n".join(report), "project_report.md")


# ------------------------------------------- 1. initiation and integration
def page_charter(conn, snap):
    st.header("1. Project Initiation and Integration")
    t = st.tabs(["Charter", "Management plan", "Team", "Milestones and status", "Closure"])
    ch = snap["charter"]
    with t[0]:
        with st.form("charter"):
            name = st.text_input("Project name", ch["name"])
            obj = st.text_area("Objectives", ch["objectives"])
            stk = st.text_area("Stakeholders", ch["stakeholders"])
            scope = st.text_area("Scope boundaries", ch["scope_boundaries"])
            c1, c2, c3, c4 = st.columns(4)
            bud = c1.number_input("Approved budget (PKR)", 1.0, value=float(ch["approved_budget"]), step=100000.0)
            sd = c2.date_input("Start date", pm.parse_date(ch["start_date"]))
            dl = c3.date_input("Deadline", pm.parse_date(ch["deadline"]))
            mgr = c4.text_input("Project manager", ch["manager"] or "")
            if st.form_submit_button("Save charter"):
                act(pm.save_charter, conn, name, obj, stk, scope, bud, sd, dl, mgr, ok="Charter saved.")
        st.caption(f"With approved changes: budget {money(snap['budget'])}, deadline {snap['deadline']}.")
    with t[1]:
        plan = pm.get_plan(conn)
        e = snap["evm"]
        c = st.columns(4)
        c[0].metric("Approved requirements", snap["n_requirements"])
        c[1].metric("Work packages in scope", snap["n_work_packages"])
        c[2].metric("Planned finish", str(snap["planned_end"]))
        c[3].metric("Planned cost (BAC)", money(e["bac"]))
        defects = conn.execute("SELECT COUNT(*) FROM defects").fetchone()[0]
        checks = conn.execute("SELECT COUNT(*) FROM checklist WHERE result<>'Pending'").fetchone()[0]
        st.caption(f"Quality: {defects} defects logged, {checks} checklist items inspected. Figures above are calculated from the live data.")
        with st.form("plan"):
            sp = st.text_area("Scope management", plan["scope_plan"])
            sc = st.text_area("Schedule management", plan["schedule_plan"])
            cp = st.text_area("Cost management", plan["cost_plan"])
            qp = st.text_area("Quality management", plan["quality_plan"])
            if st.form_submit_button("Save plan"):
                act(pm.save_plan, conn, sp, sc, cp, qp, ok="Plan saved.")
    with t[2]:
        table([dict(r) for r in conn.execute("SELECT id,name,role,responsibilities FROM team ORDER BY id")])
        with st.form("team", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n, r = c1.text_input("Name"), c2.text_input("Role")
            resp = st.text_input("Responsibilities")
            if st.form_submit_button("Add team member"):
                act(pm.add_team_member, conn, n, r, resp, ok="Team member added.")
    with t[3]:
        st.selectbox("Project status", ["Initiating", "Planning", "Executing", "Monitoring"],
                     index=["Initiating", "Planning", "Executing", "Monitoring"].index(ch["status"]) if ch["status"] != "Closed" else 3,
                     key="proj_status")
        if st.button("Update status"):
            act(pm.set_project_status, conn, st.session_state["proj_status"], ok="Status updated.")
        ms = []
        for r in conn.execute("SELECT m.*, a.id AS aid FROM milestones m LEFT JOIN activities a ON a.id=m.activity_id ORDER BY m.due_date"):
            it = snap["items"].get(r["aid"]) if r["aid"] else None
            fc = it["forecast_end"] if it else None
            ms.append(dict(ID=r["id"], Milestone=r["name"], Due=r["due_date"], Forecast=str(fc) if fc else "",
                           Status="Achieved" if r["achieved"] else ("At risk" if fc and str(fc) > r["due_date"] else "On track")))
        table(ms)
        c1, c2 = st.columns(2)
        with c1.form("ms_add", clear_on_submit=True):
            n = st.text_input("Milestone name")
            due = st.date_input("Due date", pm.parse_date(ch["start_date"]) + timedelta(days=30))
            names = act_map(conn)
            link = st.selectbox("Linked activity", [None] + list(names), format_func=lambda x: "None" if x is None else names[x])
            if st.form_submit_button("Add milestone"):
                act(pm.add_milestone, conn, n, due, link, ok="Milestone added.")
        with c2.form("ms_ach"):
            ids = [m["ID"] for m in ms]
            mid = st.selectbox("Milestone", ids, format_func=lambda i: next(m["Milestone"] for m in ms if m["ID"] == i)) if ids else None
            val = st.checkbox("Achieved")
            if st.form_submit_button("Update milestone") and mid:
                act(pm.set_milestone_achieved, conn, mid, val, ok="Milestone updated.")
    with t[4]:
        if ch["closed"]:
            st.success("Project is closed.")
            st.write(ch["closure_notes"])
        blockers = pm.closure_blockers(conn)
        for b in blockers:
            st.warning("Blocker: " + b)
        notes = st.text_area("Closure notes and lessons learned", ch["closure_notes"] or "")
        if st.button("Close project"):
            act(pm.close_project, conn, notes, ok="Project closed.")


# --------------------------------------------------------------- 2. scope
def wbs_dot(rows):
    lines = ['digraph W { rankdir=LR; node [shape=box, style="rounded,filled", fontname=Helvetica, fontsize=10];']
    colors = {"Project": "#cfe8ff", "Deliverable": "#d9f2d9", "Work Package": "#ffffff"}
    for r in rows:
        label = r["code"] + "\\n" + "\\n".join(textwrap.wrap(r["name"].replace('"', "'"), 28))
        lines.append(f'n{r["id"]} [label="{label}", fillcolor="{colors[r["level_type"]]}"];')
        if r["parent_id"]:
            lines.append(f'n{r["parent_id"]} -> n{r["id"]};')
    return "\n".join(lines + ["}"])


def impact_table(before, after):
    def row(label, b, a, f=str):
        return {"Measure": label, "Before": f(b), "After approval": f(a)}
    return [row("Requirements in approved scope", before["n_requirements"], after["n_requirements"]),
            row("Work packages in scope", before["n_work_packages"], after["n_work_packages"]),
            row("Planned finish (baseline)", before["planned_end"], after["planned_end"]),
            row("Forecast finish", before["forecast_end"], after["forecast_end"]),
            row("Approved deadline", before["deadline"], after["deadline"]),
            row("Forecast vs deadline (days)", (before["forecast_end"] - before["deadline"]).days,
                (after["forecast_end"] - after["deadline"]).days, lambda x: f"{x:+d}"),
            row("Approved budget", before["budget"], after["budget"], money),
            row("Planned cost of in-scope work (BAC)", before["evm"]["bac"], after["evm"]["bac"], money),
            row("Budget headroom", before["budget"] - before["evm"]["bac"], after["budget"] - after["evm"]["bac"], money)]


def page_scope(conn, snap):
    st.header("2. Scope Management and WBS")
    t = st.tabs(["Requirements", "WBS", "Change requests", "Change impact"])
    with t[0]:
        reqs = [dict(r) for r in conn.execute("SELECT * FROM requirements ORDER BY id")]
        order = {"High": 0, "Medium": 1, "Low": 2}
        for r in reqs:
            r["In approved scope"] = "Yes" if r["status"] == "Approved" else "No"
        table(sorted(reqs, key=lambda r: (order[r["priority"]], r["id"])),
              ["code", "title", "priority", "status", "In approved scope", "description"])
        c1, c2 = st.columns(2)
        with c1.form("req_add", clear_on_submit=True):
            st.markdown("**Add requirement** (starts as Proposed, outside approved scope)")
            ti = st.text_input("Title")
            de = st.text_area("Description")
            pr = st.selectbox("Priority", ["High", "Medium", "Low"], index=1)
            if st.form_submit_button("Add"):
                act(pm.add_requirement, conn, ti, de, pr, ok="Requirement added as Proposed.")
        with c2:
            rm = req_map(conn)
            sel = st.selectbox("Select requirement", list(rm), format_func=rm.get)
            r = next(x for x in reqs if x["id"] == sel)
            with st.form("req_upd"):
                ti = st.text_input("Title", r["title"], key=f"t{sel}")
                de = st.text_area("Description", r["description"], key=f"d{sel}")
                pr = st.selectbox("Priority", ["High", "Medium", "Low"], index=["High", "Medium", "Low"].index(r["priority"]), key=f"p{sel}")
                if st.form_submit_button("Update / prioritize"):
                    act(pm.update_requirement, conn, sel, ti, de, pr, ok="Requirement updated.")
            b1, b2, _ = st.columns(3)
            if b1.button("Approve"):
                act(pm.set_requirement_status, conn, sel, "Approved", ok="Requirement approved.")
            if b2.button("Reject"):
                act(pm.set_requirement_status, conn, sel, "Rejected", ok="Requirement rejected.")
    with t[1]:
        rows = [dict(r) for r in conn.execute("SELECT * FROM wbs ORDER BY id")]
        st.caption("The WBS contains only approved requirements. It is rebuilt automatically when scope or activities change.")
        st.graphviz_chart(wbs_dot(rows))
        table(rows, ["code", "name", "level_type"], {"code": "WBS code", "name": "Name", "level_type": "Level"})
        excl = [r for r in conn.execute("SELECT code,title,status FROM requirements WHERE status<>'Approved'")]
        if excl:
            st.warning("Excluded from the approved scope: " + ", ".join(f"{r['code']} {r['title']} ({r['status']})" for r in excl))
        if st.button("Regenerate WBS"):
            act(pm.refresh_wbs, conn, ok="WBS regenerated.")
    with t[2]:
        table([dict(r) for r in conn.execute("""SELECT c.id, c.title, r.code AS requirement, c.justification, c.cost_impact,
                 c.schedule_impact_weeks AS weeks, c.status, c.submitted_on, c.decided_on
                 FROM change_requests c LEFT JOIN requirements r ON r.id=c.requirement_id ORDER BY c.id""")])
        rm = req_map(conn, ("Proposed", "Rejected"))
        with st.form("cr_add", clear_on_submit=True):
            ti = st.text_input("Change title")
            rq = st.selectbox("Linked requirement", [None] + list(rm), format_func=lambda x: "None" if x is None else rm[x])
            ju = st.text_area("Justification")
            c1, c2 = st.columns(2)
            co = c1.number_input("Cost impact (PKR)", 0.0, step=50000.0)
            wk = c2.number_input("Schedule impact (weeks)", 0.0, step=1.0)
            if st.form_submit_button("Submit change request"):
                act(pm.submit_change_request, conn, ti, rq, ju, co, wk, ok="Change request submitted.")
    with t[3]:
        pend = {r["id"]: f"CR-{r['id']} {r['title']}" for r in conn.execute("SELECT * FROM change_requests WHERE status='Pending'")}
        if not pend:
            st.info("No pending change requests.")
            return
        cid = st.selectbox("Pending change request", list(pend), format_func=pend.get)
        cr = conn.execute("SELECT * FROM change_requests WHERE id=?", (cid,)).fetchone()
        st.write(f"**Justification:** {cr['justification']}  \n**Declared impact:** {money(cr['cost_impact'])} and {cr['schedule_impact_weeks']:g} week(s)")
        after = pm.snapshot(conn, extra_req_ids=[cr["requirement_id"]] if cr["requirement_id"] else [])
        table(impact_table(snap, after))
        c1, c2, _ = st.columns(3)
        if c1.button("Approve change request", type="primary"):
            act(pm.approve_change_request, conn, cid, ok="Approved. Scope, WBS, schedule and budget are updated.")
        if c2.button("Reject change request"):
            act(pm.reject_change_request, conn, cid, ok="Change request rejected.")


# ------------------------------------------------------------ 3. schedule
def gantt(conn, snap):
    rows = []
    for a in snap["in_scope"]:
        s = snap["items"][a["id"]]
        label = f"A{a['id']} {a['name']}"
        rows.append(dict(Task=label, Start=s["planned_start"], Finish=s["planned_end"] + pm.ONE, Type="Planned baseline"))
        rows.append(dict(Task=label, Start=s["forecast_start"], Finish=s["forecast_end"] + pm.ONE,
                         Type="Forecast (critical path)" if s["critical"] else "Forecast"))
    if not rows:
        st.info("No activities in approved scope.")
        return
    df = pd.DataFrame(rows)
    for c in ("Start", "Finish"):
        df[c] = pd.to_datetime(df[c])
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Type",
                      color_discrete_map={"Planned baseline": "#b0b8c4", "Forecast": "#2b7de9", "Forecast (critical path)": "#d9382e"})
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_layout(height=120 + 38 * len(snap["in_scope"]), barmode="group", legend_title=None, margin=dict(l=0, r=0, t=30, b=0))
    ms = [dict(r) for r in conn.execute("SELECT * FROM milestones")]
    if ms:
        fig.add_trace(go.Scatter(x=[pd.to_datetime(m["due_date"]) for m in ms], y=["Milestones"] * len(ms), mode="markers+text",
                                 marker=dict(symbol="diamond", size=12, color=["#2e9d4f" if m["achieved"] else "#f0a500" for m in ms]),
                                 text=[m["name"] for m in ms], textposition="top center", name="Milestones"))
    for x, lab, col in ((pd.to_datetime(snap["status_date"]), "Status date", "#555"), (pd.to_datetime(snap["deadline"]), "Deadline", "#d9382e")):
        fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, yref="paper", line=dict(color=col, dash="dash"))
        fig.add_annotation(x=x, y=1.03, yref="paper", text=lab, showarrow=False, font=dict(color=col))
    plot(fig)


def page_schedule(conn, snap):
    st.header("3. Schedule and Resource Management")
    t = st.tabs(["Activities", "Dependencies", "Schedule and delays", "Gantt chart"])
    with t[0]:
        rows = []
        for a in snap["in_scope"] + snap["excluded"]:
            rows.append(dict(ID=f"A{a['id']}", Activity=a["name"], Requirement=a["req_code"], Assignee=a["assignee"],
                             Days=a["duration_days"], Cost=a["planned_cost"], Complete=a["percent_complete"], Delay=a["delay_days"],
                             Scope="In scope" if a in snap["in_scope"] else "Excluded (requirement not approved)"))
        table(rows)
        wl = pd.DataFrame(snap["in_scope"])
        if not wl.empty:
            st.markdown("**Workload (in-scope days per team member)**")
            st.bar_chart(wl.groupby("assignee")["duration_days"].sum())
        c1, c2 = st.columns(2)
        with c1.form("act_add", clear_on_submit=True):
            st.markdown("**Add activity**")
            nm = st.text_input("Name")
            rm = req_map(conn)
            rq = st.selectbox("Requirement", list(rm), format_func=rm.get)
            tm = team_map(conn)
            asg = st.selectbox("Assigned to", list(tm), format_func=tm.get)
            d1, d2 = st.columns(2)
            du = d1.number_input("Duration (days)", 1, value=5)
            co = d2.number_input("Planned cost (PKR)", 0.0, step=10000.0)
            if st.form_submit_button("Add activity"):
                act(pm.add_activity, conn, nm, rq, asg, du, co, ok="Activity added.")
        with c2:
            st.markdown("**Update progress and delay**")
            progress_form(conn, "sched")
            names = act_map(conn)
            d = st.selectbox("Delete activity", list(names), format_func=names.get, key="del_act")
            if st.button("Delete selected activity"):
                act(pm.delete_activity, conn, d, ok="Activity deleted.")
    with t[1]:
        names = act_map(conn)
        deps = [dict(Activity=names[r[0]], Predecessor=names[r[1]]) for r in conn.execute("SELECT * FROM dependencies ORDER BY 1,2")]
        table(deps)
        c1, c2 = st.columns(2)
        with c1.form("dep_add"):
            a = st.selectbox("Activity", list(names), format_func=names.get)
            p = st.selectbox("Depends on (finish to start)", list(names), format_func=names.get)
            if st.form_submit_button("Add dependency"):
                act(pm.add_dependency, conn, a, p, ok="Dependency added.")
        with c2.form("dep_rm"):
            pairs = [(r[0], r[1]) for r in conn.execute("SELECT * FROM dependencies ORDER BY 1,2")]
            sel = st.selectbox("Dependency", pairs, format_func=lambda x: f"{names[x[0]]}  after  {names[x[1]]}") if pairs else None
            if st.form_submit_button("Remove dependency") and sel:
                act(pm.remove_dependency, conn, *sel, ok="Dependency removed.")
    with t[2]:
        rows = []
        for a in snap["in_scope"]:
            s = snap["items"][a["id"]]
            rows.append({"ID": f"A{a['id']}", "Activity": a["name"], "Planned start": s["planned_start"], "Planned end": s["planned_end"],
                         "Forecast start": s["forecast_start"], "Forecast end": s["forecast_end"], "Slip (days)": s["slip_days"],
                         "Float": s["float_days"], "Critical": "Yes" if s["critical"] else ""})
        table(rows)
        slip = (snap["forecast_end"] - snap["planned_end"]).days if snap["forecast_end"] else 0
        over = (snap["forecast_end"] - snap["deadline"]).days if snap["forecast_end"] else 0
        c = st.columns(3)
        c[0].metric("Project finish slip vs baseline", f"{slip} days")
        c[1].metric("Forecast finish", str(snap["forecast_end"]))
        c[2].metric("Days past deadline", max(over, 0), delta=f"deadline {snap['deadline']}", delta_color="off")
        st.markdown("**Delayed activities and impact on dependents**")
        table(pm.delayed_activities(snap), ["id", "name", "type", "direct_delay", "slip_days", "affected"],
              {"id": "ID", "name": "Activity", "type": "Type", "direct_delay": "Own delay", "slip_days": "Finish slip", "affected": "Dependent activities pushed back"})
    with t[3]:
        gantt(conn, snap)


# ------------------------------------------------------------- 4. cost/EVM
def page_cost(conn, snap):
    st.header("4. Cost Management and Earned Value Analysis")
    e = snap["evm"]
    t = st.tabs(["Cost estimates", "Track actuals", "Earned value"])
    with t[0]:
        c = st.columns(3)
        c[0].metric("Total planned cost (BAC)", money(e["bac"]))
        c[1].metric("Approved budget", money(snap["budget"]))
        c[2].metric("Budget headroom", money(snap["budget"] - e["bac"]))
        table([dict(ID=f"A{a['id']}", Activity=a["name"], Requirement=a["req_code"], Planned_cost=a["planned_cost"],
                    Scope="In scope" if a in snap["in_scope"] else "Excluded") for a in snap["in_scope"] + snap["excluded"]])
    with t[1]:
        progress_form(conn, "cost")
    with t[2]:
        d = st.date_input("Status date", snap["status_date"], key="evm_date")
        if d != snap["status_date"]:
            act(pm.set_status_date, conn, d, ok="Status date changed.")
        for level, msg in pm.alerts(conn, snap):
            if level != "info":
                {"critical": st.error, "warning": st.warning}[level](msg)
        c = st.columns(5)
        for col, (k, v) in zip(c, (("PV", e["pv"]), ("EV", e["ev"]), ("AC", e["ac"]), ("BAC", e["bac"]), ("EAC", e["eac"]))):
            col.metric(k, money(v))
        c = st.columns(5)
        c[0].metric("CPI (EV / AC)", ratio(e["cpi"]))
        c[1].metric("SPI (EV / PV)", ratio(e["spi"]))
        c[2].metric("Cost variance", money(e["cv"]))
        c[3].metric("Schedule variance", money(e["sv"]))
        c[4].metric("Variance at completion", money(e["vac"]))
        plot(px.bar(pd.DataFrame({"Measure": ["PV", "EV", "AC"], "PKR": [e["pv"], e["ev"], e["ac"]]}), x="Measure", y="PKR", color="Measure"))
        st.markdown("**By activity**")
        table(e["rows"], ["id", "name", "bac", "pv", "ev", "ac", "cpi", "spi", "over_budget"],
              {"id": "ID", "name": "Activity", "bac": "BAC", "pv": "PV", "ev": "EV", "ac": "AC", "cpi": "CPI", "spi": "SPI", "over_budget": "Over budget"})
        th = snap["thresholds"]
        with st.form("thr"):
            st.markdown("**Warning thresholds**")
            c1, c2, c3 = st.columns(3)
            a = c1.number_input("CPI warning below", 0.1, 1.5, th["cpi_warn"], 0.01)
            b = c2.number_input("SPI warning below", 0.1, 1.5, th["spi_warn"], 0.01)
            cr = c3.number_input("Critical below", 0.1, 1.5, th["critical"], 0.01)
            if st.form_submit_button("Save thresholds"):
                act(pm.set_thresholds, conn, a, b, cr, ok="Thresholds saved.")


# -------------------------------------------------------- 5. quality/risk
def pdpc_dot(risks, goal):
    wrap = lambda s, n=30: "\\n".join(textwrap.wrap(s.replace('"', "'"), n))
    out = ['digraph P { rankdir=LR; node [shape=box, style="rounded,filled", fontname=Helvetica, fontsize=10];',
           f'goal [label="{wrap(goal, 26)}", fillcolor="#cfe8ff"];']
    for r in risks:
        col = {"High": "#ffb3b3", "Medium": "#ffe0a3", "Low": "#e6f2d9"}[r["level"]]
        out.append(f'r{r["id"]} [label="Problem R{r["id"]} (score {r["score"]})\\n{wrap(r["description"])}", fillcolor="{col}"];')
        out.append(f'p{r["id"]} [label="Prevent: {wrap(r["preventive_action"])}", fillcolor="#d9f2d9"];')
        out.append(f'c{r["id"]} [label="If it occurs: {wrap(r["corrective_action"])}", fillcolor="#fff2cc"];')
        out.append(f'goal -> r{r["id"]}; r{r["id"]} -> p{r["id"]} [label="preventive"]; r{r["id"]} -> c{r["id"]} [style=dashed, label="corrective"];')
    return "\n".join(out + ["}"])


def page_quality(conn, snap):
    st.header("5. Quality Management and Risk Control")
    t = st.tabs(["Defects", "Checklist and inspections", "Prioritization matrix", "PDPC"])
    with t[0]:
        rows = [dict(r) for r in conn.execute("""SELECT d.id, d.title, d.severity, d.status, t.name AS assignee,
                 'A' || d.activity_id AS activity, d.reported_on FROM defects d LEFT JOIN team t ON t.id=d.assignee_id ORDER BY d.id""")]
        table(rows)
        c1, c2 = st.columns(2)
        with c1.form("def_add", clear_on_submit=True):
            ti = st.text_input("Defect title")
            sv = st.selectbox("Severity", ["Critical", "Major", "Minor"], index=1)
            tm = team_map(conn)
            asg = st.selectbox("Assigned to", list(tm), format_func=tm.get)
            names = act_map(conn)
            ac = st.selectbox("Related activity", [None] + list(names), format_func=lambda x: "None" if x is None else names[x])
            if st.form_submit_button("Log defect"):
                act(pm.add_defect, conn, ti, sv, asg, ac, ok="Defect logged.")
        with c2.form("def_upd"):
            ids = [r["id"] for r in rows]
            did = st.selectbox("Defect", ids, format_func=lambda i: f"D{i} {next(r['title'] for r in rows if r['id'] == i)}") if ids else None
            stt = st.selectbox("New status", ["Open", "In Progress", "Resolved", "Closed"])
            if st.form_submit_button("Update status") and did:
                act(pm.update_defect_status, conn, did, stt, ok="Defect updated.")
    with t[1]:
        rows = [dict(r) for r in conn.execute("SELECT * FROM checklist ORDER BY deliverable, id")]
        table(rows, ["id", "deliverable", "item", "result", "notes", "inspected_on"])
        c1, c2 = st.columns(2)
        with c1.form("chk_add", clear_on_submit=True):
            dv, it = st.text_input("Deliverable"), st.text_input("Checklist item")
            if st.form_submit_button("Add checklist item"):
                act(pm.add_check_item, conn, dv, it, ok="Checklist item added.")
        with c2.form("chk_rec"):
            ids = [r["id"] for r in rows]
            cid = st.selectbox("Item", ids, format_func=lambda i: next(f"{r['deliverable']}: {r['item']}" for r in rows if r["id"] == i)) if ids else None
            res = st.selectbox("Result", ["Pass", "Fail", "Pending"])
            nt = st.text_input("Notes (required on Fail)")
            dt = st.date_input("Inspection date", snap["status_date"])
            if st.form_submit_button("Record inspection") and cid:
                act(pm.record_inspection, conn, cid, res, nt, dt, ok="Inspection recorded.")
    risks = pm.risk_ranking(conn)
    with t[2]:
        table(risks, ["rank", "id", "description", "likelihood", "impact", "score", "level", "status"],
              {"rank": "Rank", "id": "ID", "description": "Risk", "likelihood": "Likelihood", "impact": "Impact", "score": "Score", "level": "Level", "status": "Status"})
        z = [[l * i for l in range(1, 6)] for i in range(1, 6)]
        txt = [[", ".join(f"R{r['id']}" for r in risks if r["likelihood"] == l and r["impact"] == i) for l in range(1, 6)] for i in range(1, 6)]
        fig = go.Figure(go.Heatmap(z=z, x=[1, 2, 3, 4, 5], y=[1, 2, 3, 4, 5], text=txt, texttemplate="%{text}",
                                   colorscale=[[0, "#d9f2d9"], [0.4, "#ffe9a8"], [1, "#ff8f8f"]], showscale=False))
        fig.update_layout(xaxis_title="Likelihood", yaxis_title="Impact", height=420, margin=dict(t=20))
        plot(fig)
        with st.form("risk_add", clear_on_submit=True):
            ds = st.text_input("Risk description")
            c1, c2 = st.columns(2)
            lk, im = c1.slider("Likelihood", 1, 5, 3), c2.slider("Impact", 1, 5, 3)
            pv, co = st.text_input("Preventive action"), st.text_input("Corrective action")
            if st.form_submit_button("Add risk"):
                act(pm.add_risk, conn, ds, lk, im, pv, co, ok="Risk added.")
    with t[3]:
        st.caption("Process Decision Program Chart: objective, potential problems, preventive and corrective actions.")
        st.graphviz_chart(pdpc_dot(risks, snap["charter"]["name"] + " delivered on time and in budget"))


# ------------------------------------------------------------------- main
def main():
    conn = pm.connect()
    pm.init_db(conn, seed=True)
    pages = {"Dashboard and report": page_dashboard, "1. Initiation and integration": page_charter,
             "2. Scope and WBS": page_scope, "3. Schedule and resources": page_schedule,
             "4. Cost and EVM": page_cost, "5. Quality and risk": page_quality}
    st.sidebar.title("Healthcare PM System")
    choice = st.sidebar.radio("Module", list(pages))
    with st.sidebar.expander("Sample data"):
        if st.checkbox("I want to reset all data"):
            if st.button("Reset to sample data"):
                pm.reset_db(conn)
                flash("success", "Sample data restored.")
                st.rerun()
    show_flash()
    try:
        snap = pm.snapshot(conn)
        pages[choice](conn, snap)
    except ValidationError as e:
        st.error(str(e))
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
    finally:
        conn.close()


main()
