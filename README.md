# agent-godmode

<!-- mcp-name: io.github.mdvohra/agent-godmode -->

Workspace-scoped **MCP tools** for building Cursor-style agents: **read_file**, **write_file**, **edit_file**, **run_command**, **list_files**. Includes **strict, versioned system prompts** (`SYSTEM_PROMPT_V1`) and **OpenAI-style tool definitions** so your app can wire any LLM with one import.

The **LLM and API keys stay in your app**. This package provides tool execution, sandboxing, and prompts—not a hosted model.

**OpenAI + in-process tools:** the **Tier B** section below is self-contained—copy the Python into a script, module, or REPL; no separate artifact is required.

## Install

```bash
pip install agent-godmode
```

Editable / dev:

```bash
pip install -e ".[dev]"
```

**Migrating from `mcp-agent-tools`:** uninstall the old package, install **`agent-godmode`**, change Python imports from `mcp_agent_tools` to **`agent_godmode`**, the CLI from `mcp-agent-tools` to **`agent-godmode`**, and environment variables from `MCP_AGENT_TOOLS_*` to **`AGENT_GODMODE_*`** (for example `AGENT_GODMODE_ROOT`).

## Tools

All tools are scoped to a single **workspace root**. Paths are relative to that root (or absolute only if they resolve under it). The same operations are available over **MCP** (the `agent-godmode` server) and in-process via **`AgentWorkspace`** / **`WorkspaceTools`**.

| Tool | Purpose |
|------|---------|
| **`read_file`** | Read a UTF-8 text file; optional line range and byte cap. |
| **`write_file`** | Create or overwrite/append UTF-8 text; creates parent directories. |
| **`edit_file`** | Search-and-replace in an existing UTF-8 file: non-empty `old_string`, optional `replace_all`. With `replace_all=false`, `old_string` must match **exactly once** (use surrounding context from `read_file` for uniqueness). Invalid UTF-8 returns an error instead of corrupting binary data. |
| **`list_files`** | List directory entries with optional recursion, glob, depth cap, dotfile control. |
| **`run_command`** | Run a subprocess from an **`argv` list only** (no shell); optional `cwd` under the root. |

For LLM integrations, tool shapes and descriptions are centralized in **`OPENAI_TOOL_DEFINITIONS`** and **`TOOL_DESCRIPTIONS`**; agent behavior is guided by **`SYSTEM_PROMPT_V1`**.

## Tier A — Cursor (or any MCP client)

**1.** Pick a workspace directory (only paths under this root are allowed).

**2.** Add a server entry (stdio). Example for a global MCP config (paths use forward slashes on Windows):

```json
{
  "mcpServers": {
    "agent-godmode": {
      "command": "agent-godmode",
      "args": [],
      "env": {
        "AGENT_GODMODE_ROOT": "D:/your/project"
      }
    }
  }
}
```

Or with an explicit CLI root (overrides env for that process):

```json
{
  "mcpServers": {
    "agent-godmode": {
      "command": "agent-godmode",
      "args": ["--root", "D:/your/project"]
    }
  }
}
```

**3.** Paste **`SYSTEM_PROMPT_V1`** (from `agent_godmode.prompts` or below) into your host’s system prompt if the client does not load server `instructions` automatically.

### Environment variables


| Variable                                   | Meaning                                                                                                                       |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `AGENT_GODMODE_ROOT`                     | **Required** unless `--root` is passed. Absolute workspace root.                                                              |
| `AGENT_GODMODE_MAX_READ_BYTES`           | Max bytes per read (default `512000`).                                                                                        |
| `AGENT_GODMODE_COMMAND_TIMEOUT`          | Subprocess timeout in seconds (default `120`).                                                                                |
| `AGENT_GODMODE_MAX_COMMAND_OUTPUT_BYTES` | Truncate stdout/stderr combined (default `256000`).                                                                           |
| `AGENT_GODMODE_LIST_MAX_ENTRIES`         | Cap for list_files (default `2000`).                                                                                          |
| `AGENT_GODMODE_ALLOWED_COMMANDS`         | Comma-separated **basenames** allowed as `argv[0]` (e.g. `python,uv,node`). If unset, all commands allowed under the sandbox. |


## Tier B — Python app (in-process + OpenAI)

**Design notes**

- **Workspace root** — Examples use `D:\Avi-assign` as a placeholder; point `WORK_DIR` at any directory you control.
- **API key policy** — `OPENAI_API_KEY` is required **only** for Chat Completions. Imports set `client = OpenAI() if HAS_OPENAI_KEY else None`; workspace setup and **direct `edit_file`** run without a key.
- **Model-authored I/O** — For `write_file`, persist **only** text returned by the model. For `edit_file`, the model must copy **`old_string`** exactly from **`read_file`** (see `SYSTEM_PROMPT_V1`).

### 1. Install dependencies

In a shell or any interactive Python session:

```bash
pip install -q openai
pip install -q -e "D:/MCP"   # editable checkout; or: pip install agent-godmode
```

