from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from .errors import IntegrityError


@dataclass(frozen=True)
class FileDigest:
    size_bytes: int
    sha256: str
    sha512: str
    mtime_ns: int


def hash_file(path: Path, block_size: int = 4 * 1024 * 1024) -> FileDigest:
    before = path.stat()
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(block_size), b""):
            sha256.update(block)
            sha512.update(block)
    after = path.stat()
    identity_before = (before.st_size, before.st_mtime_ns, getattr(before, "st_ino", 0))
    identity_after = (after.st_size, after.st_mtime_ns, getattr(after, "st_ino", 0))
    if identity_before != identity_after:
        raise IntegrityError("Input metadata changed while hashing")
    return FileDigest(
        size_bytes=after.st_size,
        sha256=sha256.hexdigest(),
        sha512=sha512.hexdigest(),
        mtime_ns=after.st_mtime_ns,
    )


def safe_relative(path: Path, root: Path) -> str:
    return os.fspath(path.relative_to(root)).replace("\\", "/")

