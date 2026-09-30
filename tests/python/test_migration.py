from __future__ import annotations

import sqlite3
import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "python"))

from nexus_lab.config import LabConfig  # noqa: E402
from nexus_lab.migration import migrate_legacy, preview_legacy  # noqa: E402


class LegacyMigrationTests(unittest.TestCase):
    def test_preview_is_read_only_and_reports_blocking_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "legacy.sqlite3"
            connection = sqlite3.connect(path)
            connection.executescript(
                """
                CREATE TABLE cases(case_id TEXT PRIMARY KEY, title TEXT, opened_at_utc TEXT);
                INSERT INTO cases VALUES('CASE-2026-9999','Synthetic','2026-01-01T00:00:00Z');
                CREATE TABLE evidence_items(
                    evidence_id TEXT, source_path TEXT, size_bytes INTEGER,
                    sha256 TEXT, sha512 TEXT
                );
                INSERT INTO evidence_items VALUES('EVID-1','X:/synthetic.bin',NULL,NULL,NULL);
                """
            )
            connection.commit()
            connection.close()
            before = path.read_bytes()
            preview = preview_legacy(path)
            self.assertFalse(preview["migration_allowed"])
            self.assertEqual(preview["blocking_gaps"][0]["evidence_id"], "EVID-1")
            self.assertEqual(path.read_bytes(), before)

    def test_preview_maps_v1_manifests_as_derived_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / "legacy.sqlite3"
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE cases(case_id TEXT PRIMARY KEY, title TEXT, opened_at_utc TEXT);
                INSERT INTO cases VALUES('CASE-2026-9998','Synthetic','2026-01-01T00:00:00Z');
                CREATE TABLE evidence_items(evidence_id TEXT, source_path TEXT, size_bytes INTEGER, sha256 TEXT, sha512 TEXT);
                """
            )
            connection.commit()
            connection.close()
            registry = root / "registry"
            registry.mkdir()
            content = b"synthetic"
            manifest = {
                "schema": "nexus-lab-evidence-hash/v1",
                "observed_at_utc": "2026-01-01T00:00:00Z",
                "tool": {"name": "synthetic", "version": "1", "python_version": "test"},
                "path": "X:/synthetic.bin",
                "size_bytes": len(content),
                "mtime_ns": 1,
                "sha256": hashlib.sha256(content).hexdigest(),
                "sha512": hashlib.sha512(content).hexdigest(),
            }
            (registry / "EVID-0042.hash.json").write_text(json.dumps(manifest), encoding="utf-8")
            preview = preview_legacy(database, registry)
            self.assertTrue(preview["migration_allowed"])
            self.assertEqual(preview["manifest_records"][0]["evidence_id"], "EVID-0042")
            self.assertEqual(preview["manifest_records"][0]["id_state"], "derived")

    def test_migration_creates_a_new_case_without_changing_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root, case_root, tool_root = root / "evidence", root / "cases", root / "tools"
            for item in (evidence_root, case_root, tool_root):
                item.mkdir()
            config_path = root / "config.json"
            config_path.write_text(json.dumps({
                "schema": "nexus-lab/config/v2", "repository_root": str(REPOSITORY),
                "evidence_root": str(evidence_root), "case_root": str(case_root),
                "tool_root": str(tool_root),
            }), encoding="utf-8")
            legacy = root / "legacy.sqlite3"
            connection = sqlite3.connect(legacy)
            connection.executescript(
                """
                CREATE TABLE cases(case_id TEXT PRIMARY KEY,title TEXT,authority TEXT,lead_examiner TEXT,source_timezone TEXT,status TEXT,opened_at_utc TEXT,closed_at_utc TEXT,notes TEXT);
                INSERT INTO cases VALUES('CASE-2026-9997','Synthetic',NULL,NULL,NULL,'open','2026-01-01T00:00:00Z',NULL,NULL);
                CREATE TABLE evidence_items(evidence_id TEXT,case_id TEXT,parent_evidence_id TEXT,source_path TEXT,evidence_type TEXT,description TEXT,size_bytes INTEGER,sha256 TEXT,sha512 TEXT,acquired_at_utc TEXT,verified_at_utc TEXT,write_protected INTEGER,metadata_json TEXT);
                CREATE TABLE custody_events(custody_event_id INTEGER,case_id TEXT,evidence_id TEXT,event_at_utc TEXT,actor TEXT,action TEXT,source_location TEXT,destination_location TEXT,purpose TEXT,notes TEXT);
                """
            )
            connection.commit(); connection.close()
            registry = root / "registry"; registry.mkdir()
            content = b"synthetic"
            manifest = {"schema":"nexus-lab-evidence-hash/v1","observed_at_utc":"2026-01-01T00:00:00Z","tool":{"name":"synthetic","version":"1"},"path":"X:/synthetic.bin","size_bytes":len(content),"mtime_ns":1,"sha256":hashlib.sha256(content).hexdigest(),"sha512":hashlib.sha512(content).hexdigest()}
            (registry / "EVID-0001.hash.json").write_text(json.dumps(manifest), encoding="utf-8")
            before = legacy.read_bytes()
            result = migrate_legacy(
                LabConfig.load(config_path), legacy_database=str(legacy), legacy_registry=str(registry),
                schema_path=str(REPOSITORY / "schemas" / "case-v2.sql"), authority="synthetic authority",
                scope="synthetic scope", question="synthetic question", examiner="test",
            )
            self.assertEqual(result["imported"]["evidence_items"], 1)
            self.assertEqual(legacy.read_bytes(), before)
            destination = sqlite3.connect(case_root / "CASE-2026-9997" / "registry" / "case.sqlite3")
            try:
                row = destination.execute("SELECT evidence_id,evidence_type,registered_by FROM evidence_items").fetchone()
                self.assertEqual(row[0], "EVID-0001")
                self.assertEqual(row[1], "not-determined")
                self.assertTrue(row[2].startswith("not-determined"))
            finally:
                destination.close()


if __name__ == "__main__":
    unittest.main()