If your environment supports line magics (for example `%pip` in IPython), you can run the same installs there; do not place shell comments on the same line as `%pip`.

### 2. Imports and API key handling

```python
import os
from pathlib import Path

# OPENAI_API_KEY is required only for steps that call Chat Completions (LLM + agent loops).
# Workspace + direct edit_file work without a key.
# Set via OS env or e.g. %env OPENAI_API_KEY sk-... in IPython
# Local-only optional override — never commit a real key:
# os.environ["OPENAI_API_KEY"] = "sk-..."

from openai import OpenAI

from agent_godmode import (
    AgentWorkspace,
    OPENAI_TOOL_DEFINITIONS,
    SYSTEM_PROMPT_V1,
    run_agent_loop,
)

HAS_OPENAI_KEY = bool(os.environ.get("OPENAI_API_KEY"))
client = OpenAI() if HAS_OPENAI_KEY else None
MODEL = "gpt-4o-mini"

if not HAS_OPENAI_KEY:
    print(
        "Note: OPENAI_API_KEY not set — Chat Completions examples will raise until you set it. "
        "Workspace + direct edit_file still work."
    )
```

### 3. Workspace bootstrap and seed file

```python
# Fixed workspace — all reads/writes/commands stay under this folder
WORK_DIR = Path(r"D:\Avi-assign")
WORK_DIR.mkdir(parents=True, exist_ok=True)
print("Workspace:", WORK_DIR.resolve())

hello = WORK_DIR / "hello.txt"
if not hello.exists():
    hello.write_text("Hello from Avi-assign workspace.\n", encoding="utf-8")

ws = AgentWorkspace(WORK_DIR)
print(ws.read_file("hello.txt"))
print("--- list_files ---")
print(ws.list_files(".", recursive=False))
```

### 4. LLM-authored file body (no tool calls)

**Requires `OPENAI_API_KEY`.** Skip if you are only exercising tools without the API.

```python
if client is None:
    raise ValueError(
        "Set OPENAI_API_KEY to run this block (e.g. export OPENAI_API_KEY=... or %env in IPython). "
        "Skip if you only want workspace / edit_file demos."
    )

# 1) Context from disk (read-only)
context = ws.read_file("hello.txt")

# 2) Ask the model to author the entire new file; no static template for the body
user_prompt = (
    "Here is the current contents of hello.txt in my workspace:\n\n"
    f"---\n{context}\n---\n\n"
    "Write ONLY the body of a new Markdown file (no preamble, no code fences) "
    "with a title line and two bullet points explaining what this greeting is for."
)

resp = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": "You output only the file body the user asked for. No extra commentary.",
        },
        {"role": "user", "content": user_prompt},
    ],
)

generated = (resp.choices[0].message.content or "").strip()
if not generated:
    raise RuntimeError("LLM returned empty content; nothing to write.")

# 3) Persist exactly what the LLM produced
out_rel = "llm_generated_notes.md"
ws.write_file(out_rel, generated, mode="overwrite")
print(f"Wrote {out_rel!r} ({len(generated)} chars from model)\n")
print(ws.read_file(out_rel))
```

### 5. Direct `edit_file` (no Chat Completions)

**No API key required.** The next lines create `ws` if you have not run the workspace section yet (same root).

```python
# Direct edit_file (no Chat Completions call).
# If `ws` is not defined yet (e.g. you skipped §3), the next few lines create it (same WORK_DIR).
from pathlib import Path

from agent_godmode import AgentWorkspace

if "ws" not in globals():
    WORK_DIR = Path(r"D:\Avi-assign")
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    ws = AgentWorkspace(WORK_DIR)

demo_edit = "edit_demo.txt"
ws.write_file(
    demo_edit,
    "version: 1\nstatus: draft\nfooter: end\n",
    mode="overwrite",
)
print("--- before ---")
print(ws.read_file(demo_edit), end="")
print(ws.edit_file(demo_edit, old_string="status: draft", new_string="status: ready"))
print("--- after ---")
print(ws.read_file(demo_edit), end="")
```

### 6. Agent loop: model calls `write_file`

**Requires `OPENAI_API_KEY`.**

```python
if client is None:
    raise ValueError(
        "Set OPENAI_API_KEY to run this block. "
        "Skip if you only need workspace or direct edit_file."
    )


def complete(messages, tools):
    """One Chat Completions turn; return OpenAI-shaped dict for run_agent_loop."""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    return resp.model_dump()


answer = run_agent_loop(
    complete,
    "Use tools only. List the workspace root, read hello.txt, then call write_file on "
    "agent_notes.txt. The `content` argument must be your own freshly written summary "
    "(several sentences) based only on what you read—do not paste boilerplate.",
    ws,
    system_prompt=SYSTEM_PROMPT_V1,
    max_turns=12,
)
print("--- final answer ---")
print(answer)
print("--- agent_notes.txt (if created by tool write_file) ---")
p = WORK_DIR / "agent_notes.txt"
print(p.read_text(encoding="utf-8") if p.exists() else "(missing)")
```

### 7. Agent loop: model calls `edit_file`

