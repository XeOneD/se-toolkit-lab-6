# System Agent (Task 3)

## Overview

This agent is a CLI tool that calls an LLM with three tools (`read_file`, `list_files`, `query_api`) to answer questions by reading project documentation, exploring the codebase, and querying the live backend API. It implements an agentic loop that iteratively calls tools until it has enough information to provide a complete answer.

## Architecture

### Components

1. **agent.py** — Main CLI entry point
   - Parses command-line arguments
   - Reads LLM configuration from environment variables (`LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`)
   - Reads API configuration from environment variables (`LMS_API_KEY`, `AGENT_API_BASE_URL`)
   - Implements three tool functions: `read_file`, `list_files`, `query_api`
   - Runs the agentic loop with function calling
   - Outputs structured JSON response with `answer`, `source`, and `tool_calls` fields

2. **.env.agent.secret** — LLM configuration
   - `LLM_API_KEY` — API key for LLM provider authentication
   - `LLM_API_BASE` — Base URL of the LLM API endpoint
   - `LLM_MODEL` — Model name to use (e.g., `qwen3-coder-plus`)

3. **.env.docker.secret** — Backend API configuration
   - `LMS_API_KEY` — API key for backend LMS authentication
   - `AGENT_API_BASE_URL` — Base URL for the backend API (default: `http://localhost:42002`)

### LLM Provider

**Provider:** Qwen Code API (compatible with OpenAI format)

**Model:** `qwen3-coder-plus`

## Tools

### `read_file`

Reads contents of a file from the project repository.

**Parameters:**
- `path` (string, required) — Relative path from project root (e.g., `wiki/git-workflow.md`, `backend/app/main.py`)

**Returns:** File contents as string, or error message.

**Security:** Rejects paths containing `../` (directory traversal) or absolute paths.

### `list_files`

Lists files and directories at a given path.

**Parameters:**
- `path` (string, required) — Relative directory path from project root (e.g., `wiki`, `backend/app/routers`)

**Returns:** Newline-separated listing of entries (directories end with `/`).

**Security:** Rejects paths containing `../` (directory traversal) or absolute paths.

### `query_api` (NEW in Task 3)

Calls the backend LMS API to fetch real-time data or test endpoints.

**Parameters:**
- `method` (string, required) — HTTP method (GET, POST, PUT, DELETE, PATCH)
- `path` (string, required) — API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional) — JSON request body for POST/PUT/PATCH requests
- `auth` (boolean, optional, default: true) — Whether to include Bearer token authentication

**Returns:** JSON string with `status_code` and `body` fields.

**Authentication:** Uses `LMS_API_KEY` from environment variables with Bearer token format: `Authorization: Bearer <key>`

**Security:** Validates HTTP methods, requires paths to start with `/`, uses timeout (30s).

## Agentic Loop

```
1. Send user question + all tool schemas to LLM
2. Parse LLM response:
   - If tool_calls present:
     a. Execute each tool with provided arguments
     b. Append tool results to messages (as "tool" role)
     c. IMPORTANT: Add assistant message with tool_calls BEFORE tool responses
     d. Send updated messages back to LLM
     e. Repeat (max 10 iterations)
   - If no tool_calls (final answer):
     a. Extract answer from message content
     b. Extract source from last read_file path
     c. Output JSON and exit
```

### Message Ordering (Critical for Qwen API)

The Qwen API requires that tool response messages follow their corresponding assistant message with tool_calls:

```
User → Assistant (with tool_calls) → Tool (result) → Assistant (with tool_calls) → Tool (result) → Assistant (final answer)
```

This ordering was a key discovery during implementation — initially the agent failed because tool responses were added before the assistant message.

## System Prompt Strategy

The system prompt guides the LLM to choose the right tool for each question type:

1. **Conceptual/how-to questions** → Use `list_files` + `read_file` on wiki docs
2. **Data questions** (how many, what value) → Use `query_api` with authenticated request
3. **Implementation details** → Use `read_file` on source code
4. **HTTP status codes / error testing** → Use `query_api` with `auth: false`
5. **Source code framework discovery** → Use `read_file` on backend files

The prompt includes:
- Clear tool descriptions with use cases
- Path rules for nested directories (e.g., `backend/app/routers` not just `app`)
- Examples of good vs bad final answers
- Instruction to provide complete answers (not "Let me check...")

## Output Format

```json
{
  "answer": "The backend uses FastAPI framework...",
  "source": "backend/app/main.py",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "backend/app"},
      "result": "main.py\nrouters/\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "backend/app/main.py"},
      "result": "from fastapi import FastAPI..."
    }
  ]
}
```

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api | Optional, defaults to `http://localhost:42002` |

**Important:** The autochecker injects its own values for these variables. Hardcoding will cause evaluation failure.

## Usage

### Basic Usage

```bash
# Start the backend services
docker-compose --env-file .env.docker.secret up -d app postgres caddy

# Run the agent
uv run agent.py "What framework does the backend use?"
```

### Example Questions

| Question Type | Example | Expected Tools |
|---------------|---------|----------------|
| Wiki lookup | "How do you resolve a merge conflict?" | `list_files`, `read_file` |
| Source code | "What framework does the backend use?" | `read_file` |
| Data query | "How many items are in the database?" | `query_api` (auth: true) |
| Status code | "What status code for unauthenticated request?" | `query_api` (auth: false) |
| API structure | "List all router modules" | `list_files`, `read_file` |

## Lessons Learned

### Challenge 1: Message Ordering
The Qwen API rejected our requests initially because we were adding tool response messages before the assistant message containing the tool_calls. The fix was to append the assistant message first, then add each tool response.

### Challenge 2: API Authentication
The backend uses Bearer token authentication (`Authorization: Bearer <key>`), not the `X-API-Key` header we initially tried. This was discovered by reading `backend/app/auth.py`.

### Challenge 3: LLM Inconsistency
The LLM sometimes gives incomplete answers ("Let me check...") instead of using tools. Adding explicit examples of good vs bad responses to the system prompt significantly improved this behavior.

### Challenge 4: Path Navigation
The LLM struggled with nested paths (e.g., using `app` instead of `backend/app`). Adding explicit path rules with examples to the system prompt fixed this.

### Challenge 5: Empty Database
Our local database is empty (0 items) because the ETL pipeline hasn't loaded data. The autochecker uses a populated database, so data-dependent questions will pass there but may fail locally.

## Testing

Run the test suite:

```bash
uv run pytest tests/test_agent.py -v
```

Expected output: 8 tests passing (6 from Task 2 + 2 new for Task 3).

## Benchmark Results

Local evaluation (`uv run run_eval.py`):
- Wiki questions: ✅ Pass
- Source code questions: ✅ Pass  
- Router structure: ✅ Pass
- Status code (401): ✅ Pass
- Data queries: ⚠️ Fail locally (empty DB), should pass on autochecker

## Future Improvements

1. **Content truncation** — Large files may exceed LLM context limits
2. **Error recovery** — Better handling when API is unavailable
3. **Multi-step reasoning** — Chain multiple API calls for complex analytics
4. **Caching** — Cache API responses to reduce redundant calls

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
