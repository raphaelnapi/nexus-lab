from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


lab_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(lab_root / "python"))

from nexus_lab.evidence_hash import create_manifest, digest  # noqa: E402


class EvidenceHashTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.evidence_root = self.root / "Evidence"
        self.registry_case = self.root / "Registry" / "CASE-TEST-0001"
        self.evidence_root.mkdir()
        self.registry_case.mkdir(parents=True)
        self.evidence = self.evidence_root / "sample.bin"
        self.evidence.write_bytes(b"Nexus-Lab test evidence\n")

    def test_digest_known_content(self) -> None:
        sha256, sha512 = digest(self.evidence)
        self.assertEqual(len(sha256), 64)
        self.assertEqual(len(sha512), 128)

    def test_manifest_is_created_below_registry(self) -> None:
        output = self.registry_case / "sample.hash.json"
        manifest = create_manifest(self.root, self.evidence, output)
        stored = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(stored, manifest)
        self.assertEqual(stored["schema"], "nexus-lab-evidence-hash/v1")
        self.assertEqual(stored["tool"]["name"], "nexus-lab-evidence-hash")

    def test_refuses_output_outside_registry(self) -> None:
        with self.assertRaises(ValueError):
            create_manifest(self.root, self.evidence, self.root / "outside.json")

    def test_refuses_to_overwrite_manifest(self) -> None:
        output = self.registry_case / "existing.json"
        output.write_text("existing", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            create_manifest(self.root, self.evidence, output)


if __name__ == "__main__":
    unittest.main()
