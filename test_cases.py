"""Test cases with expected and actual results.

Run:  python test_cases.py          (prints a table and writes test_results.md)
      python -m unittest test_cases (standard unittest run)
Expected values were worked out by hand from the sample data, not copied from the code.
"""
import sqlite3
import unittest
from datetime import date

import pm_core as pm
from pm_core import ValidationError


def fresh():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    pm.init_db(c, seed=True)
    return c


def raises(fn, *a):
    try:
        fn(*a)
        return "accepted"
    except ValidationError:
        return "rejected"


def tc_baseline_finish():
    return str(pm.snapshot(fresh())["planned_end"])


def tc_forecast_finish():
    return str(pm.snapshot(fresh())["forecast_end"])


def tc_cycle():
    c = fresh()
    return raises(pm.add_dependency, c, 1, 13)  # A13 already depends (indirectly) on A1


def tc_self_dep():
    return raises(pm.add_dependency, fresh(), 3, 3)


def tc_evm_values():
    e = pm.snapshot(fresh())["evm"]
    return f"BAC={e['bac']:.0f} PV={e['pv']:.0f} EV={e['ev']:.0f} AC={e['ac']:.0f} CPI={e['cpi']:.4f} SPI={e['spi']:.4f}"


def tc_eac():
    return f"{pm.snapshot(fresh())['evm']['eac']:.0f}"


def tc_warnings():
    c = fresh()
    msgs = [m for l, m in pm.alerts(c, pm.snapshot(c))]
    return f"CPI warning={any(m.startswith('CPI') for m in msgs)}, SPI warning={any(m.startswith('SPI') for m in msgs)}"


def tc_deadline_alert():
    c = fresh()
    return any("after the deadline" in m for l, m in pm.alerts(c, pm.snapshot(c)))


def tc_delayed_list():
    return ",".join(str(d["id"]) for d in pm.delayed_activities(pm.snapshot(fresh())))


def tc_unapproved_excluded():
    s = pm.snapshot(fresh())
    return f"BAC={s['evm']['bac']:.0f}, in-scope activities={len(s['in_scope'])}, excluded={len(s['excluded'])}"


def tc_wbs_excludes():
    c = fresh()
    return [r[0] for r in c.execute("SELECT code FROM wbs WHERE level_type='Deliverable'")].__len__()


def tc_cr_approval():
    c = fresh()
    pm.approve_change_request(c, 1)
    s = pm.snapshot(c)
    return (f"status={c.execute('SELECT status FROM requirements WHERE id=7').fetchone()[0]}, BAC={s['evm']['bac']:.0f}, "
            f"budget={s['budget']:.0f}, deadline={s['deadline']}")


def tc_both_crs():
    c = fresh()
    pm.approve_change_request(c, 1)
    pm.approve_change_request(c, 2)
    s = pm.snapshot(c)
    return f"budget={s['budget']:.0f}, deadline={s['deadline']}, forecast={s['forecast_end']}, deliverables={tc_count_deliverables(c)}"


def tc_count_deliverables(c):
    return c.execute("SELECT COUNT(*) FROM wbs WHERE level_type='Deliverable'").fetchone()[0]


def tc_reject_cr():
    c = fresh()
    pm.reject_change_request(c, 1)
    return f"req={c.execute('SELECT status FROM requirements WHERE id=7').fetchone()[0]}, BAC={pm.snapshot(c)['evm']['bac']:.0f}"


def tc_double_decision():
    c = fresh()
    pm.approve_change_request(c, 1)
    return raises(pm.approve_change_request, c, 1)


def tc_direct_approve_blocked():
    return raises(pm.set_requirement_status, fresh(), 7, "Approved")


def tc_rejected_req_activity():
    c = fresh()
    pm.reject_change_request(c, 1)
    return raises(pm.add_activity, c, "AI extra", 7, 2, 5, 1000)


def tc_progress_unapproved():
    return raises(pm.update_progress, fresh(), 14, 50, 1000, 0)


def tc_invalid_numbers():
    c = fresh()
    return ",".join([raises(pm.add_activity, c, "x", 1, 1, 0, 100), raises(pm.add_activity, c, "x", 1, 1, 5, -1),
                     raises(pm.update_progress, c, 11, 101, 0, 0), raises(pm.update_progress, c, 11, 10, -5, 0)])


def tc_blank_fields():
    c = fresh()
    return ",".join([raises(pm.add_requirement, c, "  ", "", "High"),
                     raises(pm.submit_change_request, c, "t", None, "", 0, 0),
                     raises(pm.add_defect, c, "bug", "Major", None, None)])


def tc_bad_dates():
    c = fresh()
    return ",".join([raises(pm.save_charter, c, "n", "o", "s", "b", 1000, "2026-10-01", "2026-09-01", "m"),
                     raises(pm.save_charter, c, "n", "o", "s", "b", 1000, "not-a-date", "2026-09-01", "m")])


def tc_critical_blocks_complete():
    return raises(pm.update_progress, fresh(), 9, 100, 300000, 0)  # A9 has an open critical defect


def tc_resolve_then_complete():
    c = fresh()
    pm.update_defect_status(c, 1, "Resolved")
    return raises(pm.update_progress, c, 9, 100, 300000, 0)


def tc_close_blocked():
    return raises(pm.close_project, fresh(), "lessons")


def tc_milestone_rule():
    return raises(pm.set_milestone_achieved, fresh(), 4, True)  # linked activity A11 is 0%


def tc_risk_rank():
    r = pm.risk_ranking(fresh())
    return f"top=R{r[0]['id']} score={r[0]['score']} level={r[0]['level']}"