**Requires `OPENAI_API_KEY` and the `complete` function from §6.**

```python
from pathlib import Path

from agent_godmode import AgentWorkspace

if "ws" not in globals():
    WORK_DIR = Path(r"D:\Avi-assign")
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    ws = AgentWorkspace(WORK_DIR)
if "complete" not in globals():
    raise NameError("Define `complete` in §6 (after imports) before running this block.")
if client is None:
    raise ValueError(
        "Set OPENAI_API_KEY to run this block. "
        "The direct edit_file example in §5 works without a key."
    )

target = "edit_agent_target.txt"
ws.write_file(
    target,
    "# Demo\nThere are three erorrs in this sentance.\n",
    mode="overwrite",
)
edit_answer = run_agent_loop(
    complete,
    (
        f"Use tools only. Read `{target}`. Then use edit_file (not write_file) to fix typos: "
        "change erorrs to errors and sentance to sentence. "
        "Copy old_string exactly from read_file; use two edit_file calls or replace_all where appropriate."
    ),
    ws,
    system_prompt=SYSTEM_PROMPT_V1,
    max_turns=14,
)
print("--- agent (edit_file) answer ---")
print(edit_answer)
print("--- file after agent ---")
print(ws.read_file(target), end="")
```

### 8. Optional: custom tool loop without `run_agent_loop`

Use **`OPENAI_TOOL_DEFINITIONS`**, call the Chat Completions API with `tools=...`, parse **`tool_calls`**, and route each call through **`ws.dispatch(name, json.loads(arguments))`** (requires `import json`). For **`write_file`**, the **`content`** field should be whatever the **model** authored; for **`edit_file`**, pass **`old_string`**, **`new_string`**, and **`replace_all`** exactly as the model returned.

### Optional limits on `AgentWorkspace`

```python
ws = AgentWorkspace(
    r"D:\Avi-assign",
    allowed_commands=frozenset({"python", "uv"}),
    command_timeout_sec=60.0,
)
```

### Lower-level (`WorkspaceTools` + `OPENAI_TOOL_DEFINITIONS`)

Same sandbox without `AgentWorkspace`: use `config_from_root(...)` and `WorkspaceTools`. Pass **`OPENAI_TOOL_DEFINITIONS`** to your provider as `tools=` when you implement your own loop instead of `run_agent_loop`.

```python
from agent_godmode import WorkspaceTools, OPENAI_TOOL_DEFINITIONS, SYSTEM_PROMPT_V1
from agent_godmode.config import config_from_root

tools = WorkspaceTools(config_from_root(r"D:\Avi-assign"))
print(tools.read_file("hello.txt"))
```

Compose the system message:

```python
final_system = SYSTEM_PROMPT_V1 + "\n\n" + "Your org rules here."
```

### Imports reference

- `AgentWorkspace` — pass a directory path; use `read_file` / `write_file` / `edit_file` / `list_files` / `run_command` on that tree only
- `SYSTEM_PROMPT_V1`, `SYSTEM_PROMPT_CHANGELOG`, `TOOL_DESCRIPTIONS`
- `OPENAI_TOOL_DEFINITIONS` — same shapes as MCP tools (for `tools=` in chat completions)
- `build_server(config)` — build a `FastMCP` app (stdio via `build_server(cfg).run()`)
- `run_agent_loop` — minimal multi-turn executor with your `complete` callable (accepts `WorkspaceConfig` or `AgentWorkspace`)

## Safety model

- **Python:** all paths are resolved **under** the directory you passed to `AgentWorkspace(...)` or `config_from_root(...)`.
- **MCP / CLI:** same rule via `AGENT_GODMODE_ROOT` or `--root` (no `..` escape).
- `read_file`, `write_file`, and `edit_file` only touch UTF-8 text paths under that root; `edit_file` requires valid UTF-8 (strict decode).
- `run_command` uses **`argv` only** (no shell). Optional allowlist via `AGENT_GODMODE_ALLOWED_COMMANDS`.
- Subprocess inherits the current environment; avoid passing secrets you do not want child processes to see.

## CLI

```bash
agent-godmode --root D:/your/project
```

Runs the MCP server on **stdio** (default for Cursor).

## Agent loop (conceptual)

1. System = `SYSTEM_PROMPT_V1` (+ optional suffix).
2. User message + `OPENAI_TOOL_DEFINITIONS` → your LLM.
3. For each `tool_call`, run `WorkspaceTools.dispatch` (or MCP `call_tool`) — including `read_file`, `write_file`, **`edit_file`**, `list_files`, and `run_command` as defined by the server.
4. Append tool results; repeat until the model returns text without tools.

`run_agent_loop` implements steps 2–4 given your `complete()` function.

## License

MIT

[![MCP Badge](https://lobehub.com/badge/mcp/mdvohra-agent-godmode)](https://lobehub.com/mcp/mdvohra-agent-godmode)

[![MCP Badge](https://lobehub.com/badge/mcp-full/mdvohra-agent-godmode?theme=light)](https://lobehub.com/mcp/mdvohra-agent-godmode)
