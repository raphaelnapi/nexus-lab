from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "python"))

from nexus_lab.config import LabConfig  # noqa: E402
from nexus_lab.database import CaseDatabase, create_case, create_working_copy, register_evidence, verify_evidence  # noqa: E402
from nexus_lab.errors import AuthorizationError, BoundaryError, IntegrityError, NexusError  # noqa: E402
from nexus_lab.hashing import hash_file  # noqa: E402
from nexus_lab.operations import approve_method, finish_run, require_approval, start_run  # noqa: E402
from nexus_lab.reporting import create_report  # noqa: E402


class NexusCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.evidence = root / "evidence"
        self.cases = root / "cases"
        self.tools = root / "tools"
        for path in (self.evidence, self.cases, self.tools):
            path.mkdir()
        self.config_path = root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "schema": "nexus-lab/config/v2",
                    "repository_root": str(REPOSITORY),
                    "evidence_root": str(self.evidence),
                    "case_root": str(self.cases),
                    "tool_root": str(self.tools),
                    "python_executable": sys.executable,
                }
            ),
            encoding="utf-8",
        )
        self.config = LabConfig.load(self.config_path)
        self.case_id = "CASE-2026-9001"
        create_case(
            self.config,
            REPOSITORY / "schemas" / "case-v2.sql",
            case_id=self.case_id,
            authority="synthetic test authority",
            scope="synthetic fixtures only",
            question="Does the v2 core preserve its invariants?",
            examiner="test-operator",
        )

    def test_case_layout_schema_and_no_overwrite(self) -> None:
        database = CaseDatabase(self.config, self.case_id)
        self.assertTrue(database.path.is_file())
        for relative in ("working-copies", "derived/analysis", "ledger/checkpoints", "staging"):
            self.assertTrue((database.case_dir / relative).is_dir())
        connection = database.connect()
        try:
            version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
            self.assertEqual(version, 2)
        finally:
            connection.close()
        with self.assertRaises(FileExistsError):
            create_case(
                self.config, REPOSITORY / "schemas" / "case-v2.sql",
                case_id=self.case_id, authority="a", scope="s", question="q", examiner="e",
            )

    def test_evidence_is_read_only_and_working_copy_is_verified(self) -> None:
        source = self.evidence / "synthetic.bin"
        source.write_bytes(b"synthetic evidence; not case data\n")
        before = source.stat()
        registered = register_evidence(
            self.config, case_id=self.case_id, evidence_id="EVID-TEST-001",
            source_path=str(source), evidence_type="synthetic-file", operator="test-operator",
        )
        verified = verify_evidence(self.config, case_id=self.case_id, evidence_id="EVID-TEST-001")
        after = source.stat()
        self.assertTrue(verified["matches"])
        self.assertEqual((before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))
        with self.assertRaises(AuthorizationError):
            create_working_copy(
                self.config, case_id=self.case_id, evidence_id="EVID-TEST-001",
                working_copy_id="WC-TEST-001", operator="test-operator", authorization_reference="",
            )
        copied = create_working_copy(
            self.config, case_id=self.case_id, evidence_id="EVID-TEST-001",
            working_copy_id="WC-TEST-001", operator="test-operator",
            authorization_reference="AUTH-SYNTHETIC-001",
        )
        self.assertEqual(copied["sha256"], registered["sha256"])

    def test_ledger_detects_tampering(self) -> None:
        database = CaseDatabase(self.config, self.case_id)
        self.assertTrue(database.verify_ledger()["valid"])
        connection = database.connect()
        try:
            connection.execute("DROP TRIGGER audit_events_no_update")
            connection.execute("UPDATE audit_events SET payload_json='{}' WHERE sequence=1")
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(IntegrityError):
            database.verify_ledger()

    def test_approval_is_bound_to_parameters_and_method_hash(self) -> None:
        expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        approval = approve_method(
            self.config, case_id=self.case_id, method_id="exiftool-metadata",
            approved_by="reviewer", expires_at_utc=expiry,
            parameter_bounds={"profile": "metadata-only"},
        )
        row = require_approval(
            self.config, case_id=self.case_id, approval_id=approval["approval_id"],
            method_id="exiftool-metadata", parameters={"profile": "metadata-only"},
        )
        self.assertEqual(row["method_id"], "exiftool-metadata")
        with self.assertRaises(AuthorizationError):
            require_approval(
                self.config, case_id=self.case_id, approval_id=approval["approval_id"],
                method_id="exiftool-metadata", parameters={"profile": "expanded"},
            )

    def test_configuration_rejects_overlapping_roots(self) -> None:
        bad = Path(self.temporary.name) / "bad.json"
        bad.write_text(
            json.dumps(
                {
                    "schema": "nexus-lab/config/v2",
                    "repository_root": str(REPOSITORY),
                    "evidence_root": str(self.evidence),
                    "case_root": str(self.evidence),
                    "tool_root": str(self.tools),
                }
            ), encoding="utf-8",
        )
        with self.assertRaises(BoundaryError):
            LabConfig.load(bad)

    def test_run_requires_registered_input_validated_tool_and_output_zone(self) -> None:
        source = self.evidence / "run-input.bin"
        source.write_bytes(b"synthetic run input")
        register_evidence(
            self.config, case_id=self.case_id, evidence_id="EVID-RUN",
            source_path=str(source), evidence_type="synthetic-file", operator="operator",
        )
        copied = create_working_copy(
            self.config, case_id=self.case_id, evidence_id="EVID-RUN",
            working_copy_id="WC-RUN", operator="operator", authorization_reference="AUTH-COPY",
        )
        expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        approval = approve_method(
            self.config, case_id=self.case_id, method_id="exiftool-metadata",
            approved_by="reviewer", expires_at_utc=expiry, parameter_bounds={"profile": "metadata-only"},
        )
        executable = self.tools / "exiftool.exe"
        executable.write_bytes(b"synthetic executable fixture; never executed")
        binary = hash_file(executable)
        output = self.cases / self.case_id / "derived" / "analysis" / "metadata.json"
        started = start_run(
            self.config, case_id=self.case_id, approval_id=approval["approval_id"],
            method_id="exiftool-metadata", parameters={"profile": "metadata-only"},
            command=[str(executable), "-json"], purpose="Synthetic run lifecycle test",
            parameter_explanation="-json selects structured metadata",
            operator="operator", retry_of=None, planned_outputs=[str(output)],
            inputs=[{"input_id": "IN-1", "entity_type": "working-copy", "entity_id": "WC-RUN", "sha256": copied["sha256"]}],
            tool={"provider_id": "exiftool", "tool_name": "ExifTool", "version": "test", "executable_path": str(executable), "binary_sha256": binary.sha256, "signature_status": "not-applicable", "validated_at_utc": datetime.now(timezone.utc).isoformat(), "validation_reference": "synthetic fixture"},
            environment={"os": "synthetic", "timezone": "UTC"},
        )
        output.write_text("{}\n", encoding="utf-8")
        result = finish_run(
            self.config, case_id=self.case_id, tool_run_id=started["tool_run_id"],
            status="succeeded", exit_status=0, stdout_path=None, stderr_path=None,
            output_paths=[str(output)], output_summary="Synthetic output", limitations=None,
            operator="operator",
        )
        self.assertEqual(result["outputs"], 1)
        with self.assertRaises(NexusError):
            start_run(
                self.config, case_id=self.case_id, approval_id=approval["approval_id"],
                method_id="exiftool-metadata", parameters={"profile": "metadata-only"},
                command=[str(executable)], purpose="bad zone", parameter_explanation="test",
                operator="operator", retry_of=None, planned_outputs=[str(self.cases / self.case_id / "administrative" / "bad.txt")],
                inputs=[{"input_id": "IN-2", "entity_type": "working-copy", "entity_id": "WC-RUN", "sha256": copied["sha256"]}],
                tool={"provider_id": "exiftool", "tool_name": "ExifTool", "version": "test", "executable_path": str(executable), "binary_sha256": binary.sha256, "signature_status": "not-applicable", "validated_at_utc": datetime.now(timezone.utc).isoformat(), "validation_reference": "synthetic fixture"},
                environment={"os": "synthetic", "timezone": "UTC"},
            )

    def test_reports_are_versioned_and_never_overwritten(self) -> None:
        first = create_report(self.config, case_id=self.case_id, operator="reporter")
        second = create_report(self.config, case_id=self.case_id, operator="reporter")
        self.assertEqual((first["version"], second["version"]), (1, 2))
        self.assertNotEqual(first["path"], second["path"])
        self.assertTrue(Path(first["path"]).is_file())
        self.assertTrue(Path(second["path"]).is_file())


if __name__ == "__main__":
    unittest.main()

