from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path


lab_root = Path(__file__).resolve().parents[2]
schema_path = lab_root / "database" / "schema.sql"
migration_path = lab_root / "database" / "migrations" / "0002_tool_run_purpose.sql"


class ToolRunSchemaTests(unittest.TestCase):
    def test_new_schema_requires_run_purpose_and_parameter_explanation(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO cases(case_id, opened_at_utc) VALUES(?, ?)",
            ("CASE-TEST-0001", "2026-01-01T00:00:00Z"),
        )

        base_values = (
            "RUN-0001",
            "CASE-TEST-0001",
            "tool",
            "1.0",
            "tool --flag input",
            "WC-0001",
            "examiner",
            "2026-01-01T00:00:00Z",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO tool_runs(
                    tool_run_id, case_id, tool_name, tool_version, command_line,
                    input_reference, operator, started_at_utc
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                base_values,
            )

        connection.execute(
            """
            INSERT INTO tool_runs(
                tool_run_id, case_id, tool_name, tool_version, command_line,
                purpose, parameter_explanation, input_reference, operator,
                started_at_utc, output_summary
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                *base_values[:5],
                "Identify allocated filesystem entries",
                "--flag enables the documented bounded listing; input selects WC-0001",
                *base_values[5:],
                "No relevant output recorded yet",
            ),
        )
        stored = connection.execute(
            "SELECT purpose, parameter_explanation FROM tool_runs WHERE tool_run_id = ?",
            ("RUN-0001",),
        ).fetchone()
        self.assertEqual(stored[0], "Identify allocated filesystem entries")
        self.assertIn("--flag", stored[1])

    def test_migration_marks_legacy_records_and_guards_new_inserts(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.executescript(
            """
            CREATE TABLE tool_runs (tool_run_id TEXT PRIMARY KEY);
            INSERT INTO tool_runs(tool_run_id) VALUES('RUN-LEGACY');
            """
        )
        connection.executescript(migration_path.read_text(encoding="utf-8"))

        legacy = connection.execute(
            "SELECT purpose, parameter_explanation FROM tool_runs WHERE tool_run_id = ?",
            ("RUN-LEGACY",),
        ).fetchone()
        self.assertTrue(legacy[0].startswith("not determined:"))
        self.assertTrue(legacy[1].startswith("not determined:"))

        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO tool_runs(tool_run_id) VALUES('RUN-NEW')")


if __name__ == "__main__":
    unittest.main()
