-- Smart Healthcare Project Management System: database schema (SQLite)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS charter (
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

CREATE TABLE IF NOT EXISTS plan (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    scope_plan    TEXT DEFAULT '',
    schedule_plan TEXT DEFAULT '',
    cost_plan     TEXT DEFAULT '',
    quality_plan  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS team (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL UNIQUE,
    role             TEXT NOT NULL,
    responsibilities TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS requirements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority    TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('High','Medium','Low')),
    status      TEXT NOT NULL DEFAULT 'Proposed' CHECK (status IN ('Proposed','Approved','Rejected'))
);

CREATE TABLE IF NOT EXISTS change_requests (
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

CREATE TABLE IF NOT EXISTS wbs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    code           TEXT NOT NULL,
    name           TEXT NOT NULL,
    parent_id      INTEGER REFERENCES wbs(id),
    level_type     TEXT NOT NULL CHECK (level_type IN ('Project','Deliverable','Work Package')),
    requirement_id INTEGER REFERENCES requirements(id)
);

CREATE TABLE IF NOT EXISTS activities (
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

CREATE TABLE IF NOT EXISTS dependencies (
    activity_id    INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    predecessor_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    PRIMARY KEY (activity_id, predecessor_id),
    CHECK (activity_id <> predecessor_id)
);

CREATE TABLE IF NOT EXISTS milestones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    due_date    TEXT NOT NULL,
    activity_id INTEGER REFERENCES activities(id) ON DELETE SET NULL,
    achieved    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS defects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    severity    TEXT NOT NULL CHECK (severity IN ('Critical','Major','Minor')),
    assignee_id INTEGER REFERENCES team(id),
    activity_id INTEGER REFERENCES activities(id) ON DELETE SET NULL,
    status      TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','In Progress','Resolved','Closed')),
    reported_on TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checklist (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    deliverable  TEXT NOT NULL,
    item         TEXT NOT NULL,
    result       TEXT NOT NULL DEFAULT 'Pending' CHECK (result IN ('Pending','Pass','Fail')),
    notes        TEXT DEFAULT '',
    inspected_on TEXT
);

CREATE TABLE IF NOT EXISTS risks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    description       TEXT NOT NULL,
    likelihood        INTEGER NOT NULL CHECK (likelihood BETWEEN 1 AND 5),
    impact            INTEGER NOT NULL CHECK (impact BETWEEN 1 AND 5),
    preventive_action TEXT NOT NULL,
    corrective_action TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Mitigated','Occurred'))
);
