# Documentation Agent

## Overview

This agent is a CLI tool that calls an LLM with tools (`read_file`, `list_files`) to answer questions by reading the project documentation. It implements an agentic loop that iteratively calls tools until it has enough information to answer.

## Architecture

### Components

1. **agent.py** — Main CLI entry point
   - Parses command-line arguments
   - Reads LLM configuration from environment variables
   - Implements tool functions (`read_file`, `list_files`)
   - Runs the agentic loop
   - Outputs structured JSON response

2. **.env.agent.secret** — Environment configuration
   - `LLM_API_KEY` — API key for authentication
   - `LLM_API_BASE` — Base URL of the LLM API
   - `LLM_MODEL` — Model name to use

### LLM Provider

**Provider:** Qwen Code API

**Model:** `qwen3-coder-plus`

## Tools

### `read_file`

Reads contents of a file from the project repository.

**Parameters:**
- `path` (string, required) — Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as string, or error message.

**Security:** Rejects paths containing `../` to prevent directory traversal.

### `list_files`

Lists files and directories at a given path.

**Parameters:**
- `path` (string, required) — Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries (directories end with `/`).

**Security:** Rejects paths containing `../` to prevent directory traversal.

## Agentic Loop

```
1. Send user question + tool schemas to LLM
2. Parse LLM response:
   - If tool_calls present:
     a. Execute each tool
     b. Append tool results to messages (as "tool" role)
     c. Send updated messages back to LLM
     d. Repeat (max 10 iterations)
   - If no tool_calls (final answer):
     a. Extract answer from message content
     b. Extract source from last read_file path
     c. Output JSON and exit
```

### Flow Diagram

```
User question
     ↓
[system prompt + question + tool schemas] → LLM
     ↓
LLM response with tool_calls?
     │
     ├─YES→ Execute tools → Append results → Back to LLM
     │
     └─NO → Final answer
              ↓
         Extract answer + source
              ↓
         Output JSON
```

## System Prompt

The system prompt instructs the LLM to:
1. Use `list_files` to explore relevant directories (like `wiki`)
2. Use `read_file` to read specific files that contain the answer
3. Include source references in answers (file path + section anchor)
4. Format section references as: `filename.md#section-name` (lowercase, hyphens)

## Usage

### Basic Usage

```bash
uv run agent.py "How do you resolve a merge conflict?"
```

### Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's answer to the question |
| `source` | string | Reference to the wiki section (e.g., `wiki/file.md#section`) |
| `tool_calls` | array | List of all tool calls made during the agentic loop |

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for LLM authentication | `my-secret-key` |
| `LLM_API_BASE` | Base URL of the LLM API | `http://10.93.26.97:8080/v1` |
| `LLM_MODEL` | Model name to use | `qwen3-coder-plus` |

## Setup

1. Copy the example environment file:
   ```bash
   cp .env.agent.example .env.agent.secret
   ```

2. Edit `.env.agent.secret` and set your credentials.

3. Run the agent:
   ```bash
   uv run agent.py "Your question"
   ```

## Dependencies

- `httpx` — HTTP client for API calls
- `python-dotenv` — Load environment variables from `.env.agent.secret`

## Testing

Run the regression tests:

```bash
uv run pytest tests/test_agent.py -v
```

## Security

- Paths are validated to prevent directory traversal (`../`)
- Absolute paths are rejected
- Maximum 10 tool calls per question (prevents infinite loops)

## Future Improvements (Task 3)

- Add `query_api` tool to query the backend LMS API
- Enhance system prompt with domain knowledge
- Improve source extraction with section detection
