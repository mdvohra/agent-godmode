"""MCP stdio server exposing workspace tools."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from agent_godmode.config import WorkspaceConfig, config_from_env
from agent_godmode.prompts import SERVER_INSTRUCTIONS_SUMMARY, TOOL_DESCRIPTIONS
from agent_godmode.tools import WorkspaceTools


def build_server(config: WorkspaceConfig) -> FastMCP:
    """Create a FastMCP app bound to the given workspace config."""
    wt = WorkspaceTools(config)

    mcp = FastMCP(
        name="agent-godmode",
        instructions=SERVER_INSTRUCTIONS_SUMMARY,
    )

    @mcp.tool(description=TOOL_DESCRIPTIONS["read_file"])
    def read_file(
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        max_bytes: int | None = None,
    ) -> str:
        return wt.read_file(
            path,
            start_line=start_line,
            end_line=end_line,
            max_bytes=max_bytes,
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["write_file"])
    def write_file(
        path: str,
        content: str,
        mode: str = "overwrite",
    ) -> str:
        return wt.write_file(path, content, mode=mode)

    @mcp.tool(description=TOOL_DESCRIPTIONS["edit_file"])
    def edit_file(
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        return wt.edit_file(
            path,
            old_string=old_string,
            new_string=new_string,
            replace_all=replace_all,
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["run_command"])
    def run_command(
        argv: list[str],
        cwd: str | None = None,
        timeout_sec: float | None = None,
    ) -> str:
        return wt.run_command(argv, cwd=cwd, timeout_sec=timeout_sec)

    @mcp.tool(description=TOOL_DESCRIPTIONS["list_files"])
    def list_files(
        path: str = ".",
        recursive: bool = False,
        glob_pattern: str | None = None,
        max_depth: int | None = None,
        include_dotfiles: bool = False,
    ) -> str:
        return wt.list_files(
            path,
            recursive=recursive,
            glob_pattern=glob_pattern,
            max_depth=max_depth,
            include_dotfiles=include_dotfiles,
        )

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent-godmode",
        description="MCP server: workspace-scoped file and command tools.",
    )
    parser.add_argument(
        "--root",
        "-r",
        default=None,
        help="Workspace root directory. Overrides AGENT_GODMODE_ROOT for this process.",
    )
    args = parser.parse_args()
    if args.root:
        os.environ["AGENT_GODMODE_ROOT"] = str(
            Path(args.root).expanduser().resolve()
        )
    config = config_from_env()
    build_server(config).run(transport="stdio")


if __name__ == "__main__":
    main()
