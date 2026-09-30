from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes
from .config import LabConfig
from .database import CaseDatabase, create_case, new_id, utc_now
from .errors import IntegrityError, NexusError
from .paths import resolved


LEGACY_TABLES = (
    "cases", "evidence_items", "custody_events", "working_copies", "methods",
    "tool_runs", "artifacts", "findings", "finding_artifacts", "generated_files",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def preview_legacy(legacy_database: str | Path, legacy_registry: str | Path | None = None) -> dict[str, Any]:
    database_path = resolved(legacy_database)
    uri = f"file:{database_path.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        existing = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {name: connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in LEGACY_TABLES if name in existing}
        cases = [dict(row) for row in connection.execute("SELECT * FROM cases")] if "cases" in existing else []
        evidence_gaps: list[dict[str, Any]] = []
        if "evidence_items" in existing:
            for row in connection.execute("SELECT evidence_id,source_path,size_bytes,sha256,sha512 FROM evidence_items"):
                missing = [field for field in ("source_path", "size_bytes", "sha256", "sha512") if row[field] in (None, "")]
                if missing:
                    evidence_gaps.append({"evidence_id": row["evidence_id"], "missing": missing})
    finally:
        connection.close()
    manifests = 0
    manifest_records: list[dict[str, Any]] = []
    manifest_gaps: list[dict[str, Any]] = []
    registry_path = resolved(legacy_registry) if legacy_registry else None
    if registry_path and registry_path.is_dir():
        import re
        for manifest_path in sorted(registry_path.glob("*.hash.json")):
            manifests += 1
            match = re.fullmatch(r"(EVID-[0-9]+)\.hash\.json", manifest_path.name)
            try:
                value = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                manifest_gaps.append({"manifest": manifest_path.name, "error": f"invalid JSON: {error}"})
                continue
            missing = [name for name in ("path", "size_bytes", "sha256", "sha512", "observed_at_utc") if value.get(name) in (None, "")]
            if value.get("schema") != "nexus-lab-evidence-hash/v1":
                missing.append("supported schema")
            if not match:
                missing.append("derived evidence ID in manifest filename")
            if missing:
                manifest_gaps.append({"manifest": manifest_path.name, "missing": missing})
                continue
            manifest_records.append(
                {
                    "evidence_id": match.group(1),
                    "id_state": "derived",
                    "id_derivation": "regex (EVID-[0-9]+) from registered manifest filename",
                    "manifest_path": str(manifest_path),
                    "manifest_sha256": file_sha256(manifest_path),
                    "source_path": value["path"],
                    "size_bytes": value["size_bytes"],
                    "mtime_ns": value.get("mtime_ns"),
                    "sha256": value["sha256"],
                    "sha512": value["sha512"],
                    "observed_at_utc": value["observed_at_utc"],
                    "tool": value.get("tool", {}),
                }
            )
    duplicate_manifest_ids = sorted({record["evidence_id"] for record in manifest_records if sum(item["evidence_id"] == record["evidence_id"] for item in manifest_records) > 1})
    if duplicate_manifest_ids:
        manifest_gaps.append({"duplicate_evidence_ids": duplicate_manifest_ids})
    database_ids: set[str] = set()
    if "evidence_items" in existing:
        check = sqlite3.connect(uri, uri=True)
        try:
            database_ids = {row[0] for row in check.execute("SELECT evidence_id FROM evidence_items")}
        finally:
            check.close()
    collisions = sorted(database_ids.intersection(record["evidence_id"] for record in manifest_records))
    if collisions:
        manifest_gaps.append({"database_manifest_id_collisions": collisions})
    all_gaps = evidence_gaps + manifest_gaps
    return {
        "schema": "nexus-lab/legacy-preview/v2",
        "source_database": str(database_path),
        "source_sha256": file_sha256(database_path),
        "counts": counts,
        "cases": cases,
        "hash_manifests": manifests,
        "manifest_records": manifest_records,
        "blocking_gaps": all_gaps,
        "migration_allowed": len(cases) == 1 and not all_gaps,
    }


def migrate_legacy(
    config: LabConfig,
    *,
    legacy_database: str,
    legacy_registry: str | None,
    schema_path: str,
    authority: str,
    scope: str,
    question: str,
    examiner: str,
) -> dict[str, Any]:
    preview = preview_legacy(legacy_database, legacy_registry)
    if not preview["migration_allowed"]:
        raise NexusError("Legacy preview contains blocking gaps or an ambiguous case identity")
    legacy_case = preview["cases"][0]
    case_id = legacy_case["case_id"]
    target = config.case_dir(case_id)
    if target.exists():
        raise FileExistsError(f"Migration target already exists: {target}")
    create_case(
        config, resolved(schema_path), case_id=case_id,
        authority=authority, scope=scope, question=question,
        examiner=examiner, title=legacy_case.get("title"),
    )
    source = resolved(legacy_database)
    source_connection = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    source_connection.row_factory = sqlite3.Row
    destination = CaseDatabase(config, case_id)
    imported = {"evidence_items": 0, "custody_events": 0}
    try:
        with destination.transaction() as connection:
            connection.execute("UPDATE cases SET legacy_source=? WHERE case_id=?", (str(source), case_id))
            parent_links: list[tuple[str, str]] = []
            for row in source_connection.execute("SELECT * FROM evidence_items ORDER BY evidence_id"):
                connection.execute(
                    """INSERT INTO evidence_items(
                        evidence_id,case_id,parent_evidence_id,logical_name,evidence_type,
                        sensitive_locator,description,size_bytes,sha256,sha512,
                        registered_at_utc,registered_by,verified_at_utc,write_protection,
                        metadata_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        row["evidence_id"], case_id, None,
                        Path(row["source_path"]).name, row["evidence_type"], row["source_path"],
                        row["description"], row["size_bytes"], row["sha256"], row["sha512"],
                        row["verified_at_utc"] or legacy_case["opened_at_utc"],
                        "legacy:not-determined", row["verified_at_utc"],
                        "observed" if row["write_protected"] else "not-determined",
                        row["metadata_json"] or "{}",
                    ),
                )
                if row["parent_evidence_id"]:
                    parent_links.append((row["parent_evidence_id"], row["evidence_id"]))
                imported["evidence_items"] += 1
            for parent_id, evidence_id in parent_links:
                connection.execute("UPDATE evidence_items SET parent_evidence_id=? WHERE evidence_id=?", (parent_id, evidence_id))
            for record in preview["manifest_records"]:
                metadata = {
                    "legacy_manifest": record["manifest_path"],
                    "legacy_manifest_sha256": record["manifest_sha256"],
                    "evidence_id_state": record["id_state"],
                    "evidence_id_derivation": record["id_derivation"],
                    "legacy_tool": record["tool"],
                }
                connection.execute(
                    """INSERT INTO evidence_items(
                        evidence_id,case_id,parent_evidence_id,logical_name,evidence_type,
                        sensitive_locator,description,size_bytes,sha256,sha512,source_mtime_ns,
                        registered_at_utc,registered_by,verified_at_utc,write_protection,
                        metadata_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        record["evidence_id"], case_id, None, Path(record["source_path"]).name,
                        "not-determined", record["source_path"],
                        "Imported from a v1 hash manifest; type not determined",
                        record["size_bytes"], record["sha256"], record["sha512"], record["mtime_ns"],
                        record["observed_at_utc"], "not-determined: v1 manifest has no operator",
                        record["observed_at_utc"], "not-determined",
                        canonical_bytes(metadata).decode("utf-8"),
                    ),
                )
                imported["evidence_items"] += 1
            for row in source_connection.execute("SELECT * FROM custody_events ORDER BY custody_event_id"):
                connection.execute(
                    """INSERT INTO custody_events(
                        custody_event_id,case_id,evidence_id,event_at_utc,actor,action,
                        source_location,destination_location,purpose,notes
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        f"LEGACY-CUST-{row['custody_event_id']}", case_id, row["evidence_id"],
                        row["event_at_utc"], row["actor"], row["action"], row["source_location"],
                        row["destination_location"], row["purpose"] or "not determined: legacy record",
                        row["notes"],
                    ),
                )
                imported["custody_events"] += 1
            migration_id = new_id("MIG")
            connection.execute(
                """INSERT INTO migration_records(
                    migration_id,case_id,source_path,source_sha256,preview_json,
                    migrated_at_utc,status
                ) VALUES(?,?,?,?,?,?,?)""",
                (migration_id, case_id, str(source), preview["source_sha256"], canonical_bytes(preview).decode("utf-8"), utc_now(), "completed"),
            )
            destination.append_audit(
                connection, actor=examiner, action="legacy-migrated",
                entity_type="migration", entity_id=migration_id,
                payload={"source_sha256": preview["source_sha256"], "imported": imported},
            )
    finally:
        source_connection.close()
    expected_evidence = preview["counts"].get("evidence_items", 0) + len(preview["manifest_records"])
    if expected_evidence != imported["evidence_items"]:
        raise IntegrityError("Migrated evidence count does not match preview")
    return {"case_id": case_id, "migration_id": migration_id, "imported": imported, "legacy_preserved": True}

