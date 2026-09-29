PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

ALTER TABLE tool_runs ADD COLUMN purpose TEXT;
ALTER TABLE tool_runs ADD COLUMN parameter_explanation TEXT;
ALTER TABLE tool_runs ADD COLUMN output_summary TEXT;

UPDATE tool_runs
SET purpose = 'not determined: record predates migration 0002'
WHERE purpose IS NULL OR length(trim(purpose)) = 0;

UPDATE tool_runs
SET parameter_explanation = 'not determined: record predates migration 0002'
WHERE parameter_explanation IS NULL OR length(trim(parameter_explanation)) = 0;

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

COMMIT;
