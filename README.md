# Smart Healthcare Project Management System

Python, Streamlit (GUI), SQLite (database). All calculations are done in code (pm_core.py).

## Run
    pip install -r requirements.txt
    streamlit run app.py
Windows: double click run.bat. The database healthcare_pm.db is created with sample data on first start.
Sidebar > Sample data resets everything.

## Files
- app.py: GUI (6 pages)
- pm_core.py: database, validation, change control, scheduling, delay impact, EVM, alerts, risk ranking
- schema.sql: database schema. sample_data.sql: sample data dump
- test_cases.py: 29 test cases (python test_cases.py writes test_results.md)

## Module map
1. Initiation and integration: charter, plan, team, milestones, status, closure
2. Scope and WBS: requirements, auto WBS, change requests, change impact preview
3. Schedule and resources: activities, dependencies, delays, Gantt chart
4. Cost and EVM: estimates, actuals, PV EV AC CPI SPI, thresholds and warnings
5. Quality and risk: defects, checklist, prioritization matrix, PDPC
6. Dashboard and report: progress, pending changes, delays, budget, critical defects

## Demo script (about 5 minutes)
1. Dashboard: forecast finish is after the deadline, CPI and SPI warnings, 2 critical defects.
2. Scope > Requirements: R7 and R8 are Proposed. Scope > WBS: they are not in the WBS.
3. Schedule > Activities: AI and mobile activities show "Excluded".
4. Scope > Change impact: select CR-1, read before and after, click Approve.
5. Dashboard: scope, WBS, forecast, budget and deadline all changed. Repeat for CR-2.
6. Schedule > Update progress: A9 to 100% is blocked by the open critical defect.
7. Cost > Earned value: change the status date or thresholds and watch the warnings.
8. Quality: resolve the defect, then complete A9. Try entering invalid values for validation messages.
