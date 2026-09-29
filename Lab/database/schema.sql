PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    title TEXT,
    authority TEXT,
    lead_examiner TEXT,
    source_timezone TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'suspended', 'closed', 'archived')),
    opened_at_utc TEXT NOT NULL,
    closed_at_utc TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    parent_evidence_id TEXT REFERENCES evidence_items(evidence_id),
    source_path TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    description TEXT,
    size_bytes INTEGER CHECK (size_bytes IS NULL OR size_bytes >= 0),
    sha256 TEXT,
    sha512 TEXT,
    acquired_at_utc TEXT,
    verified_at_utc TEXT,
    write_protected INTEGER NOT NULL DEFAULT 0 CHECK (write_protected IN (0, 1)),
    metadata_json TEXT,
    UNIQUE (case_id, source_path)
);

CREATE TABLE IF NOT EXISTS custody_events (
    custody_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    evidence_id TEXT NOT NULL REFERENCES evidence_items(evidence_id),
    event_at_utc TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    source_location TEXT,
    destination_location TEXT,
    purpose TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS working_copies (
    working_copy_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    evidence_id TEXT NOT NULL REFERENCES evidence_items(evidence_id),
    path TEXT NOT NULL,
    format TEXT,
    size_bytes INTEGER CHECK (size_bytes IS NULL OR size_bytes >= 0),
    sha256 TEXT NOT NULL,
    sha512 TEXT,
    created_at_utc TEXT NOT NULL,
    verified_at_utc TEXT NOT NULL,
    UNIQUE (case_id, path)
);

CREATE TABLE IF NOT EXISTS methods (
    method_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    purpose TEXT NOT NULL,
    validation_reference TEXT,
    limitations TEXT
);

CREATE TABLE IF NOT EXISTS tool_runs (
    tool_run_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    method_id TEXT REFERENCES methods(method_id),
    tool_name TEXT NOT NULL,
    tool_version TEXT NOT NULL,
    command_line TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (length(trim(purpose)) > 0),
    parameter_explanation TEXT NOT NULL CHECK (length(trim(parameter_explanation)) > 0),
    input_reference TEXT NOT NULL,
    input_sha256 TEXT,
    output_path TEXT,
    output_summary TEXT,
    operator TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    ended_at_utc TEXT,
    exit_status INTEGER,
    stdout_log_path TEXT,
    stderr_log_path TEXT,
    limitations TEXT
);

CREATE TRIGGER IF NOT EXISTS tool_runs_require_documentation_insert
BEFORE INSERT ON tool_runs
WHEN length(trim(COALESCE(NEW.purpose, ''))) = 0
  OR length(trim(COALESCE(NEW.parameter_explanation, ''))) = 0
BEGIN
    SELECT RAISE(ABORT, 'tool run requires purpose and parameter explanation');
END;

CREATE TRIGGER IF NOT EXISTS tool_runs_require_documentation_update
BEFORE UPDATE OF purpose, parameter_explanation ON tool_runs
WHEN length(trim(COALESCE(NEW.purpose, ''))) = 0
  OR length(trim(COALESCE(NEW.parameter_explanation, ''))) = 0
BEGIN
    SELECT RAISE(ABORT, 'tool run requires purpose and parameter explanation');
END;

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    evidence_id TEXT NOT NULL REFERENCES evidence_items(evidence_id),
    tool_run_id TEXT REFERENCES tool_runs(tool_run_id),
    artifact_type TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    observed_at_utc TEXT,
    source_timestamp TEXT,
    source_timezone TEXT,
    attributes_json TEXT,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    finding_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    title TEXT NOT NULL,
    observation TEXT NOT NULL,
    interpretation TEXT,
    hypothesis TEXT,
    conclusion TEXT,
    confidence TEXT CHECK (confidence IS NULL OR confidence IN ('low', 'medium', 'high')),
    limitations TEXT,
    created_by TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    reviewed_by TEXT,
    reviewed_at_utc TEXT
);

CREATE TABLE IF NOT EXISTS finding_artifacts (
    finding_id TEXT NOT NULL REFERENCES findings(finding_id),
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
    relationship TEXT NOT NULL,
    PRIMARY KEY (finding_id, artifact_id)
);

CREATE TABLE IF NOT EXISTS generated_files (
    generated_file_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    tool_run_id TEXT REFERENCES tool_runs(tool_run_id),
    path TEXT NOT NULL,
    purpose TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    sha512 TEXT,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    created_at_utc TEXT NOT NULL,
    UNIQUE (case_id, path, sha256)
);

CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence_items(case_id);
CREATE INDEX IF NOT EXISTS idx_custody_evidence_time ON custody_events(evidence_id, event_at_utc);
CREATE INDEX IF NOT EXISTS idx_tool_runs_case_time ON tool_runs(case_id, started_at_utc);
CREATE INDEX IF NOT EXISTS idx_artifacts_evidence_type ON artifacts(evidence_id, artifact_type);
CREATE INDEX IF NOT EXISTS idx_findings_case ON findings(case_id);
