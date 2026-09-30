from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable

from .canonical import canonical_bytes
from .checkpoints import create_checkpoint
from .config import LabConfig
from .database import CaseDatabase, create_case, create_working_copy, register_evidence, verify_evidence
from .errors import NexusError
from .migration import migrate_legacy, preview_legacy
from .operations import (
    add_artifact,
    add_finding,
    add_timeline_event,
    approve_method,
    export_manifest,
    finish_run,
    require_approval,
    start_run,
)
from .paths import ensure_distinct_roots
from .reporting import create_report


def read_request() -> dict[str, Any]:
    text = sys.stdin.read()
    return json.loads(text) if text.strip() else {}


def write_response(value: Any) -> None:
    sys.stdout.buffer.write(canonical_bytes({"ok": True, "result": value}) + b"\n")


def initialize_config(request: dict[str, Any]) -> dict[str, Any]:
    repository = Path(request["repository_root"]).resolve(strict=True)
    evidence = Path(request["evidence_root"]).resolve(strict=False)
    cases = Path(request["case_root"]).resolve(strict=False)
    tools = Path(request["tool_root"]).resolve(strict=False)
    ensure_distinct_roots(repository, evidence, cases, tools)
    if not request.get("create_roots", False):
        missing = [str(path) for path in (evidence, cases, tools) if not path.is_dir()]
        if missing:
            raise NexusError(f"Configured roots do not exist: {', '.join(missing)}")
    else:
        for path in (evidence, cases, tools):
            path.mkdir(parents=True, exist_ok=True)
    output = Path(request["config_path"]).resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite configuration: {output}")
    if not output.parent.is_dir():
        raise NexusError(f"Configuration parent does not exist: {output.parent}")
    payload = {
        "schema": "nexus-lab/config/v2",
        "repository_root": str(repository),
        "evidence_root": str(evidence.resolve(strict=True)),
        "case_root": str(cases.resolve(strict=True)),
        "tool_root": str(tools.resolve(strict=True)),
        "python_executable": request.get("python_executable", sys.executable),
    }
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
        stream.write("\n")
    return {"config_path": str(output), **payload}


def get_case(config: LabConfig, request: dict[str, Any]) -> dict[str, Any]:
    database = CaseDatabase(config, request["case_id"])
    connection = database.connect()
    try:
        row = connection.execute("SELECT * FROM cases WHERE case_id=?", (request["case_id"],)).fetchone()
        if not row:
            raise NexusError("Case not found")
        return dict(row)
    finally:
        connection.close()


def get_run(config: LabConfig, request: dict[str, Any]) -> dict[str, Any]:
    database = CaseDatabase(config, request["case_id"])
    connection = database.connect()
    try:
        row = connection.execute("SELECT * FROM tool_runs WHERE case_id=? AND tool_run_id=?", (request["case_id"], request["tool_run_id"])).fetchone()
        if not row:
            raise NexusError("Tool run not found")
        result = dict(row)
        result["inputs"] = [dict(value) for value in connection.execute("SELECT * FROM run_inputs WHERE tool_run_id=?", (request["tool_run_id"],))]
        result["outputs"] = [dict(value) for value in connection.execute("""SELECT gf.* FROM generated_files gf JOIN run_outputs ro ON ro.output_id=gf.generated_file_id WHERE ro.tool_run_id=?""", (request["tool_run_id"],))]
        return result
    finally:
        connection.close()


def dispatch(action: str, config: LabConfig | None, request: dict[str, Any]) -> Any:
    if action == "initialize-config":
        return initialize_config(request)
    if action == "migration-preview":
        return preview_legacy(request["legacy_database"], request.get("legacy_registry"))
    if config is None:
        raise NexusError("--config is required for this action")
    schema_path = config.repository_root / "schemas" / "case-v2.sql"
    actions: dict[str, Callable[[], Any]] = {
        "new-case": lambda: create_case(config, schema_path, **request),
        "get-case": lambda: get_case(config, request),
        "register-evidence": lambda: register_evidence(config, **request),
        "verify-evidence": lambda: verify_evidence(config, **request),
        "new-working-copy": lambda: create_working_copy(config, **request),
        "approve-method": lambda: approve_method(config, **request),
        "check-approval": lambda: require_approval(config, **request),
        "run-start": lambda: start_run(config, **request),
        "run-finish": lambda: finish_run(config, **request),
        "get-run": lambda: get_run(config, request),
        "add-artifact": lambda: add_artifact(config, request),
        "add-finding": lambda: add_finding(config, request),
        "add-timeline-event": lambda: add_timeline_event(config, request),
        "new-report": lambda: create_report(config, **request),
        "export-manifest": lambda: export_manifest(config, **request),
        "verify-ledger": lambda: CaseDatabase(config, request["case_id"]).verify_ledger(),
        "new-checkpoint": lambda: create_checkpoint(config, **request),
        "migration-run": lambda: migrate_legacy(config, schema_path=str(schema_path), **request),
    }
    if action not in actions:
        raise NexusError(f"Unknown action: {action}")
    return actions[action]()


def main() -> int:
    parser = argparse.ArgumentParser(description="Nexus-Lab v2 transactional core")
    parser.add_argument("action")
    parser.add_argument("--config")
    args = parser.parse_args()
    try:
        request = read_request()
        config = LabConfig.load(args.config) if args.config else None
        write_response(dispatch(args.action, config, request))
        return 0
    except (NexusError, FileExistsError, FileNotFoundError, KeyError, ValueError, OSError, sqlite3.Error, json.JSONDecodeError) as error:
        payload = {"ok": False, "error": {"type": type(error).__name__, "message": str(error)}}
        sys.stderr.buffer.write(canonical_bytes(payload) + b"\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

