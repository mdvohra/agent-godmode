"""Single-directory Python API: construct with a path, then call tools in-process."""

from __future__ import annotations

from pathlib import Path

from agent_godmode.config import WorkspaceConfig, config_from_root
from agent_godmode.tools import WorkspaceTools


class AgentWorkspace:
    """
    Bind all operations to one directory tree.

    ``read_file``, ``write_file``, ``edit_file``, ``list_files``, and ``run_command`` (default cwd)
    only touch paths under ``root``. Relative paths are interpreted under that root.

    Optional keyword arguments match :func:`agent_godmode.config.config_from_root`
    (e.g. ``allowed_commands``, ``command_timeout_sec``).
    """

    __slots__ = ("_config", "_tools")

    def __init__(self, root_dir: str | Path, **config_kwargs) -> None:
        self._config = config_from_root(root_dir, **config_kwargs)
        self._tools = WorkspaceTools(self._config)

    @property
    def root(self) -> Path:
        """Resolved workspace root (absolute)."""
        return self._config.root_dir

    @property
    def config(self) -> WorkspaceConfig:
        """Underlying config (timeouts, allowlists, etc.)."""
        return self._config

    def read_file(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        max_bytes: int | None = None,
    ) -> str:
        return self._tools.read_file(
            path,
            start_line=start_line,
            end_line=end_line,
            max_bytes=max_bytes,
        )

    def write_file(self, path: str, content: str, mode: str = "overwrite") -> str:
        return self._tools.write_file(path, content, mode=mode)

    def edit_file(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        return self._tools.edit_file(
            path,
            old_string=old_string,
            new_string=new_string,
            replace_all=replace_all,
        )

    def run_command(
        self,
        argv: list[str],
        cwd: str | None = None,
        timeout_sec: float | None = None,
    ) -> str:
        """Run ``argv`` with optional ``cwd`` (relative to root or absolute under root)."""
        return self._tools.run_command(argv, cwd=cwd, timeout_sec=timeout_sec)

    def list_files(
        self,
        path: str = ".",
        recursive: bool = False,
        glob_pattern: str | None = None,
        max_depth: int | None = None,
        include_dotfiles: bool = False,
    ) -> str:
        return self._tools.list_files(
            path,
            recursive=recursive,
            glob_pattern=glob_pattern,
            max_depth=max_depth,
            include_dotfiles=include_dotfiles,
        )

    def dispatch(self, name: str, arguments: dict) -> str:
        """Route a tool name and JSON-like args (for LLM tool-call handling)."""
        return self._tools.dispatch(name, arguments)
