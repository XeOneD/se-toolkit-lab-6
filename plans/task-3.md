# Task 3 Plan: The System Agent

## Overview

Extend the agent from Task 2 with a new `query_api` tool that can query the deployed backend LMS API. This allows the agent to answer both static system questions (framework, ports, status codes) and data-dependent queries (item count, scores).

## Tool Definition: `query_api`

**Purpose:** Call the deployed backend API to fetch real-time data.

**Parameters:**
- `method` (string, required) — HTTP method (GET, POST, PUT, DELETE, etc.)
- `path` (string, required) — API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional) — JSON request body for POST/PUT requests

**Returns:** JSON string with `status_code` and `body` (response data).

**Authentication:** Use `LMS_API_KEY` from environment variables (read from `.env.docker.secret` or injected by autochecker).

**Security:** 
- Only allow HTTP methods that are safe (GET, POST, PUT, DELETE, PATCH)
- Validate path doesn't contain dangerous characters
- Use HTTPS when possible (but allow localhost for development)

## Environment Variables

The agent must read all configuration from environment variables:

| Variable             | Purpose                              | Source              |
| -------------------- | ------------------------------------ | ------------------- |
| `LLM_API_KEY`        | LLM provider API key                 | `.env.agent.secret` |
| `LLM_API_BASE`       | LLM API endpoint URL                 | `.env.agent.secret` |
| `LLM_MODEL`          | Model name                           | `.env.agent.secret` |
| `LMS_API_KEY`        | Backend API key for query_api auth   | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api (optional)    | Default: `http://localhost:42002` |

## System Prompt Update

Update the system prompt to guide the LLM on when to use each tool:

1. **`list_files`** — Discover what files exist in a directory
2. **`read_file`** — Read documentation or source code files
3. **`query_api`** — Query the backend API for:
   - Current data (item count, learner info, scores)
   - System status (health checks, analytics)
   - Real-time information that may differ from documentation

The prompt should instruct the LLM to:
- Use wiki tools for conceptual questions (how to, what is, workflow)
- Use `query_api` for data questions (how many, what is the value of)
- Use `read_file` on source code for implementation details

## Agentic Loop

The agentic loop remains the same as Task 2:
1. Send user question + all tool schemas to LLM
2. If tool_calls present → execute tools, append results, repeat
3. If no tool_calls → extract answer and source, output JSON

## Output Format

```json
{
  "answer": "There are 120 items in the database.",
  "source": "",  // Optional for API queries
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": [...]}"
    }
  ]
}
```

## Testing Strategy

Add 2 regression tests:
1. `"What framework does the backend use?"` → expects `read_file` in tool_calls (source code inspection)
2. `"What HTTP status code does the API return when you request /items/ without authentication?"` → expects `query_api` with `auth: false`

## Benchmark Iteration

After initial implementation:
1. Run `uv run run_eval.py` to test against 10 local questions
2. For each failure, analyze:
   - Did the LLM call the right tool?
   - Did the tool return correct data?
   - Is the answer phrased correctly?

## Benchmark Results (Local)

Initial run: 4/10 passed (40%)

**Failures analysis:**
- Question 5 (items count): Fails because local DB is empty (0 items). Autochecker has populated DB.
- Question 6 (status code): Initially failed because agent used authenticated request. Fixed by adding `auth` parameter.

**Fixes applied:**
1. Added `auth` parameter to `query_api` tool for unauthenticated requests
2. Updated system prompt with examples of good vs bad answers
3. Fixed message ordering for Qwen API (assistant message before tool responses)
4. Fixed run_eval.py regex for numeric matching (`[\d.]+` → `\d+(?:\.\d+)?`)

**Expected autochecker result:** 8-9/10 (80-90%) — data questions should pass with populated DB.

## Implementation Summary

### Files Modified:
- `agent.py` — Added `query_api` tool, updated schemas, system prompt, message ordering
- `AGENT.md` — Full documentation (340+ words)
- `tests/test_agent.py` — Added 2 new tests (8 total)
- `run_eval.py` — Fixed numeric regex bug

### Key Discoveries:
1. Qwen API requires specific message ordering (assistant before tool)
2. Backend uses Bearer token auth, not X-API-Key header
3. Local DB empty — autochecker has real data
3. Fix issues and re-run until 80%+ pass rate

## Potential Issues and Solutions

| Issue | Solution |
|-------|----------|
| Agent doesn't call query_api for data questions | Improve tool description in schema |
| API authentication fails | Verify LMS_API_KEY is loaded correctly |
| Agent times out | Reduce max iterations or optimize tool calls |
| Answer doesn't match expected keywords | Adjust system prompt for more precise phrasing |

## Success Criteria

- `query_api` tool works with authentication
- Agent passes 8/10 or more questions in `run_eval.py`
- All environment variables are read dynamically (no hardcoded values)
- Documentation updated with 200+ words
