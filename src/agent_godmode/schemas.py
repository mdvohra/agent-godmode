"""OpenAI-style tool definitions (single source for host agent loops)."""

from __future__ import annotations

from agent_godmode.prompts import TOOL_DESCRIPTIONS

_READ_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path relative to workspace root."},
        "start_line": {
            "type": "integer",
            "description": "First line to include (1-based). Omit from start of file.",
        },
        "end_line": {
            "type": "integer",
            "description": "Last line to include (1-based inclusive). Omit through end of file.",
        },
        "max_bytes": {
            "type": "integer",
            "description": "Optional cap on bytes read (default from server config).",
        },
    },
    "required": ["path"],
    "additionalProperties": False,
}

_WRITE_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path relative to workspace root."},
        "content": {"type": "string", "description": "Full text to write."},
        "mode": {
            "type": "string",
            "enum": ["overwrite", "append"],
            "description": "overwrite replaces file; append appends text.",
        },
    },
    "required": ["path", "content"],
    "additionalProperties": False,
}

_EDIT_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path relative to workspace root."},
        "old_string": {
            "type": "string",
            "description": "Exact substring to find (non-empty). Must match once unless replace_all is true.",
        },
        "new_string": {
            "type": "string",
            "description": "Replacement text (may be empty). Newlines are written like write_file (normalized to \\n).",
        },
        "replace_all": {
            "type": "boolean",
            "description": "If true, replace every occurrence; if false, require exactly one occurrence.",
        },
    },
    "required": ["path", "old_string", "new_string"],
    "additionalProperties": False,
}

_RUN_COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "argv": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Executable and arguments (no shell). argv[0] is the program name.",
        },
        "cwd": {
            "type": "string",
            "description": "Working directory, relative to workspace unless absolute under root.",
        },
        "timeout_sec": {
            "type": "number",
            "description": "Optional timeout in seconds (server default if omitted).",
        },
    },
    "required": ["argv"],
    "additionalProperties": False,
}

_LIST_FILES_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Directory path relative to workspace (default '.').",
        },
        "recursive": {"type": "boolean", "description": "Recurse into subdirectories."},
        "glob_pattern": {
            "type": "string",
            "description": "If set, filter with glob (e.g. '*.py').",
        },
        "max_depth": {
            "type": "integer",
            "description": "When recursive, maximum directory depth below path.",
        },
        "include_dotfiles": {
            "type": "boolean",
            "description": "Include entries whose names start with a dot.",
        },
    },
    "additionalProperties": False,
}


def _openai_tool(name: str, schema: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": TOOL_DESCRIPTIONS[name],
            "parameters": schema,
        },
    }


OPENAI_TOOL_DEFINITIONS: list[dict] = [
    _openai_tool("read_file", _READ_FILE_SCHEMA),
    _openai_tool("write_file", _WRITE_FILE_SCHEMA),
    _openai_tool("edit_file", _EDIT_FILE_SCHEMA),
    _openai_tool("run_command", _RUN_COMMAND_SCHEMA),
    _openai_tool("list_files", _LIST_FILES_SCHEMA),
]
