"""Optional in-process agent loop helper (user supplies the LLM client)."""

from __future__ import annotations

import json
from typing import Any, Callable

from agent_godmode.agent_workspace import AgentWorkspace
from agent_godmode.config import WorkspaceConfig
from agent_godmode.prompts import SYSTEM_PROMPT_V1
from agent_godmode.schemas import OPENAI_TOOL_DEFINITIONS
from agent_godmode.tools import WorkspaceTools


def _workspace_config(workspace: WorkspaceConfig | AgentWorkspace) -> WorkspaceConfig:
    return workspace.config if isinstance(workspace, AgentWorkspace) else workspace


def _extract_assistant_message(raw: Any) -> dict[str, Any]:
    """Accept OpenAI chat completion shape or a bare assistant message dict."""
    if not isinstance(raw, dict):
        raise TypeError("LLM response must be a dict")
    if raw.get("role") == "assistant" and (
        "content" in raw or "tool_calls" in raw
    ):
        return raw
    choices = raw.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message")
        if isinstance(msg, dict):
            return msg
    raise TypeError(
        "Expected assistant message dict or OpenAI-style {'choices': [{'message': ...}]}"
    )


def run_agent_loop(
    complete: Callable[[list[dict[str, Any]], list[dict[str, Any]]], Any],
    user_message: str,
    workspace: WorkspaceConfig | AgentWorkspace,
    *,
    system_prompt: str | None = None,
    max_turns: int = 32,
) -> str:
    """
    Run a simple tool loop: call ``complete(messages, tools)`` each turn until the model
    returns text without tool_calls.

    ``complete`` must return either an assistant message dict
    (``role``, ``content``, optional ``tool_calls``) or an OpenAI-style
    ``{"choices": [{"message": ...}]}``.

    Tool definitions use the same JSON schema as :data:`OPENAI_TOOL_DEFINITIONS`.
    """
    system = system_prompt or SYSTEM_PROMPT_V1
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]
    tools = OPENAI_TOOL_DEFINITIONS
    exec_tools = WorkspaceTools(_workspace_config(workspace))

    for _ in range(max_turns):
        raw = complete(messages, tools)
        msg = _extract_assistant_message(raw)
        tool_calls = msg.get("tool_calls") or []

        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": msg.get("content"),
        }
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        if not tool_calls:
            return (msg.get("content") or "").strip()

        for tc in tool_calls:
            tid = tc.get("id", "")
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            args_raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError as e:
                result = f"Error: invalid JSON arguments for {name}: {e}"
            else:
                if not isinstance(args, dict):
                    result = f"Error: arguments for {name} must be a JSON object"
                else:
                    result = exec_tools.dispatch(name, args)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tid,
                    "content": result,
                }
            )

    raise RuntimeError(f"Exceeded max_turns={max_turns} without finishing")
