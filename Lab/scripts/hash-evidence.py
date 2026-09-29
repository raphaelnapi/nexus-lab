#!/usr/bin/env python3
"""Compatibility entry point; prefer scripts/python/hash_evidence.py."""

from __future__ import annotations

import sys
from pathlib import Path


lab_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(lab_root / "python"))

from nexus_lab.evidence_hash import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
