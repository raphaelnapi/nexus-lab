from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, canonical_hash
from .config import LabConfig
from .database import CaseDatabase, new_id, utc_now
from .errors import AuthorizationError, IntegrityError, NexusError
from .hashing import hash_file, safe_relative
from .paths import reject_alternate_data_stream, reject_hardlink, reject_reparse_components, require_within, resolved


def load_method(config: LabConfig, method_id: str) -> tuple[Path, dict[str, Any], str]:
    path = config.repository_root / "methods" / f"{method_id}.json"
    path = resolved(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "nexus-lab/method-pack/v2" or data.get("method_id") != method_id:
        raise NexusError(f"Invalid method pack: {path}")
    required = {"version", "purpose", "question", "capability_id", "execution", "authorization", "validation", "limitations"}
    missing = sorted(required.difference(data))
    if missing:
        raise NexusError(f"Method pack is missing required fields: {', '.join(missing)}")
    execution_required = {"backend", "timeout_seconds", "allowed_exit_codes", "input_zones", "output_zones", "argument_patterns"}
    missing_execution = sorted(execution_required.difference(data["execution"]))
    if missing_execution:
        raise NexusError(f"Method execution is missing fields: {', '.join(missing_execution)}")
    return path, data, hashlib.sha256(path.read_bytes()).hexdigest()


def register_method(connection: sqlite3.Connection, method: dict[str, Any], digest: str) -> None:
    connection.execute(
        """INSERT INTO method_versions(
            method_id,version,definition_sha256,capability_id,purpose,
            validation_reference,limitations,definition_json
        ) VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(method_id,version) DO UPDATE SET
            definition_sha256=excluded.definition_sha256,
            capability_id=excluded.capability_id,
            purpose=excluded.purpose,
            validation_reference=excluded.validation_reference,
            limitations=excluded.limitations,
            definition_json=excluded.definition_json""",
        (
            method["method_id"], method["version"], digest, method["capability_id"],
            method["purpose"], canonical_bytes(method["validation"]).decode("utf-8"),
            canonical_bytes(method["limitations"]).decode("utf-8"),
            canonical_bytes(method).decode("utf-8"),
        ),
    )


def approve_method(
    config: LabConfig,
    *,
    case_id: str,
    method_id: str,
    approved_by: str,
    expires_at_utc: str,
    parameter_bounds: dict[str, Any],
) -> dict[str, Any]:
    _, method, method_hash = load_method(config, method_id)
    expires = datetime.fromisoformat(expires_at_utc.replace("Z", "+00:00"))
    if expires.tzinfo is None or expires.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise AuthorizationError("Approval expiry must be a future timezone-aware timestamp")
    approval_id = new_id("APR")
    database = CaseDatabase(config, case_id)
    with database.transaction() as connection:
        register_method(connection, method, method_hash)
        bounds_json = canonical_bytes(parameter_bounds).decode("utf-8")
        connection.execute(
            """INSERT INTO approvals(
                approval_id,case_id,method_id,method_version,method_sha256,
                approved_by,approved_at_utc,expires_at_utc,parameter_bounds_json,
                parameter_bounds_sha256
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                approval_id, case_id, method_id, method["version"], method_hash,
                approved_by, utc_now(), expires_at_utc, bounds_json,
                canonical_hash(parameter_bounds),
            ),
        )
        database.append_audit(
            connection, actor=approved_by, action="method-approved",
            entity_type="approval", entity_id=approval_id,
            payload={"method_id": method_id, "method_version": method["version"], "method_sha256": method_hash, "expires_at_utc": expires_at_utc, "parameter_bounds": parameter_bounds},
        )
    return {"approval_id": approval_id, "method_id": method_id, "method_sha256": method_hash, "expires_at_utc": expires_at_utc}


def require_approval(
    config: LabConfig,
    *,
    case_id: str,
    approval_id: str,
    method_id: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    _, method, current_hash = load_method(config, method_id)
    database = CaseDatabase(config, case_id)
    connection = database.connect()
    try:
        row = connection.execute(
            "SELECT * FROM approvals WHERE case_id=? AND approval_id=? AND method_id=?",
            (case_id, approval_id, method_id),
        ).fetchone()
        if not row or row["status"] != "active":
            raise AuthorizationError("No active approval matches the requested method")
        if row["method_sha256"] != current_hash or row["method_version"] != method["version"]:
            raise AuthorizationError("Method definition changed after approval")
        expiry = datetime.fromisoformat(row["expires_at_utc"].replace("Z", "+00:00"))
        if expiry <= datetime.now(timezone.utc):
            raise AuthorizationError("Method approval expired")
        bounds = json.loads(row["parameter_bounds_json"])
        if set(parameters) != set(bounds):
            raise AuthorizationError("Requested parameter names differ from the approved bounds")
        for key, expected in bounds.items():
            if key not in parameters:
                raise AuthorizationError(f"Approved parameter is missing: {key}")
            actual = parameters[key]
            if isinstance(expected, list) and actual not in expected:
                raise AuthorizationError(f"Parameter outside approved set: {key}")
            if not isinstance(expected, list) and actual != expected:
                raise AuthorizationError(f"Parameter differs from approval: {key}")
        return dict(row)
    finally:
        connection.close()


def start_run(
    config: LabConfig,
    *,
    case_id: str,
    approval_id: str,
    method_id: str,
    parameters: dict[str, Any],
    command: list[str],
    purpose: str,
    parameter_explanation: str,
    operator: str,
    inputs: list[dict[str, Any]],
    planned_outputs: list[str],
    tool: dict[str, Any],
    environment: dict[str, Any],
    retry_of: str | None = None,
) -> dict[str, Any]:
    approval = require_approval(
        config, case_id=case_id, approval_id=approval_id,
        method_id=method_id, parameters=parameters,
    )
    database = CaseDatabase(config, case_id)
    _, method, _ = load_method(config, method_id)
    executable = require_within(tool["executable_path"], config.tool_root)
    tool_required = {"provider_id", "tool_name", "version", "binary_sha256", "signature_status", "validated_at_utc", "validation_reference"}
    missing_tool = sorted(name for name in tool_required if not tool.get(name))
    if missing_tool:
        raise NexusError(f"Validated tool record is incomplete: {', '.join(missing_tool)}")
    if tool["signature_status"] not in {"valid", "unsigned-reviewed", "not-applicable"}:
        raise NexusError("Unsupported tool signature status")
    reject_alternate_data_stream(Path(tool["executable_path"]))
    reject_reparse_components(Path(tool["executable_path"]).absolute(), config.tool_root)
    if not command or resolved(command[0]) != executable:
        raise IntegrityError("Recorded command executable differs from the validated tool")
    for argument in command[1:]:
        if not any(re.fullmatch(pattern, argument) for pattern in method["execution"]["argument_patterns"]):
            raise AuthorizationError(f"Command argument is outside the method pack: {argument}")
    catalog = json.loads((config.repository_root / "tools" / "catalog.json").read_text(encoding="utf-8"))
    capability = next((item for item in catalog["capabilities"] if item["id"] == method["capability_id"]), None)
    if not capability or tool["provider_id"] not in {item["id"] for item in capability["providers"]}:
        raise AuthorizationError("Tool provider is not cataloged for the method capability")
    actual_binary = hash_file(executable).sha256
    if actual_binary != tool["binary_sha256"]:
        raise IntegrityError("Tool binary hash does not match the validated tool manifest")
    allowed_input_roots = {
        "working-copies": database.case_dir / "working-copies",
        "derived": database.case_dir / "derived",
    }
    normalized_inputs: list[dict[str, Any]] = []
    verify_connection = database.connect()
    try:
        for item in inputs:
            if item["entity_type"] == "working-copy":
                record = verify_connection.execute("SELECT relative_path,sha256 FROM working_copies WHERE case_id=? AND working_copy_id=?", (case_id, item["entity_id"])).fetchone()
            elif item["entity_type"] == "generated-file":
                record = verify_connection.execute("SELECT relative_path,sha256 FROM generated_files WHERE case_id=? AND generated_file_id=?", (case_id, item["entity_id"])).fetchone()
            else:
                raise NexusError("Executable run inputs must be registered working copies or generated files")
            if not record:
                raise NexusError(f"Registered run input was not found: {item['entity_id']}")
            path = (database.case_dir / record["relative_path"]).resolve(strict=True)
            zone_ok = any(
                path != root and path.is_relative_to(root)
                for name, root in allowed_input_roots.items()
                if name in method["execution"]["input_zones"]
            )
            if not zone_ok:
                raise NexusError(f"Input is outside method zones: {path}")
            digest = hash_file(path)
            if digest.sha256 != record["sha256"] or (item.get("sha256") and digest.sha256 != item["sha256"]):
                raise IntegrityError(f"Run input hash mismatch: {item['entity_id']}")
            normalized_inputs.append({"input_id": item["input_id"], "entity_type": item["entity_type"], "entity_id": item["entity_id"], "relative_path": record["relative_path"], "sha256": digest.sha256})
    finally:
        verify_connection.close()
    zone_paths = {
        "staging": database.case_dir / "staging",
        "extracted": database.case_dir / "derived" / "extracted",
        "analysis": database.case_dir / "derived" / "analysis",
        "timelines": database.case_dir / "derived" / "timelines",
        "reports": database.case_dir / "derived" / "reports",
        "exports": database.case_dir / "derived" / "exports",
    }
    for value in planned_outputs:
        candidate = Path(value).resolve(strict=False)
        reject_alternate_data_stream(Path(value))
        reject_reparse_components(Path(value).absolute().parent, database.case_dir)
        if not any((candidate != zone_paths[name] and candidate.is_relative_to(zone_paths[name])) for name in method["execution"]["output_zones"]):
            raise NexusError(f"Planned output is outside method zones: {candidate}")
    run_id = new_id("RUN")
    tool_version_id = f"TOOL-{actual_binary[:24]}"
    environment_id = new_id("ENV")
    with database.transaction() as connection:
        environment_json = canonical_bytes(environment).decode("utf-8")
        connection.execute(
            "INSERT INTO environments(environment_id,case_id,environment_type,captured_at_utc,details_json,details_sha256) VALUES(?,?,?,?,?,?)",
            (environment_id, case_id, "windows-host", utc_now(), environment_json, canonical_hash(environment)),
        )
        connection.execute(
            """INSERT OR IGNORE INTO tool_versions(
                tool_version_id,capability_id,provider_id,tool_name,version,
                executable_path,binary_sha256,signature_status,validated_at_utc,
                validation_reference
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (tool_version_id, method["capability_id"], tool["provider_id"], tool["tool_name"], tool["version"], str(executable), actual_binary, tool["signature_status"], tool["validated_at_utc"], tool["validation_reference"]),
        )
        connection.execute(
            """INSERT INTO tool_runs(
                tool_run_id,case_id,approval_id,method_id,method_version,purpose,
                command_json,parameter_explanation,operator,started_at_utc,status,retry_of
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, case_id, approval_id, method_id, approval["method_version"],
                purpose, canonical_bytes(command).decode("utf-8"),
                parameter_explanation, operator, utc_now(), "started", retry_of,
            ),
        )
        connection.execute("UPDATE tool_runs SET tool_version_id=? WHERE tool_run_id=?", (tool_version_id, run_id))
        connection.execute("UPDATE tool_runs SET environment_id=? WHERE tool_run_id=?", (environment_id, run_id))
        for item in normalized_inputs:
            connection.execute(
                """INSERT INTO run_inputs(
                    tool_run_id,input_id,entity_type,entity_id,relative_path,sha256
                ) VALUES(?,?,?,?,?,?)""",
                (run_id, item["input_id"], item["entity_type"], item["entity_id"], item.get("relative_path"), item["sha256"]),
            )
        database.append_audit(
            connection, actor=operator, action="tool-run-started",
            entity_type="tool-run", entity_id=run_id,
            payload={"approval_id": approval_id, "method_id": method_id, "command": command, "inputs": normalized_inputs, "planned_outputs": planned_outputs, "tool_sha256": actual_binary, "environment_id": environment_id},
        )
    return {"tool_run_id": run_id, "started_at_utc": utc_now()}


def finish_run(
    config: LabConfig,
    *,
    case_id: str,
    tool_run_id: str,
    status: str,
    exit_status: int | None,
    stdout_path: str | None,
    stderr_path: str | None,
    output_paths: list[str],
    output_summary: str,
    limitations: str | None,
    operator: str,
) -> dict[str, Any]:
    allowed_status = {"succeeded", "failed", "timed-out", "cancelled"}
    if status not in allowed_status:
        raise NexusError(f"Invalid terminal run status: {status}")
    database = CaseDatabase(config, case_id)
    outputs: list[dict[str, Any]] = []
    for value in output_paths:
        path = require_within(value, database.case_dir)
        if not path.is_file():
            continue
        reject_alternate_data_stream(path)
        reject_reparse_components(Path(value).absolute(), database.case_dir)
        reject_hardlink(path)
        digest = hash_file(path)
        outputs.append({"path": path, "relative_path": safe_relative(path, database.case_dir), "digest": digest})
    lookup = database.connect()
    try:
        run_row = lookup.execute("SELECT method_id FROM tool_runs WHERE case_id=? AND tool_run_id=?", (case_id, tool_run_id)).fetchone()
        if not run_row:
            raise NexusError("Tool run not found")
        run_method_id = run_row["method_id"]
    finally:
        lookup.close()
    _, method, _ = load_method(config, run_method_id)
    allowed_output_roots = {
        "staging": database.case_dir / "staging", "extracted": database.case_dir / "derived" / "extracted",
        "analysis": database.case_dir / "derived" / "analysis", "timelines": database.case_dir / "derived" / "timelines",
        "reports": database.case_dir / "derived" / "reports", "exports": database.case_dir / "derived" / "exports",
    }
    for output in outputs:
        if not any(output["path"].is_relative_to(allowed_output_roots[name]) for name in method["execution"]["output_zones"]):
            raise NexusError(f"Generated output is outside method zones: {output['path']}")
    with database.transaction() as connection:
        row = connection.execute(
            "SELECT status FROM tool_runs WHERE case_id=? AND tool_run_id=?",
            (case_id, tool_run_id),
        ).fetchone()
        if not row or row["status"] != "started":
            raise NexusError("Run is unknown or already terminal")
        stdout_relative = safe_relative(require_within(stdout_path, database.case_dir), database.case_dir) if stdout_path else None
        stderr_relative = safe_relative(require_within(stderr_path, database.case_dir), database.case_dir) if stderr_path else None
        connection.execute(
            """UPDATE tool_runs SET ended_at_utc=?,status=?,exit_status=?,
                stdout_relative_path=?,stderr_relative_path=?,output_summary=?,limitations=?
                WHERE tool_run_id=?""",
            (utc_now(), status, exit_status, stdout_relative, stderr_relative, output_summary, limitations, tool_run_id),
        )
        for output in outputs:
            generated_id = new_id("FILE")
            digest = output["digest"]
            connection.execute(
                """INSERT INTO generated_files(
                    generated_file_id,case_id,tool_run_id,relative_path,purpose,
                    sha256,sha512,size_bytes,created_at_utc
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (generated_id, case_id, tool_run_id, output["relative_path"], output_summary, digest.sha256, digest.sha512, digest.size_bytes, utc_now()),
            )
            connection.execute("INSERT INTO run_outputs(tool_run_id,output_id) VALUES(?,?)", (tool_run_id, generated_id))
        database.append_audit(
            connection, actor=operator, action="tool-run-finished",
            entity_type="tool-run", entity_id=tool_run_id,
            payload={"status": status, "exit_status": exit_status, "outputs": [{"relative_path": value["relative_path"], "sha256": value["digest"].sha256} for value in outputs], "summary": output_summary},
        )
    return {"tool_run_id": tool_run_id, "status": status, "outputs": len(outputs)}


def add_artifact(config: LabConfig, payload: dict[str, Any]) -> dict[str, Any]:
    database = CaseDatabase(config, payload["case_id"])
    artifact_id = payload.get("artifact_id") or new_id("ART")
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO artifacts(
                artifact_id,case_id,evidence_id,working_copy_id,tool_run_id,
                artifact_type,source_locator,attributes_json,created_at_utc
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (artifact_id, payload["case_id"], payload.get("evidence_id"), payload.get("working_copy_id"), payload.get("tool_run_id"), payload["artifact_type"], payload["source_locator"], canonical_bytes(payload.get("attributes", {})).decode("utf-8"), utc_now()),
        )
        for target_type, target_id, relationship in (
            ("evidence", payload.get("evidence_id"), "sourced-from"),
            ("working-copy", payload.get("working_copy_id"), "parsed-from"),
            ("tool-run", payload.get("tool_run_id"), "produced-by"),
        ):
            if target_id:
                connection.execute(
                    "INSERT INTO provenance_edges(edge_id,case_id,source_type,source_id,relationship,target_type,target_id,created_at_utc) VALUES(?,?,?,?,?,?,?,?)",
                    (new_id("EDGE"), payload["case_id"], "artifact", artifact_id, relationship, target_type, target_id, utc_now()),
                )
        database.append_audit(connection, actor=payload["operator"], action="artifact-added", entity_type="artifact", entity_id=artifact_id, payload={"artifact_type": payload["artifact_type"], "source_locator": payload["source_locator"]})
    return {"artifact_id": artifact_id}


def add_timeline_event(config: LabConfig, payload: dict[str, Any]) -> dict[str, Any]:
    database = CaseDatabase(config, payload["case_id"])
    event_id = payload.get("event_id") or new_id("EVT")
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO timeline_events(
                event_id,case_id,artifact_id,original_timestamp,timestamp_semantics,
                source_timezone,normalized_utc,resolution,uncertainty,description,
                interpretation_status
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (event_id, payload["case_id"], payload["artifact_id"], payload["original_timestamp"], payload["timestamp_semantics"], payload.get("source_timezone", "unknown"), payload.get("normalized_utc"), payload.get("resolution"), payload.get("uncertainty"), payload["description"], payload["interpretation_status"]),
        )
        database.append_audit(connection, actor=payload["operator"], action="timeline-event-added", entity_type="timeline-event", entity_id=event_id, payload={key: payload.get(key) for key in ("artifact_id", "original_timestamp", "source_timezone", "normalized_utc", "interpretation_status")})
    return {"event_id": event_id}


def add_finding(config: LabConfig, payload: dict[str, Any]) -> dict[str, Any]:
    database = CaseDatabase(config, payload["case_id"])
    finding_id = payload.get("finding_id") or new_id("FIND")
    statement_ids: list[str] = []
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO findings(finding_id,case_id,title,limitations,created_by,created_at_utc) VALUES(?,?,?,?,?,?)",
            (finding_id, payload["case_id"], payload["title"], payload.get("limitations"), payload["operator"], utc_now()),
        )
        for statement in payload["statements"]:
            statement_id = statement.get("statement_id") or new_id("STMT")
            statement_ids.append(statement_id)
            connection.execute(
                """INSERT INTO statements(
                    statement_id,case_id,state,text,source_locator,assumptions,
                    alternatives,confidence,created_by,created_at_utc
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (statement_id, payload["case_id"], statement["state"], statement["text"], statement.get("source_locator"), statement.get("assumptions"), statement.get("alternatives"), statement.get("confidence"), payload["operator"], utc_now()),
            )
            connection.execute(
                "INSERT INTO finding_support(finding_id,statement_id,relationship) VALUES(?,?,?)",
                (finding_id, statement_id, statement["relationship"]),
            )
            connection.execute(
                "INSERT INTO provenance_edges(edge_id,case_id,source_type,source_id,relationship,target_type,target_id,created_at_utc) VALUES(?,?,?,?,?,?,?,?)",
                (new_id("EDGE"), payload["case_id"], "finding", finding_id, statement["relationship"], "statement", statement_id, utc_now()),
            )
        database.append_audit(connection, actor=payload["operator"], action="finding-added", entity_type="finding", entity_id=finding_id, payload={"title": payload["title"], "statement_ids": statement_ids})
    return {"finding_id": finding_id, "statement_ids": statement_ids}


def export_manifest(config: LabConfig, *, case_id: str, operator: str) -> dict[str, Any]:
    database = CaseDatabase(config, case_id)
    ledger = database.verify_ledger()
    connection = database.connect()
    try:
        tables = ("evidence_items", "working_copies", "tool_runs", "artifacts", "timeline_events", "findings", "generated_files")
        counts = {table: connection.execute(f"SELECT count(*) FROM {table} WHERE case_id=?", (case_id,)).fetchone()[0] for table in tables}
        case = dict(connection.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone())
    finally:
        connection.close()
    manifest = {"schema": "nexus-lab/case-manifest/v2", "generated_at_utc": utc_now(), "generated_by": operator, "case": case, "counts": counts, "ledger": ledger}
    output = database.case_dir / "derived" / "exports" / f"{case_id}-manifest-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    output.write_bytes(canonical_bytes(manifest) + b"\n")
    digest = hash_file(output)
    return {"path": str(output), "sha256": digest.sha256, "manifest": manifest}
