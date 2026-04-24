"""agent-godmode: workspace-scoped MCP tools and in-process helpers (read/write/edit, commands, listings, prompts)."""

from __future__ import annotations

from agent_godmode.agent import run_agent_loop
from agent_godmode.agent_workspace import AgentWorkspace
from agent_godmode.config import WorkspaceConfig, config_from_env, config_from_root
from agent_godmode.prompts import (
    SERVER_INSTRUCTIONS_SUMMARY,
    SYSTEM_PROMPT_CHANGELOG,
    SYSTEM_PROMPT_V1,
    TOOL_DESCRIPTIONS,
)
from agent_godmode.schemas import OPENAI_TOOL_DEFINITIONS
from agent_godmode.server import build_server
from agent_godmode.tools import WorkspaceTools

__all__ = [
    "AgentWorkspace",
    "WorkspaceConfig",
    "WorkspaceTools",
    "config_from_env",
    "config_from_root",
    "build_server",
    "run_agent_loop",
    "SYSTEM_PROMPT_V1",
    "SYSTEM_PROMPT_CHANGELOG",
    "SERVER_INSTRUCTIONS_SUMMARY",
    "TOOL_DESCRIPTIONS",
    "OPENAI_TOOL_DEFINITIONS",
]
