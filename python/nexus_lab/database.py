from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .canonical import canonical_hash, canonical_bytes
from .config import LabConfig, validate_case_id
from .errors import AuthorizationError, IntegrityError, NexusError
from .hashing import hash_file, safe_relative
from .paths import reject_alternate_data_stream, reject_reparse_components, require_within, resolved


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


CASE_DIRECTORIES = (
    "administrative",
    "registry",
    "working-copies",
    "derived/extracted",
    "derived/analysis",
    "derived/timelines",
    "derived/reports",
    "derived/exports",
    "logs/tool-runs",
    "ledger/checkpoints",
    "staging",
)


class CaseDatabase:
    def __init__(self, config: LabConfig, case_id: str):
        validate_case_id(case_id)
        self.config = config
        self.case_id = case_id
        self.case_dir = config.case_dir(case_id)
        self.path = self.case_dir / "registry" / "case.sqlite3"

    def connect(self) -> sqlite3.Connection:
        if not self.path.is_file():
            raise NexusError(f"Case database does not exist: {self.path}")
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA trusted_schema = OFF")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def append_audit(
        self,
        connection: sqlite3.Connection,
        *,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
    ) -> str:
        previous = connection.execute(
            "SELECT event_hash FROM audit_events WHERE case_id=? ORDER BY sequence DESC LIMIT 1",
            (self.case_id,),
        ).fetchone()
        previous_hash = previous[0] if previous else None
        event_id = new_id("AUD")
        event_at = utc_now()
        payload_json = canonical_bytes(payload).decode("utf-8")
        event_hash = canonical_hash(
            {
                "event_id": event_id,
                "case_id": self.case_id,
                "event_at_utc": event_at,
                "actor": actor,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "payload": payload,
                "previous_hash": previous_hash,
            }
        )
        connection.execute(
            """INSERT INTO audit_events(
                event_id, case_id, event_at_utc, actor, action, entity_type,
                entity_id, payload_json, previous_hash, event_hash
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                event_id,
                self.case_id,
                event_at,
                actor,
                action,
                entity_type,
                entity_id,
                payload_json,
                previous_hash,
                event_hash,
            ),
        )
        return event_hash

    def verify_ledger(self) -> dict[str, Any]:
        connection = self.connect()
        try:
            previous_hash = None
            count = 0
            for row in connection.execute(
                "SELECT * FROM audit_events WHERE case_id=? ORDER BY sequence", (self.case_id,)
            ):
                payload = json.loads(row["payload_json"])
                expected = canonical_hash(
                    {
                        "event_id": row["event_id"],
                        "case_id": row["case_id"],
                        "event_at_utc": row["event_at_utc"],
                        "actor": row["actor"],
                        "action": row["action"],
                        "entity_type": row["entity_type"],
                        "entity_id": row["entity_id"],
                        "payload": payload,
                        "previous_hash": previous_hash,
                    }
                )
                if row["previous_hash"] != previous_hash or row["event_hash"] != expected:
                    raise IntegrityError(f"Audit ledger mismatch at sequence {row['sequence']}")
                previous_hash = row["event_hash"]
                count += 1
            return {"valid": True, "events": count, "last_event_hash": previous_hash}
        finally:
            connection.close()


def create_case(
    config: LabConfig,
    schema_path: Path,
    *,
    case_id: str,
    authority: str,
    scope: str,
    question: str,
    examiner: str,
    title: str | None = None,
) -> dict[str, Any]:
    validate_case_id(case_id)
    case_dir = config.case_dir(case_id)
    if case_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing case: {case_dir}")
    schema_path = resolved(schema_path)
    schema_text = schema_path.read_text(encoding="utf-8")
    try:
        for relative in CASE_DIRECTORIES:
            target = case_dir / relative
            target.mkdir(parents=True, exist_ok=False)
        database_path = case_dir / "registry" / "case.sqlite3"
        connection = sqlite3.connect(database_path)
        try:
            connection.executescript(schema_text)
            now = utc_now()
            import hashlib
            schema_hash = hashlib.sha256(schema_text.encode("utf-8")).hexdigest()
            connection.execute(
                "INSERT INTO schema_version(version, applied_at_utc, migration_hash) VALUES(2,?,?)",
                (now, schema_hash),
            )
            connection.execute(
                """INSERT INTO cases(
                    case_id,title,authority,scope,question,lead_examiner,opened_at_utc
                ) VALUES(?,?,?,?,?,?,?)""",
                (case_id, title, authority, scope, question, examiner, now),
            )
            database = CaseDatabase(config, case_id)
            database.append_audit(
                connection,
                actor=examiner,
                action="case-created",
                entity_type="case",
                entity_id=case_id,
                payload={"schema_version": 2, "schema_sha256": schema_hash},
            )
            connection.commit()
        finally:
            connection.close()
    except Exception as error:
        # Preserve the failed initialization for review; never silently remove a
        # case directory once creation has begun.
        marker_parent = case_dir / "administrative"
        marker_parent.mkdir(parents=True, exist_ok=True)
        marker = marker_parent / "INITIALIZATION_FAILED.txt"
        if not marker.exists():
            marker.write_text(f"{utc_now()}\n{type(error).__name__}: {error}\n", encoding="utf-8")
        raise
    return {"case_id": case_id, "case_dir": str(case_dir), "database": str(database_path)}


def register_evidence(
    config: LabConfig,
    *,
    case_id: str,
    evidence_id: str,
    source_path: str,
    evidence_type: str,
    operator: str,
    description: str | None = None,
    write_protection: str = "reported",
) -> dict[str, Any]:
    source_literal = Path(source_path).expanduser().absolute()
    reject_alternate_data_stream(source_literal)
    reject_reparse_components(source_literal, config.evidence_root)
    source = require_within(source_literal, config.evidence_root)
    if not source.is_file():
        raise NexusError("Evidence source must be a regular file")
    digest = hash_file(source)
    database = CaseDatabase(config, case_id)
    now = utc_now()
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO evidence_items(
                evidence_id,case_id,logical_name,evidence_type,sensitive_locator,
                description,size_bytes,sha256,sha512,source_mtime_ns,
                registered_at_utc,registered_by,verified_at_utc,write_protection
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                evidence_id,
                case_id,
                source.name,
                evidence_type,
                str(source),
                description,
                digest.size_bytes,
                digest.sha256,
                digest.sha512,
                digest.mtime_ns,
                now,
                operator,
                now,
                write_protection,
            ),
        )
        custody_id = new_id("CUST")
        connection.execute(
            """INSERT INTO custody_events(
                custody_event_id,case_id,evidence_id,event_at_utc,actor,action,
                source_location,purpose
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (custody_id, case_id, evidence_id, now, operator, "registered", str(source), "Evidence intake and integrity registration"),
        )
        database.append_audit(
            connection,
            actor=operator,
            action="evidence-registered",
            entity_type="evidence",
            entity_id=evidence_id,
            payload={"size_bytes": digest.size_bytes, "sha256": digest.sha256, "sha512": digest.sha512},
        )
    return {"evidence_id": evidence_id, **digest.__dict__}


def verify_evidence(config: LabConfig, *, case_id: str, evidence_id: str) -> dict[str, Any]:
    database = CaseDatabase(config, case_id)
    connection = database.connect()
    try:
        row = connection.execute(
            "SELECT * FROM evidence_items WHERE case_id=? AND evidence_id=?",
            (case_id, evidence_id),
        ).fetchone()
        if not row:
            raise NexusError(f"Unknown evidence ID: {evidence_id}")
    finally:
        connection.close()
    source_literal = Path(row["sensitive_locator"]).absolute()
    reject_alternate_data_stream(source_literal)
    reject_reparse_components(source_literal, config.evidence_root)
    source = require_within(source_literal, config.evidence_root)
    digest = hash_file(source)
    matches = digest.sha256 == row["sha256"] and digest.sha512 == row["sha512"]
    if not matches:
        raise IntegrityError(f"Evidence hash mismatch: {evidence_id}")
    return {"evidence_id": evidence_id, "matches": True, **digest.__dict__}


def create_working_copy(
    config: LabConfig,
    *,
    case_id: str,
    evidence_id: str,
    working_copy_id: str,
    operator: str,
    authorization_reference: str,
) -> dict[str, Any]:
    if not authorization_reference.strip():
        raise AuthorizationError("A copy authorization reference is required")
    database = CaseDatabase(config, case_id)
    connection = database.connect()
    try:
        row = connection.execute(
            "SELECT * FROM evidence_items WHERE case_id=? AND evidence_id=?", (case_id, evidence_id)
        ).fetchone()
        if not row:
            raise NexusError(f"Unknown evidence ID: {evidence_id}")
    finally:
        connection.close()
    source_literal = Path(row["sensitive_locator"]).absolute()
    reject_alternate_data_stream(source_literal)
    reject_reparse_components(source_literal, config.evidence_root)
    source = require_within(source_literal, config.evidence_root)
    if hash_file(source).sha256 != row["sha256"]:
        raise IntegrityError("Evidence changed before copy")
    target = database.case_dir / "working-copies" / f"{working_copy_id}-{Path(row['logical_name']).name}"
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite working copy: {target}")
    with source.open("rb") as input_stream, target.open("xb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream, 4 * 1024 * 1024)
        output_stream.flush()
    digest = hash_file(target)
    if digest.sha256 != row["sha256"] or digest.sha512 != row["sha512"]:
        raise IntegrityError("Working-copy hash mismatch")
    now = utc_now()
    relative = safe_relative(target, database.case_dir)
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO working_copies(
                working_copy_id,case_id,evidence_id,relative_path,size_bytes,
                sha256,sha512,created_at_utc,created_by,verified_at_utc,copy_method
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                working_copy_id, case_id, evidence_id, relative, digest.size_bytes,
                digest.sha256, digest.sha512, now, operator, now,
                f"byte-copy; authorization={authorization_reference}",
            ),
        )
        database.append_audit(
            connection,
            actor=operator,
            action="working-copy-created",
            entity_type="working-copy",
            entity_id=working_copy_id,
            payload={"evidence_id": evidence_id, "relative_path": relative, "sha256": digest.sha256, "authorization_reference": authorization_reference},
        )
    return {"working_copy_id": working_copy_id, "relative_path": relative, **digest.__dict__}
