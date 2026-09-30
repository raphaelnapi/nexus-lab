PRAGMA foreign_keys = ON;
PRAGMA synchronous = FULL;
PRAGMA journal_mode = DELETE;
PRAGMA trusted_schema = OFF;

CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at_utc TEXT NOT NULL,
    migration_hash TEXT NOT NULL
);

CREATE TABLE cases (
    case_id TEXT PRIMARY KEY,
    title TEXT,
    authority TEXT NOT NULL,
    scope TEXT NOT NULL,
    question TEXT NOT NULL,
    lead_examiner TEXT NOT NULL,
    source_timezone TEXT,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'suspended', 'closed', 'archived')),
    opened_at_utc TEXT NOT NULL,
    closed_at_utc TEXT,
    legacy_source TEXT,
    notes TEXT
);

CREATE TABLE case_roles (
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    principal TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('custodian','lead','examiner','reviewer','administrator')),
    assigned_at_utc TEXT NOT NULL,
    PRIMARY KEY (case_id, principal, role)
);

CREATE TABLE evidence_items (
    evidence_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    parent_evidence_id TEXT REFERENCES evidence_items(evidence_id),
    logical_name TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    sensitive_locator TEXT NOT NULL,
    description TEXT,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    sha512 TEXT NOT NULL CHECK (length(sha512) = 128),
    source_mtime_ns INTEGER,
    registered_at_utc TEXT NOT NULL,
    registered_by TEXT NOT NULL,
    verified_at_utc TEXT,
    write_protection TEXT NOT NULL DEFAULT 'reported'
        CHECK (write_protection IN ('observed','reported','not-determined')),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE (case_id, evidence_id)
);

CREATE TABLE custody_events (
    custody_event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    evidence_id TEXT NOT NULL REFERENCES evidence_items(evidence_id),
    event_at_utc TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    source_location TEXT,
    destination_location TEXT,
    purpose TEXT NOT NULL,
    notes TEXT
);

CREATE TRIGGER custody_events_no_update BEFORE UPDATE ON custody_events
BEGIN SELECT RAISE(ABORT, 'custody events are append-only'); END;
CREATE TRIGGER custody_events_no_delete BEFORE DELETE ON custody_events
BEGIN SELECT RAISE(ABORT, 'custody events are append-only'); END;

CREATE TABLE working_copies (
    working_copy_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    evidence_id TEXT NOT NULL REFERENCES evidence_items(evidence_id),
    relative_path TEXT NOT NULL,
    format TEXT,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    sha512 TEXT NOT NULL CHECK (length(sha512) = 128),
    created_at_utc TEXT NOT NULL,
    created_by TEXT NOT NULL,
    verified_at_utc TEXT NOT NULL,
    copy_method TEXT NOT NULL,
    UNIQUE (case_id, relative_path)
);

CREATE TABLE environments (
    environment_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    environment_type TEXT NOT NULL CHECK (environment_type IN ('windows-host','hyperv-worker')),
    captured_at_utc TEXT NOT NULL,
    details_json TEXT NOT NULL,
    details_sha256 TEXT NOT NULL
);

CREATE TABLE tool_versions (
    tool_version_id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    version TEXT NOT NULL,
    executable_path TEXT NOT NULL,
    binary_sha256 TEXT NOT NULL,
    signature_status TEXT NOT NULL,
    validated_at_utc TEXT,
    validation_reference TEXT,
    UNIQUE (provider_id, version, binary_sha256)
);

CREATE TABLE method_versions (
    method_id TEXT NOT NULL,
    version TEXT NOT NULL,
    definition_sha256 TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    purpose TEXT NOT NULL,
    validation_reference TEXT NOT NULL,
    limitations TEXT NOT NULL,
    definition_json TEXT NOT NULL,
    PRIMARY KEY (method_id, version)
);

CREATE TABLE approvals (
    approval_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    method_id TEXT NOT NULL,
    method_version TEXT NOT NULL,
    method_sha256 TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    approved_at_utc TEXT NOT NULL,
    expires_at_utc TEXT NOT NULL,
    parameter_bounds_json TEXT NOT NULL,
    parameter_bounds_sha256 TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','revoked','expired','consumed')),
    FOREIGN KEY (method_id, method_version) REFERENCES method_versions(method_id, version)
);

CREATE TABLE tool_runs (
    tool_run_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    approval_id TEXT NOT NULL REFERENCES approvals(approval_id),
    method_id TEXT NOT NULL,
    method_version TEXT NOT NULL,
    tool_version_id TEXT REFERENCES tool_versions(tool_version_id),
    environment_id TEXT REFERENCES environments(environment_id),
    purpose TEXT NOT NULL,
    command_json TEXT NOT NULL,
    parameter_explanation TEXT NOT NULL,
    operator TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    ended_at_utc TEXT,
    status TEXT NOT NULL CHECK (status IN ('started','succeeded','failed','timed-out','cancelled')),
    exit_status INTEGER,
    stdout_relative_path TEXT,
    stderr_relative_path TEXT,
    output_summary TEXT,
    limitations TEXT,
    retry_of TEXT REFERENCES tool_runs(tool_run_id)
);

