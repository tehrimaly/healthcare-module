BEGIN TRANSACTION;
CREATE TABLE activities (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    requirement_id   INTEGER NOT NULL REFERENCES requirements(id),
    wbs_id           INTEGER REFERENCES wbs(id),
    assignee_id      INTEGER REFERENCES team(id),
    duration_days    INTEGER NOT NULL CHECK (duration_days > 0),
    planned_cost     REAL NOT NULL DEFAULT 0 CHECK (planned_cost >= 0),
    actual_cost      REAL NOT NULL DEFAULT 0 CHECK (actual_cost >= 0),
    percent_complete REAL NOT NULL DEFAULT 0 CHECK (percent_complete BETWEEN 0 AND 100),
    delay_days       INTEGER NOT NULL DEFAULT 0 CHECK (delay_days >= 0)
);
INSERT INTO "activities" VALUES(1,'Requirements gathering and SRS',1,3,1,10,300000.0,310000.0,100.0,0);
INSERT INTO "activities" VALUES(2,'System architecture design',1,4,2,7,250000.0,250000.0,100.0,0);
INSERT INTO "activities" VALUES(3,'Database schema design',1,5,6,8,200000.0,210000.0,100.0,0);
INSERT INTO "activities" VALUES(4,'UI/UX design',1,6,4,10,250000.0,260000.0,100.0,0);
INSERT INTO "activities" VALUES(5,'Appointment module (backend)',2,8,2,22,600000.0,680000.0,100.0,4);
INSERT INTO "activities" VALUES(6,'Lab reports module (backend)',3,11,3,15,500000.0,520000.0,100.0,0);
INSERT INTO "activities" VALUES(7,'Doctor schedule and consultation (backend)',4,14,3,15,450000.0,470000.0,100.0,0);
INSERT INTO "activities" VALUES(8,'Billing module (backend)',5,16,2,12,400000.0,420000.0,100.0,0);
INSERT INTO "activities" VALUES(9,'Web frontend: appointments and doctors',2,9,4,28,450000.0,300000.0,60.0,8);
INSERT INTO "activities" VALUES(10,'Web frontend: labs and billing',3,12,5,15,350000.0,360000.0,100.0,0);
INSERT INTO "activities" VALUES(11,'System integration',6,18,2,12,300000.0,0.0,0.0,0);
INSERT INTO "activities" VALUES(12,'System testing',6,19,7,14,300000.0,0.0,0.0,0);
INSERT INTO "activities" VALUES(13,'UAT and deployment',6,20,1,10,250000.0,0.0,0.0,0);
INSERT INTO "activities" VALUES(14,'AI diagnosis model development',7,NULL,3,14,300000.0,0.0,0.0,0);
INSERT INTO "activities" VALUES(15,'AI module integration and clinical validation',7,NULL,2,28,150000.0,0.0,0.0,0);
INSERT INTO "activities" VALUES(16,'Mobile app development',8,NULL,4,21,250000.0,0.0,0.0,0);
INSERT INTO "activities" VALUES(17,'Mobile app integration and release',8,NULL,5,21,100000.0,0.0,0.0,0);
CREATE TABLE change_requests (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    title                TEXT NOT NULL,
    requirement_id       INTEGER REFERENCES requirements(id),
    justification        TEXT NOT NULL,
    cost_impact          REAL NOT NULL DEFAULT 0 CHECK (cost_impact >= 0),
    schedule_impact_weeks REAL NOT NULL DEFAULT 0 CHECK (schedule_impact_weeks >= 0),
    status               TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending','Approved','Rejected')),
    submitted_on         TEXT NOT NULL,
    decided_on           TEXT
);
INSERT INTO "change_requests" VALUES(1,'Add AI-based preliminary diagnosis module',7,'Hospital management wants faster triage and reduced doctor workload.',450000.0,2.0,'Pending','2026-09-01',NULL);
INSERT INTO "change_requests" VALUES(2,'Add patient mobile application',8,'Patients need mobile access to appointments and lab reports.',350000.0,1.0,'Pending','2026-09-03',NULL);
CREATE TABLE charter (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    name             TEXT NOT NULL,
    objectives       TEXT NOT NULL,
    stakeholders     TEXT NOT NULL,
    scope_boundaries TEXT NOT NULL,
    approved_budget  REAL NOT NULL CHECK (approved_budget > 0),
    start_date       TEXT NOT NULL,
    deadline         TEXT NOT NULL,
    status_date      TEXT NOT NULL,
    manager          TEXT,
    status           TEXT NOT NULL DEFAULT 'Planning'
                     CHECK (status IN ('Initiating','Planning','Executing','Monitoring','Closed')),
    closed           INTEGER NOT NULL DEFAULT 0,
    closure_notes    TEXT DEFAULT ''
);
INSERT INTO "charter" VALUES(1,'Smart Healthcare Project Management and Monitoring System','Deliver one system for five hospitals covering patient appointments, laboratory reports, doctor schedules, online consultations and billing, within 16 weeks and PKR 5,000,000.','Hospital management (sponsor), doctors, lab technicians, billing staff, patients, development company, QA team.','In scope: appointments, lab reports, doctor schedules, online consultations, billing. Out of scope until approved by change request: AI diagnosis, mobile app, insurance integration.',5000000.0,'2026-07-06','2026-10-25','2026-09-14','Ayesha Khan','Monitoring',0,'');
CREATE TABLE checklist (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    deliverable  TEXT NOT NULL,
    item         TEXT NOT NULL,
    result       TEXT NOT NULL DEFAULT 'Pending' CHECK (result IN ('Pending','Pass','Fail')),
    notes        TEXT DEFAULT '',
    inspected_on TEXT
);
INSERT INTO "checklist" VALUES(1,'SRS document','Requirements traceable to hospital needs','Pass','','2026-07-15');
INSERT INTO "checklist" VALUES(2,'Appointment module','Prevents double booking','Fail','Slot conflict under concurrent bookings','2026-09-08');
INSERT INTO "checklist" VALUES(3,'Appointment module','Confirmation messages sent','Pass','','2026-09-08');
INSERT INTO "checklist" VALUES(4,'Patient records','Records saved without data loss','Fail','Lost update on concurrent edit','2026-09-10');
INSERT INTO "checklist" VALUES(5,'Lab reports','Reports linked to correct patient ID','Pass','','2026-09-05');
INSERT INTO "checklist" VALUES(6,'Billing module','Invoice totals computed correctly','Pass','','2026-08-26');
INSERT INTO "checklist" VALUES(7,'Billing module','UI follows approved mockups','Pending','',NULL);
INSERT INTO "checklist" VALUES(8,'Security','Role based access verified','Pending','',NULL);
CREATE TABLE defects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    severity    TEXT NOT NULL CHECK (severity IN ('Critical','Major','Minor')),
    assignee_id INTEGER REFERENCES team(id),
    activity_id INTEGER REFERENCES activities(id) ON DELETE SET NULL,
    status      TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','In Progress','Resolved','Closed')),
    reported_on TEXT NOT NULL
);
INSERT INTO "defects" VALUES(1,'Double booking possible when two receptionists book the same slot','Critical',4,9,'In Progress','2026-09-08');
INSERT INTO "defects" VALUES(2,'Patient record lost on concurrent edit','Critical',6,11,'Open','2026-09-10');
INSERT INTO "defects" VALUES(3,'Billing total rounding error','Major',2,8,'Resolved','2026-08-20');
INSERT INTO "defects" VALUES(4,'Lab report PDF export fails for long reports','Major',3,6,'In Progress','2026-09-05');
INSERT INTO "defects" VALUES(5,'Label misaligned on billing screen','Minor',5,10,'Open','2026-09-09');
INSERT INTO "defects" VALUES(6,'Typo on appointment confirmation','Minor',4,9,'Closed','2026-08-30');
CREATE TABLE dependencies (
    activity_id    INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    predecessor_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    PRIMARY KEY (activity_id, predecessor_id),
    CHECK (activity_id <> predecessor_id)
);
INSERT INTO "dependencies" VALUES(2,1);
INSERT INTO "dependencies" VALUES(3,1);
INSERT INTO "dependencies" VALUES(4,1);
INSERT INTO "dependencies" VALUES(5,2);
INSERT INTO "dependencies" VALUES(5,3);
INSERT INTO "dependencies" VALUES(6,2);
INSERT INTO "dependencies" VALUES(6,3);
INSERT INTO "dependencies" VALUES(7,6);
INSERT INTO "dependencies" VALUES(8,5);
INSERT INTO "dependencies" VALUES(9,4);
INSERT INTO "dependencies" VALUES(9,5);
INSERT INTO "dependencies" VALUES(10,4);
INSERT INTO "dependencies" VALUES(10,6);
INSERT INTO "dependencies" VALUES(11,7);
INSERT INTO "dependencies" VALUES(11,8);
INSERT INTO "dependencies" VALUES(11,9);
INSERT INTO "dependencies" VALUES(11,10);
INSERT INTO "dependencies" VALUES(12,11);
INSERT INTO "dependencies" VALUES(13,12);
INSERT INTO "dependencies" VALUES(13,15);
INSERT INTO "dependencies" VALUES(13,17);
INSERT INTO "dependencies" VALUES(14,3);
INSERT INTO "dependencies" VALUES(15,14);
INSERT INTO "dependencies" VALUES(15,11);
INSERT INTO "dependencies" VALUES(16,4);
INSERT INTO "dependencies" VALUES(16,5);
INSERT INTO "dependencies" VALUES(17,16);
INSERT INTO "dependencies" VALUES(17,11);
CREATE TABLE milestones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    due_date    TEXT NOT NULL,
    activity_id INTEGER REFERENCES activities(id) ON DELETE SET NULL,
    achieved    INTEGER NOT NULL DEFAULT 0
);
INSERT INTO "milestones" VALUES(1,'SRS approved','2026-07-15',1,1);
INSERT INTO "milestones" VALUES(2,'Design complete','2026-07-25',4,1);
INSERT INTO "milestones" VALUES(3,'Backend complete','2026-08-26',8,1);
INSERT INTO "milestones" VALUES(4,'Integration complete','2026-09-23',11,0);
INSERT INTO "milestones" VALUES(5,'UAT and go live','2026-10-17',13,0);
CREATE TABLE plan (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    scope_plan    TEXT DEFAULT '',
    schedule_plan TEXT DEFAULT '',
    cost_plan     TEXT DEFAULT '',
    quality_plan  TEXT DEFAULT ''
);
INSERT INTO "plan" VALUES(1,'Scope is baselined from approved requirements. New requirements enter scope only through an approved change request.','16 weeks starting 6 July 2026. Activities are sequenced by finish-to-start dependencies; delays are tracked weekly.','Budget PKR 5,000,000 (PKR 400,000 reserve above planned activity cost). Cost tracked with EVM; warning at CPI/SPI below 0.95.','Every deliverable passes a checklist inspection. No release with unresolved critical defects.');
CREATE TABLE requirements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority    TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('High','Medium','Low')),
    status      TEXT NOT NULL DEFAULT 'Proposed' CHECK (status IN ('Proposed','Approved','Rejected'))
);
INSERT INTO "requirements" VALUES(1,'R1','Project foundation and design','Requirements, architecture, database and UI design','High','Approved');
INSERT INTO "requirements" VALUES(2,'R2','Patient appointment management','Online and front desk booking with conflict prevention','High','Approved');
INSERT INTO "requirements" VALUES(3,'R3','Laboratory report management','Order, record and publish lab reports','High','Approved');
INSERT INTO "requirements" VALUES(4,'R4','Doctor schedules and online consultation','Doctor availability and video consultations','High','Approved');
INSERT INTO "requirements" VALUES(5,'R5','Hospital billing','Invoices, payments and reports','Medium','Approved');
INSERT INTO "requirements" VALUES(6,'R6','Integration, testing and deployment','System integration, QA and go live','High','Approved');
INSERT INTO "requirements" VALUES(7,'R7','AI-based preliminary diagnosis','Symptom based preliminary diagnosis for doctors','Medium','Proposed');
INSERT INTO "requirements" VALUES(8,'R8','Mobile application','Patient mobile app for booking and reports','Medium','Proposed');
CREATE TABLE risks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    description       TEXT NOT NULL,
    likelihood        INTEGER NOT NULL CHECK (likelihood BETWEEN 1 AND 5),
    impact            INTEGER NOT NULL CHECK (impact BETWEEN 1 AND 5),
    preventive_action TEXT NOT NULL,
    corrective_action TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Mitigated','Occurred'))
);
INSERT INTO "risks" VALUES(1,'Scope creep from hospital management',4,4,'Enforce change control board and written approval','Re-baseline schedule and budget after approval','Occurred');
INSERT INTO "risks" VALUES(2,'Critical defects in scheduling and patient records',4,5,'Peer reviews and automated regression tests','Dedicated bug fix sprint and extra QA hours','Occurred');
INSERT INTO "risks" VALUES(3,'Key developer unavailable',2,4,'Pair programming and documentation','Reassign work and use contract developer','Open');
INSERT INTO "risks" VALUES(4,'Budget overrun from rework',3,4,'Weekly EVM review with thresholds','Use cost reserve or request budget change','Open');
INSERT INTO "risks" VALUES(5,'Patient data privacy breach',2,5,'Encryption and role based access','Incident response plan and notification','Open');
INSERT INTO "risks" VALUES(6,'Integration delays across five hospital systems',3,3,'Early interface agreements and mock services','Add integration engineer, phase rollout','Open');
INSERT INTO "risks" VALUES(7,'Doctors do not trust AI diagnosis output',3,4,'Clinical validation with doctors','Limit to advisory mode','Open');
INSERT INTO "risks" VALUES(8,'Hospital staff resist new system',2,3,'Training sessions and champions','Extra on site support','Open');
CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value REAL NOT NULL
);
INSERT INTO "settings" VALUES('cpi_warn',0.95);
INSERT INTO "settings" VALUES('spi_warn',0.95);
INSERT INTO "settings" VALUES('critical',0.85);
CREATE TABLE team (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL UNIQUE,
    role             TEXT NOT NULL,
    responsibilities TEXT DEFAULT ''
);
INSERT INTO "team" VALUES(1,'Ayesha Khan','Project Manager','Planning, tracking, change control, stakeholder reporting');
INSERT INTO "team" VALUES(2,'Hamza Ali','Backend Developer','Appointment, billing and integration services');
INSERT INTO "team" VALUES(3,'Sara Malik','Backend Developer','Lab reports, doctor schedule and consultation services');
INSERT INTO "team" VALUES(4,'Usman Tariq','Frontend Developer','UI/UX design and appointment screens');
INSERT INTO "team" VALUES(5,'Mehwish Noor','Frontend Developer','Lab and billing screens');
INSERT INTO "team" VALUES(6,'Bilal Ahmed','Database Developer','Schema design, performance and data integrity');
INSERT INTO "team" VALUES(7,'Fatima Zahra','QA Engineer','Test planning, inspections, defect verification');
CREATE TABLE wbs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    code           TEXT NOT NULL,
    name           TEXT NOT NULL,
    parent_id      INTEGER REFERENCES wbs(id),
    level_type     TEXT NOT NULL CHECK (level_type IN ('Project','Deliverable','Work Package')),
    requirement_id INTEGER REFERENCES requirements(id)
);
INSERT INTO "wbs" VALUES(1,'1','Smart Healthcare Project Management and Monitoring System',NULL,'Project',NULL);
INSERT INTO "wbs" VALUES(2,'1.1','Project foundation and design',1,'Deliverable',1);
INSERT INTO "wbs" VALUES(3,'1.1.1','Requirements gathering and SRS',2,'Work Package',1);
INSERT INTO "wbs" VALUES(4,'1.1.2','System architecture design',2,'Work Package',1);
INSERT INTO "wbs" VALUES(5,'1.1.3','Database schema design',2,'Work Package',1);
INSERT INTO "wbs" VALUES(6,'1.1.4','UI/UX design',2,'Work Package',1);
INSERT INTO "wbs" VALUES(7,'1.2','Patient appointment management',1,'Deliverable',2);
INSERT INTO "wbs" VALUES(8,'1.2.1','Appointment module (backend)',7,'Work Package',2);
INSERT INTO "wbs" VALUES(9,'1.2.2','Web frontend: appointments and doctors',7,'Work Package',2);
INSERT INTO "wbs" VALUES(10,'1.3','Laboratory report management',1,'Deliverable',3);
INSERT INTO "wbs" VALUES(11,'1.3.1','Lab reports module (backend)',10,'Work Package',3);
INSERT INTO "wbs" VALUES(12,'1.3.2','Web frontend: labs and billing',10,'Work Package',3);
INSERT INTO "wbs" VALUES(13,'1.4','Doctor schedules and online consultation',1,'Deliverable',4);
INSERT INTO "wbs" VALUES(14,'1.4.1','Doctor schedule and consultation (backend)',13,'Work Package',4);
INSERT INTO "wbs" VALUES(15,'1.5','Hospital billing',1,'Deliverable',5);
INSERT INTO "wbs" VALUES(16,'1.5.1','Billing module (backend)',15,'Work Package',5);
INSERT INTO "wbs" VALUES(17,'1.6','Integration, testing and deployment',1,'Deliverable',6);
INSERT INTO "wbs" VALUES(18,'1.6.1','System integration',17,'Work Package',6);
INSERT INTO "wbs" VALUES(19,'1.6.2','System testing',17,'Work Package',6);
INSERT INTO "wbs" VALUES(20,'1.6.3','UAT and deployment',17,'Work Package',6);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('team',7);
INSERT INTO "sqlite_sequence" VALUES('requirements',8);
INSERT INTO "sqlite_sequence" VALUES('activities',17);
INSERT INTO "sqlite_sequence" VALUES('milestones',5);
INSERT INTO "sqlite_sequence" VALUES('change_requests',2);
INSERT INTO "sqlite_sequence" VALUES('defects',6);
INSERT INTO "sqlite_sequence" VALUES('checklist',8);
INSERT INTO "sqlite_sequence" VALUES('risks',8);
INSERT INTO "sqlite_sequence" VALUES('wbs',20);
COMMIT;