from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .errors import NexusError
from .paths import ensure_distinct_roots, resolved


@dataclass(frozen=True)
class LabConfig:
    repository_root: Path
    evidence_root: Path
    case_root: Path
    tool_root: Path
    python_executable: str

    @classmethod
    def load(cls, path: str | Path) -> "LabConfig":
        config_path = resolved(path)
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if data.get("schema") != "nexus-lab/config/v2":
            raise NexusError("Unsupported or missing configuration schema")
        required = ("repository_root", "evidence_root", "case_root", "tool_root")
        missing = [name for name in required if not data.get(name)]
        if missing:
            raise NexusError(f"Missing configuration values: {', '.join(missing)}")
        roots = [resolved(data[name]) for name in required]
        ensure_distinct_roots(*roots)
        repository, evidence, cases, tools = roots
        return cls(
            repository_root=repository,
            evidence_root=evidence,
            case_root=cases,
            tool_root=tools,
            python_executable=data.get("python_executable", "python"),
        )

    def case_dir(self, case_id: str) -> Path:
        validate_case_id(case_id)
        return self.case_root / case_id


def validate_case_id(case_id: str) -> None:
    import re

    if not re.fullmatch(r"CASE-[0-9]{4}-[0-9]{4,}", case_id):
        raise NexusError(f"Invalid case ID: {case_id}")

