"""Sandboxed workspace tools (usable from MCP or in-process agent loops)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from agent_godmode._paths import resolve_under_root
from agent_godmode.config import WorkspaceConfig


class WorkspaceTools:
    """Implements read_file, write_file, edit_file, run_command, list_files under a single root."""

    def __init__(self, config: WorkspaceConfig) -> None:
        self._c = config

    def dispatch(self, name: str, arguments: dict) -> str:
        """Route a tool name + JSON-like args dict to the right method; always returns a string."""
        try:
            if name == "read_file":
                return self.read_file(**arguments)
            if name == "write_file":
                return self.write_file(**arguments)
            if name == "run_command":
                return self.run_command(**arguments)
            if name == "list_files":
                return self.list_files(**arguments)
            if name == "edit_file":
                return self.edit_file(**arguments)
            return f"Error: unknown tool {name!r}"
        except TypeError as e:
            return f"Error: invalid arguments for {name}: {e}"
        except OSError as e:
            return f"Error: {e}"
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {self._c.command_timeout_sec}s"
        except PermissionError as e:
            return f"Error: {e}"
        except ValueError as e:
            return f"Error: {e}"

    def read_file(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        max_bytes: int | None = None,
    ) -> str:
        """
        Read a UTF-8 text file under the workspace.
        Lines are 1-based inclusive when start_line/end_line are set.
        """
        cap = max_bytes if max_bytes is not None else self._c.max_read_bytes
        if cap < 1:
            raise ValueError("max_bytes must be positive")

        target = resolve_under_root(self._c.root_dir, path)
        if not target.is_file():
            raise OSError(f"Not a file or does not exist: {path!r}")

        data = target.read_bytes()
        if len(data) > cap:
            return (
                f"Error: file exceeds max_bytes ({len(data)} > {cap}). "
                "Increase AGENT_GODMODE_MAX_READ_BYTES or pass a smaller max_bytes."
            )

        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)

        if start_line is not None or end_line is not None:
            s = (start_line or 1) - 1
            if s < 0:
                raise ValueError("start_line must be >= 1")
            e = end_line if end_line is not None else len(lines)
            if e < 1:
                raise ValueError("end_line must be >= 1")
            lines = lines[s:e]

        return "".join(lines)

    def write_file(
        self,
        path: str,
        content: str,
        mode: str = "overwrite",
    ) -> str:
        """
        Write text to a path under the workspace. mode: 'overwrite' or 'append'.
        Creates parent directories as needed.
        """
        if mode not in ("overwrite", "append"):
            raise ValueError("mode must be 'overwrite' or 'append'")

        target = resolve_under_root(self._c.root_dir, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == "overwrite":
            target.write_text(content, encoding="utf-8", newline="\n")
        else:
            with target.open("a", encoding="utf-8", newline="\n") as f:
                f.write(content)
        return f"OK: wrote {len(content.encode('utf-8'))} bytes to {path!r} ({mode})."

    def edit_file(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        """
        Replace old_string with new_string in an existing UTF-8 file under the workspace.
        If replace_all is False, old_string must occur exactly once. Writes with newline='\\n' like write_file.
        """
        if not old_string:
            raise ValueError("old_string must be non-empty")

        cap = self._c.max_read_bytes
        target = resolve_under_root(self._c.root_dir, path)
        if not target.is_file():
            raise OSError(f"Not a file or does not exist: {path!r}")

        data = target.read_bytes()
        if len(data) > cap:
            return (
                f"Error: file exceeds max_bytes ({len(data)} > {cap}) for edit_file. "
                "Increase AGENT_GODMODE_MAX_READ_BYTES or use a different approach."
            )

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return (
                "Error: file is not valid UTF-8 text; edit_file cannot safely edit it. "
                "Use read_file/write_file only if you understand the encoding, or convert the file first."
            )

        count = text.count(old_string)
        if count == 0:
            return (
                "Error: old_string not found in file. "
                "Call read_file first and copy the exact span you intend to replace."
            )
        if not replace_all and count > 1:
            return (
                f"Error: old_string matched {count} times; require exactly one match when "
                "replace_all is false. Widen old_string with surrounding context for a unique match, "
                "or set replace_all to true to replace every occurrence."
            )

        if replace_all:
            new_text = text.replace(old_string, new_string)
            replaced = count
        else:
            new_text = text.replace(old_string, new_string, 1)
            replaced = 1

        target.write_text(new_text, encoding="utf-8", newline="\n")
        return f"OK: edited {path!r}; replaced {replaced} occurrence(s)."

    def _resolve_cwd(self, cwd: str | None) -> Path:
        """Working directory for subprocess; must lie under workspace root."""
        root = self._c.root_dir.resolve()
        if not cwd:
            return root
        p = Path(cwd)
        if p.is_absolute():
            rp = p.resolve()
            try:
                rp.relative_to(root)
            except ValueError as exc:
                raise PermissionError(
                    f"cwd {cwd!r} must be under workspace root {root}"
                ) from exc
            return rp
        return resolve_under_root(self._c.root_dir, cwd)

    def run_command(
        self,
        argv: list[str],
        cwd: str | None = None,
        timeout_sec: float | None = None,
    ) -> str:
        """
        Run a command with argv list (no shell). cwd is relative to workspace root unless absolute;
        absolute cwd must still resolve under root.
        """
        if not argv:
            raise ValueError("argv must be non-empty")

        exe_name = Path(argv[0]).name
        allowed = self._c.allowed_commands
        if allowed is not None and exe_name not in allowed:
            raise PermissionError(
                f"Command {exe_name!r} is not allowed. "
                f"Allowed: {sorted(allowed)}. Adjust AGENT_GODMODE_ALLOWED_COMMANDS."
            )

        work = self._resolve_cwd(cwd)
        timeout = timeout_sec if timeout_sec is not None else self._c.command_timeout_sec
        env = os.environ.copy()

        proc = subprocess.run(
            argv,
            cwd=work,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            shell=False,
        )

        out = proc.stdout or ""
        err = proc.stderr or ""
        max_out = self._c.max_command_output_bytes
        text = (
            f"exit_code: {proc.returncode}\n"
            f"--- stdout ---\n{out}\n"
            f"--- stderr ---\n{err}"
        )
        raw = text.encode("utf-8")
        if len(raw) > max_out:
            text = raw[:max_out].decode("utf-8", errors="replace") + (
                f"\n\n[Output truncated to {max_out} bytes; "
                "set AGENT_GODMODE_MAX_COMMAND_OUTPUT_BYTES to raise the limit.]"
            )
        return text

    def list_files(
        self,
        path: str = ".",
        recursive: bool = False,
        glob_pattern: str | None = None,
        max_depth: int | None = None,
        include_dotfiles: bool = False,
    ) -> str:
        """List files under path (relative to workspace). Returns relative POSIX paths, one per line."""
        base = resolve_under_root(self._c.root_dir, path)
        if not base.exists():
            raise OSError(f"Path does not exist: {path!r}")
        if not base.is_dir():
            raise OSError(f"Not a directory: {path!r}")

        root = self._c.root_dir
        max_entries = self._c.list_files_max_entries
        results: list[str] = []

        def rel(p: Path) -> str:
            try:
                r = p.resolve().relative_to(root.resolve())
            except ValueError:
                return ""
            return r.as_posix()

        if glob_pattern:
            pattern = glob_pattern
            iterator = base.rglob(pattern) if recursive else base.glob(pattern)
            for p in iterator:
                if not include_dotfiles and any(part.startswith(".") for part in p.parts):
                    continue
                if p.is_file() or p.is_dir():
                    rs = rel(p if p.is_absolute() else p.resolve())
                    if rs:
                        results.append(rs)
                if len(results) >= max_entries:
                    break
        elif recursive:

            def walk(cur: Path) -> None:
                nonlocal results
                if len(results) >= max_entries:
                    return
                try:
                    entries = sorted(cur.iterdir(), key=lambda x: x.name.lower())
                except OSError:
                    return
                for child in entries:
                    if len(results) >= max_entries:
                        return
                    name = child.name
                    if not include_dotfiles and name.startswith("."):
                        continue
                    rs = rel(child)
                    if rs:
                        results.append(rs)
                    if child.is_dir():
                        depth = len(child.resolve().relative_to(base.resolve()).parts)
                        if max_depth is None or depth <= max_depth:
                            walk(child)

            walk(base)
        else:
            for child in sorted(base.iterdir(), key=lambda x: x.name.lower()):
                if not include_dotfiles and child.name.startswith("."):
                    continue
                rs = rel(child)
                if rs:
                    results.append(rs)
                if len(results) >= max_entries:
                    break

        note = ""
        if len(results) >= max_entries:
            note = f"\n[Listing truncated at {max_entries} entries; increase AGENT_GODMODE_LIST_MAX_ENTRIES.]"

        return "\n".join(results) + note
