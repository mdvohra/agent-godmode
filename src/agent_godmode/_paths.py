"""Resolve user-supplied paths under a workspace root."""

from __future__ import annotations

from pathlib import Path


def resolve_under_root(root: Path, user_path: str) -> Path:
    """
    Resolve user_path relative to root; reject escaping the workspace via .. or symlinks.
    """
    root = root.resolve()
    raw = (user_path or ".").strip().replace("\\", "/")
    # Treat absolute-looking paths as relative to root for sandboxing
    while raw.startswith("/"):
        raw = raw[1:]
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError(
            f"Path must stay under workspace root {root}: {user_path!r}"
        ) from exc
    return candidate
