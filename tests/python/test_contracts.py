from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]


class RepositoryContractTests(unittest.TestCase):
    def test_catalog_and_methods_are_valid_json(self) -> None:
        catalog = json.loads((REPOSITORY / "tools" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["schema"], "nexus-lab/tool-catalog/v2")
        identifiers = [value["id"] for value in catalog["capabilities"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for method_path in (REPOSITORY / "methods").glob("*.json"):
            method = json.loads(method_path.read_text(encoding="utf-8"))
            self.assertEqual(method["schema"], "nexus-lab/method-pack/v2")
            self.assertIn(method["capability_id"], identifiers)

    def test_schema_creates_every_v2_domain_table(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.executescript((REPOSITORY / "schemas" / "case-v2.sql").read_text(encoding="utf-8"))
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {
            "schema_version", "cases", "case_roles", "evidence_items", "custody_events",
            "working_copies", "environments", "tool_versions", "method_versions", "approvals",
            "tool_runs", "run_inputs", "run_outputs", "artifacts", "timeline_events",
            "statements", "findings", "reviews", "reports", "provenance_edges",
            "audit_events", "ledger_checkpoints", "migration_records",
        }
        self.assertTrue(required.issubset(tables))

    def test_each_skill_has_metadata_and_five_evaluations(self) -> None:
        skills_root = REPOSITORY / ".codex" / "skills"
        skills = {path.parent.name for path in skills_root.glob("*/SKILL.md")}
        self.assertEqual(len(skills), 8)
        for skill in skills:
            self.assertTrue((skills_root / skill / "agents" / "openai.yaml").is_file())
        counts = {skill: 0 for skill in skills}
        for line in (REPOSITORY / "tests" / "skills" / "evals.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            counts[item["skill"]] += 1
        self.assertTrue(all(count == 5 for count in counts.values()), counts)


if __name__ == "__main__":
    unittest.main()

