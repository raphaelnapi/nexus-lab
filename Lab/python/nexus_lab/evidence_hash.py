"""Create a versioned hash manifest for one evidence file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

from nexus_lab import __version__


TOOL_NAME = "nexus-lab-evidence-hash"


def contained(path: Path, root: Path) -> bool:
    """Return whether *path* is contained by *root* after resolution."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def digest(path: Path) -> tuple[str, str]:
    """Calculate SHA-256 and SHA-512 in one read-only pass."""
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha256.update(block)
            sha512.update(block)
    return sha256.hexdigest(), sha512.hexdigest()


def create_manifest(root: Path, evidence_path: Path, output_path: Path) -> dict[str, object]:
    """Hash a file below Evidence and create a new manifest below Registry."""
    root = root.resolve(strict=True)
    evidence_root = (root / "Evidence").resolve(strict=True)
    registry_root = (root / "Registry").resolve(strict=True)
    evidence = evidence_path.resolve(strict=True)
    output = output_path.resolve(strict=False)

    if not contained(evidence, evidence_root) or not evidence.is_file():
        raise ValueError("Evidence must be a regular file contained below Evidence/")
    if not contained(output, registry_root):
        raise ValueError("Output must be contained below Registry/")
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing manifest")
    if not output.parent.exists():
        raise FileNotFoundError("Output directory does not exist; initialize the case first")

    before = evidence.stat()
    sha256, sha512 = digest(evidence)
    after = evidence.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError("Evidence metadata changed while hashing; result discarded")

    manifest: dict[str, object] = {
        "schema": "nexus-lab-evidence-hash/v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tool": {
            "name": TOOL_NAME,
            "version": __version__,
            "python_version": platform.python_version(),
        },
        "path": os.fspath(evidence),
        "size_bytes": before.st_size,
        "mtime_ns": before.st_mtime_ns,
        "sha256": sha256,
        "sha512": sha512,
    }
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path, help="Nexus-Lab root")
    parser.add_argument("--evidence", required=True, type=Path, help="file below Evidence")
    parser.add_argument("--output", required=True, type=Path, help="new JSON file below Registry")
    args = parser.parse_args()

    try:
        create_manifest(args.root, args.evidence, args.output)
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    return 0