CREATE TABLE run_inputs (
    tool_run_id TEXT NOT NULL REFERENCES tool_runs(tool_run_id),
    input_id TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('evidence','working-copy','generated-file','artifact')),
    entity_id TEXT NOT NULL,
    relative_path TEXT,
    sha256 TEXT NOT NULL,
    PRIMARY KEY (tool_run_id, input_id)
);

CREATE TABLE generated_files (
    generated_file_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    tool_run_id TEXT REFERENCES tool_runs(tool_run_id),
    relative_path TEXT NOT NULL,
    purpose TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    sha512 TEXT NOT NULL CHECK (length(sha512) = 128),
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    created_at_utc TEXT NOT NULL,
    UNIQUE (case_id, relative_path, sha256)
);

CREATE TABLE run_outputs (
    tool_run_id TEXT NOT NULL REFERENCES tool_runs(tool_run_id),
    output_id TEXT NOT NULL REFERENCES generated_files(generated_file_id),
    PRIMARY KEY (tool_run_id, output_id)
);

CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    evidence_id TEXT REFERENCES evidence_items(evidence_id),
    working_copy_id TEXT REFERENCES working_copies(working_copy_id),
    tool_run_id TEXT REFERENCES tool_runs(tool_run_id),
    artifact_type TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    created_at_utc TEXT NOT NULL,
    CHECK (evidence_id IS NOT NULL OR working_copy_id IS NOT NULL)
);

CREATE TABLE timeline_events (
    event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
    original_timestamp TEXT NOT NULL,
    timestamp_semantics TEXT NOT NULL,
    source_timezone TEXT NOT NULL,
    normalized_utc TEXT,
    resolution TEXT,
    uncertainty TEXT,
    description TEXT NOT NULL,
    interpretation_status TEXT NOT NULL
        CHECK (interpretation_status IN ('observed','derived','inferred','not-determined'))
);

CREATE TABLE statements (
    statement_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    state TEXT NOT NULL CHECK (state IN
        ('reported','observed','derived','inferred','concluded','unknown','not-observed','not-determined')),
    text TEXT NOT NULL,
    source_locator TEXT,
    assumptions TEXT,
    alternatives TEXT,
    confidence TEXT CHECK (confidence IS NULL OR confidence IN ('low','medium','high')),
    created_by TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE findings (
    finding_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','reviewed','accepted','rejected')),
    limitations TEXT,
    created_by TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE finding_support (
    finding_id TEXT NOT NULL REFERENCES findings(finding_id),
    statement_id TEXT NOT NULL REFERENCES statements(statement_id),
    relationship TEXT NOT NULL CHECK (relationship IN ('supports','contradicts','qualifies','concludes')),
    PRIMARY KEY (finding_id, statement_id, relationship)
);

CREATE TABLE reviews (
    review_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('accepted','changes-requested','rejected')),
    notes TEXT,
    reviewed_at_utc TEXT NOT NULL
);

CREATE TABLE reports (
    report_version_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    version INTEGER NOT NULL CHECK (version > 0),
    relative_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    review_id TEXT REFERENCES reviews(review_id),
    UNIQUE (case_id, report_id, version)
);

CREATE TABLE provenance_edges (
    edge_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    UNIQUE (case_id, source_type, source_id, relationship, target_type, target_id)
);

CREATE TABLE audit_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    event_at_utc TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    previous_hash TEXT,
    event_hash TEXT NOT NULL UNIQUE
);

CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END;
CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END;

CREATE TABLE ledger_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    last_sequence INTEGER NOT NULL,
    last_event_hash TEXT NOT NULL,
    database_sha256 TEXT,
    signature_status TEXT NOT NULL CHECK (signature_status IN ('unsigned','signed','invalid')),
    signature_path TEXT,
    created_at_utc TEXT NOT NULL,
    created_by TEXT NOT NULL
);

CREATE TABLE migration_records (
    migration_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    source_path TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    preview_json TEXT NOT NULL,
    migrated_at_utc TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('previewed','completed','failed')),
    UNIQUE (case_id, source_path, source_sha256)
);

CREATE INDEX idx_evidence_case ON evidence_items(case_id);
CREATE INDEX idx_runs_case_time ON tool_runs(case_id, started_at_utc);
CREATE INDEX idx_artifacts_case_type ON artifacts(case_id, artifact_type);
CREATE INDEX idx_timeline_case_utc ON timeline_events(case_id, normalized_utc);
CREATE INDEX idx_statements_case_state ON statements(case_id, state);
CREATE INDEX idx_audit_case_sequence ON audit_events(case_id, sequence);

