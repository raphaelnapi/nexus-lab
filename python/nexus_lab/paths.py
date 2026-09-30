from __future__ import annotations

import os
from pathlib import Path

from .errors import BoundaryError


def resolved(path: str | os.PathLike[str], *, strict: bool = True) -> Path:
    return Path(path).expanduser().resolve(strict=strict)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def require_within(
    path: str | os.PathLike[str],
    root: str | os.PathLike[str],
    *,
    strict: bool = True,
) -> Path:
    candidate = resolved(path, strict=strict)
    boundary = resolved(root, strict=True)
    if candidate == boundary or not is_within(candidate, boundary):
        raise BoundaryError(f"Path must be below, not equal to, {boundary}")
    return candidate


def ensure_distinct_roots(*roots: Path) -> None:
    normalized = [root.resolve(strict=False) for root in roots]
    for index, left in enumerate(normalized):
        for right in normalized[index + 1 :]:
            if left == right or is_within(left, right) or is_within(right, left):
                raise BoundaryError(f"Security roots overlap: {left} and {right}")


def reject_reparse_components(path: Path, stop: Path) -> None:
    """Reject symlink/junction traversal between stop and path.

    Path.resolve() protects containment, while this check makes the use of a
    reparse point explicit and fail-closed on evidence and working-copy paths.
    """
    current = path.absolute()
    stop = stop.absolute()
    while current != stop:
        attributes = getattr(current.lstat(), "st_file_attributes", 0) if current.exists() else 0
        is_junction = getattr(current, "is_junction", lambda: False)()
        if current.is_symlink() or is_junction or attributes & getattr(__import__("stat"), "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise BoundaryError(f"Reparse/symlink component is not allowed: {current}")
        parent = current.parent
        if parent == current:
            raise BoundaryError(f"Path does not descend from expected root: {stop}")
        current = parent


def reject_alternate_data_stream(path: Path) -> None:
    text = str(path)
    drive = path.drive
    remainder = text[len(drive) :]
    if ":" in remainder:
        raise BoundaryError(f"Alternate data streams are not accepted as file paths: {path}")


def reject_hardlink(path: Path) -> None:
    if path.stat().st_nlink > 1:
        raise BoundaryError(f"Hard-linked case output is not accepted: {path}")

