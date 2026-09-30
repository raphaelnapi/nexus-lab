from __future__ import annotations

from datetime import datetime, timezone

from .canonical import canonical_bytes
from .config import LabConfig
from .database import CaseDatabase, new_id, utc_now
from .hashing import hash_file


def create_checkpoint(config: LabConfig, *, case_id: str, operator: str) -> dict[str, object]:
    database = CaseDatabase(config, case_id)
    ledger = database.verify_ledger()
    checkpoint_id = new_id("CHK")
    payload = {
        "schema": "nexus-lab/ledger-checkpoint/v2",
        "checkpoint_id": checkpoint_id,
        "case_id": case_id,
        "created_at_utc": utc_now(),
        "created_by": operator,
        "last_event_hash": ledger["last_event_hash"],
        "event_count": ledger["events"],
        "signature_status": "unsigned",
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = database.case_dir / "ledger" / "checkpoints" / f"{stamp}-{checkpoint_id}.json"
    path.write_bytes(canonical_bytes(payload) + b"\n")
    checkpoint_hash = hash_file(path)
    with database.transaction() as connection:
        last_sequence = connection.execute("SELECT COALESCE(MAX(sequence),0) FROM audit_events WHERE case_id=?", (case_id,)).fetchone()[0]
        connection.execute(
            """INSERT INTO ledger_checkpoints(
                checkpoint_id,case_id,last_sequence,last_event_hash,database_sha256,
                signature_status,created_at_utc,created_by
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (checkpoint_id, case_id, last_sequence, ledger["last_event_hash"] or "", None, "unsigned", payload["created_at_utc"], operator),
        )
        database.append_audit(connection, actor=operator, action="checkpoint-created", entity_type="checkpoint", entity_id=checkpoint_id, payload={"checkpoint_sha256": checkpoint_hash.sha256, "covered_event_hash": ledger["last_event_hash"]})
    return {"checkpoint_id": checkpoint_id, "path": str(path), "sha256": checkpoint_hash.sha256, "signature_status": "unsigned"}
