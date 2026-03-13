# Task 1 Plan: Call an LLM from Code

## LLM Provider and Model

**Provider:** Qwen Code API (deployed on VM)

**Model:** `qwen3-coder-plus`

**Reasons for this choice:**
- 1000 free requests per day
- Available in Russia
- Supports OpenAI-compatible chat completions API
- Strong tool calling capabilities

## Architecture

### Components

1. **Environment Configuration** (`.env.agent.secret`)
   - `LLM_API_KEY` — API key from Qwen Code OAuth credentials
   - `LLM_API_BASE` — `http://10.93.26.97:<qwen-api-port>/v1`
   - `LLM_MODEL` — `qwen3-coder-plus`

2. **Agent CLI** (`agent.py`)
   - Parses command-line argument (question)
   - Reads environment variables from `.env.agent.secret`
   - Makes HTTP POST request to LLM API (OpenAI-compatible format)
   - Parses LLM response
   - Outputs JSON to stdout: `{"answer": "...", "tool_calls": []}`
   - All debug output goes to stderr

### Flow

```
User question (CLI arg)
    ↓
agent.py reads .env.agent.secret
    ↓
POST /v1/chat/completions → LLM API
    ↓
Parse response (choices[0].message.content)
    ↓
Output JSON: {"answer": "...", "tool_calls": []}
```

## Implementation Details

### Dependencies
- `requests` or `httpx` for HTTP calls
- `python-dotenv` for loading environment variables
- `json` for JSON parsing/output
- `argparse` or `sys.argv` for CLI arguments

### Output Format
```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Error Handling
- Timeout: 60 seconds for API call
- Exit code 0 on success
- All errors logged to stderr

## Testing Strategy

Create a regression test that:
1. Runs `uv run agent.py "test question"` as subprocess
2. Parses stdout JSON
3. Validates presence of `answer` and `tool_calls` fields
