"""Workspace and safety configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path


def _parse_optional_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    return float(raw)


def _parse_optional_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    return int(raw)


def _parse_allowed_commands() -> frozenset[str] | None:
    raw = os.environ.get("AGENT_GODMODE_ALLOWED_COMMANDS")
    if not raw or not raw.strip():
        return None
    parts = [p.strip() for p in raw.split(",")]
    return frozenset(p for p in parts if p)


@dataclass(frozen=True)
class WorkspaceConfig:
    """Sandbox and limits for file and command tools."""

    root_dir: Path
    max_read_bytes: int = 512_000
    command_timeout_sec: float = 120.0
    max_command_output_bytes: int = 256_000
    list_files_max_entries: int = 2000
    """If set, only argv[0] basenames in this set may be executed (e.g. python, uv, npx)."""

    allowed_commands: frozenset[str] | None = None


def config_from_env() -> WorkspaceConfig:
    """Load config from environment. Requires AGENT_GODMODE_ROOT."""
    root = os.environ.get("AGENT_GODMODE_ROOT")
    if not root or not str(root).strip():
        raise RuntimeError(
            "AGENT_GODMODE_ROOT is required. Set it to your workspace directory "
            "(absolute path recommended), or pass --root when starting the server."
        )
    root_path = Path(root).expanduser().resolve()
    return WorkspaceConfig(
        root_dir=root_path,
        max_read_bytes=_parse_optional_int("AGENT_GODMODE_MAX_READ_BYTES", 512_000),
        command_timeout_sec=_parse_optional_float("AGENT_GODMODE_COMMAND_TIMEOUT", 120.0),
        max_command_output_bytes=_parse_optional_int(
            "AGENT_GODMODE_MAX_COMMAND_OUTPUT_BYTES", 256_000
        ),
        list_files_max_entries=_parse_optional_int("AGENT_GODMODE_LIST_MAX_ENTRIES", 2000),
        allowed_commands=_parse_allowed_commands(),
    )


def config_from_root(
    root: str | Path,
    *,
    max_read_bytes: int | None = None,
    command_timeout_sec: float | None = None,
    max_command_output_bytes: int | None = None,
    list_files_max_entries: int | None = None,
    allowed_commands: frozenset[str] | None = None,
) -> WorkspaceConfig:
    """Build config in-process (e.g. for tests or embedded agents)."""
    root_path = Path(root).expanduser().resolve()
    base = WorkspaceConfig(root_dir=root_path)
    overrides: dict = {}
    if max_read_bytes is not None:
        overrides["max_read_bytes"] = max_read_bytes
    if command_timeout_sec is not None:
        overrides["command_timeout_sec"] = command_timeout_sec
    if max_command_output_bytes is not None:
        overrides["max_command_output_bytes"] = max_command_output_bytes
    if list_files_max_entries is not None:
        overrides["list_files_max_entries"] = list_files_max_entries
    if allowed_commands is not None:
        overrides["allowed_commands"] = allowed_commands
    return replace(base, **overrides)
