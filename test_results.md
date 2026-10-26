# Test results

| ID | Test | Expected | Actual | Result |
|---|---|---|---|---|
| TC01 | Baseline finish from forward pass (no delays) | 2026-10-17 | 2026-10-17 | PASS |
| TC02 | Forecast finish with recorded delays | 2026-10-29 | 2026-10-29 | PASS |
| TC03 | Circular dependency is rejected | rejected | rejected | PASS |
| TC04 | Self dependency is rejected | rejected | rejected | PASS |
| TC05 | EVM indicators at status date 2026-09-14 | BAC=4600000 PV=3825000 EV=3570000 AC=3780000 CPI=0.9444 SPI=0.9333 | BAC=4600000 PV=3825000 EV=3570000 AC=3780000 CPI=0.9444 SPI=0.9333 | PASS |
| TC06 | Estimate at completion = BAC / CPI | 4870588 | 4870588 | PASS |
| TC07 | Warnings fire below 0.95 thresholds | CPI warning=True, SPI warning=True | CPI warning=True, SPI warning=True | PASS |
| TC08 | Alert when forecast finish passes deadline | True | True | PASS |
| TC09 | Delayed activities (direct and knock-on) | 5,8,9,11,12,13 | 5,8,9,11,12,13 | PASS |
| TC10 | Unapproved requirements excluded from scope and cost | BAC=4600000, in-scope activities=13, excluded=4 | BAC=4600000, in-scope activities=13, excluded=4 | PASS |
| TC11 | WBS holds only approved requirements (6 deliverables) | 6 | 6 | PASS |
| TC12 | Approving CR-1 changes scope, budget, deadline | status=Approved, BAC=5050000, budget=5450000, deadline=2026-11-08 | status=Approved, BAC=5050000, budget=5450000, deadline=2026-11-08 | PASS |
| TC13 | Approving both CRs (PKR 800,000 and 3 weeks) | budget=5800000, deadline=2026-11-15, forecast=2026-11-12, deliverables=8 | budget=5800000, deadline=2026-11-15, forecast=2026-11-12, deliverables=8 | PASS |
| TC14 | Rejecting CR-1 keeps scope unchanged | req=Rejected, BAC=4600000 | req=Rejected, BAC=4600000 | PASS |
| TC15 | A decided CR cannot be decided again | rejected | rejected | PASS |
| TC16 | Requirement with pending CR cannot be approved directly | rejected | rejected | PASS |
| TC17 | Activity for rejected requirement is rejected | rejected | rejected | PASS |
| TC18 | Progress on unapproved requirement is rejected | rejected | rejected | PASS |
| TC19 | Invalid duration, cost, percent, actual cost rejected | rejected,rejected,rejected,rejected | rejected,rejected,rejected,rejected | PASS |
| TC20 | Blank title, blank justification, unassigned defect rejected | rejected,rejected,rejected | rejected,rejected,rejected | PASS |
| TC21 | Deadline before start and malformed date rejected | rejected,rejected | rejected,rejected | PASS |
| TC22 | Cannot complete activity with open critical defect | rejected | rejected | PASS |
| TC23 | After defect resolved, completion is accepted | accepted | accepted | PASS |
| TC24 | Cannot close project with blockers | rejected | rejected | PASS |
| TC25 | Milestone cannot be achieved while activity incomplete | rejected | rejected | PASS |
| TC26 | Risk ranking: likelihood x impact | top=R2 score=20 level=High | top=R2 score=20 level=High | PASS |
| TC27 | Failed inspection requires notes | rejected | rejected | PASS |
| TC28 | 5 extra delay days on critical activity move finish by 5 days | 5 | 5 | PASS |
| TC29 | Data persists in the database after reconnect | 1 | 1 | PASS |

29 of 29 passed.