def tc_fail_needs_notes():
    c = fresh()
    return raises(pm.record_inspection, c, 7, "Fail", "", date(2026, 9, 14))


def tc_delay_changes_deadline():
    c = fresh()
    base = pm.snapshot(c)["forecast_end"]
    pm.update_progress(c, 11, 0, 0, 5)  # delay critical activity A11 by 5 more days
    return (pm.snapshot(c)["forecast_end"] - base).days


def tc_persistence():
    import os, tempfile
    path = os.path.join(tempfile.mkdtemp(), "t.db")
    c = pm.connect(path)
    pm.init_db(c, seed=True)
    pm.add_requirement(c, "Insurance integration", "", "Low")
    c.close()
    c2 = pm.connect(path)
    return c2.execute("SELECT COUNT(*) FROM requirements WHERE title='Insurance integration'").fetchone()[0]


CASES = [
    ("TC01", "Baseline finish from forward pass (no delays)", "2026-10-17", tc_baseline_finish),
    ("TC02", "Forecast finish with recorded delays", "2026-10-29", tc_forecast_finish),
    ("TC03", "Circular dependency is rejected", "rejected", tc_cycle),
    ("TC04", "Self dependency is rejected", "rejected", tc_self_dep),
    ("TC05", "EVM indicators at status date 2026-09-14",
     "BAC=4600000 PV=3825000 EV=3570000 AC=3780000 CPI=0.9444 SPI=0.9333", tc_evm_values),
    ("TC06", "Estimate at completion = BAC / CPI", "4870588", tc_eac),
    ("TC07", "Warnings fire below 0.95 thresholds", "CPI warning=True, SPI warning=True", tc_warnings),
    ("TC08", "Alert when forecast finish passes deadline", True, tc_deadline_alert),
    ("TC09", "Delayed activities (direct and knock-on)", "5,8,9,11,12,13", tc_delayed_list),
    ("TC10", "Unapproved requirements excluded from scope and cost",
     "BAC=4600000, in-scope activities=13, excluded=4", tc_unapproved_excluded),
    ("TC11", "WBS holds only approved requirements (6 deliverables)", 6, tc_wbs_excludes),
    ("TC12", "Approving CR-1 changes scope, budget, deadline",
     "status=Approved, BAC=5050000, budget=5450000, deadline=2026-11-08", tc_cr_approval),
    ("TC13", "Approving both CRs (PKR 800,000 and 3 weeks)",
     "budget=5800000, deadline=2026-11-15, forecast=2026-11-12, deliverables=8", tc_both_crs),
    ("TC14", "Rejecting CR-1 keeps scope unchanged", "req=Rejected, BAC=4600000", tc_reject_cr),
    ("TC15", "A decided CR cannot be decided again", "rejected", tc_double_decision),
    ("TC16", "Requirement with pending CR cannot be approved directly", "rejected", tc_direct_approve_blocked),
    ("TC17", "Activity for rejected requirement is rejected", "rejected", tc_rejected_req_activity),
    ("TC18", "Progress on unapproved requirement is rejected", "rejected", tc_progress_unapproved),
    ("TC19", "Invalid duration, cost, percent, actual cost rejected", "rejected,rejected,rejected,rejected", tc_invalid_numbers),
    ("TC20", "Blank title, blank justification, unassigned defect rejected", "rejected,rejected,rejected", tc_blank_fields),
    ("TC21", "Deadline before start and malformed date rejected", "rejected,rejected", tc_bad_dates),
    ("TC22", "Cannot complete activity with open critical defect", "rejected", tc_critical_blocks_complete),
    ("TC23", "After defect resolved, completion is accepted", "accepted", tc_resolve_then_complete),
    ("TC24", "Cannot close project with blockers", "rejected", tc_close_blocked),
    ("TC25", "Milestone cannot be achieved while activity incomplete", "rejected", tc_milestone_rule),
    ("TC26", "Risk ranking: likelihood x impact", "top=R2 score=20 level=High", tc_risk_rank),
    ("TC27", "Failed inspection requires notes", "rejected", tc_fail_needs_notes),
    ("TC28", "5 extra delay days on critical activity move finish by 5 days", 5, tc_delay_changes_deadline),
    ("TC29", "Data persists in the database after reconnect", 1, tc_persistence),
]


def run_all():
    rows = []
    for tid, desc, expected, fn in CASES:
        try:
            actual = fn()
        except Exception as e:  # a crash is a failed test
            actual = f"ERROR {type(e).__name__}: {e}"
        rows.append((tid, desc, str(expected), str(actual), "PASS" if str(expected) == str(actual) else "FAIL"))
    return rows


class TestCases(unittest.TestCase):
    def test_all(self):
        for tid, desc, exp, act, res in run_all():
            with self.subTest(tid):
                self.assertEqual(exp, act, f"{tid} {desc}")


if __name__ == "__main__":
    results = run_all()
    lines = ["# Test results", "", "| ID | Test | Expected | Actual | Result |", "|---|---|---|---|---|"]
    lines += [f"| {t} | {d} | {e} | {a} | {r} |" for t, d, e, a, r in results]
    passed = sum(r[4] == "PASS" for r in results)
    lines += ["", f"{passed} of {len(results)} passed."]
    open("test_results.md", "w", encoding="utf-8").write("\n".join(lines))
    for t, d, e, a, r in results:
        print(f"{t} {r}  {d}\n      expected: {e}\n      actual:   {a}")
    print(f"\n{passed}/{len(results)} passed")
