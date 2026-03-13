# Agent Documentation

## Overview

This agent is a CLI tool that calls an LLM to answer questions. It is the foundation for the documentation agent (Task 2) and system agent (Task 3).

## Architecture

### Components

1. **agent.py** — Main CLI entry point
   - Parses command-line arguments
   - Reads LLM configuration from environment variables
   - Makes HTTP requests to the LLM API
   - Outputs structured JSON response

2. **.env.agent.secret** — Environment configuration
   - `LLM_API_KEY` — API key for authentication
   - `LLM_API_BASE` — Base URL of the LLM API
   - `LLM_MODEL` — Model name to use

### LLM Provider

**Provider:** Qwen Code API

**Model:** `qwen3-coder-plus`

**Why Qwen Code:**
- 1000 free requests per day
- Available in Russia
- OpenAI-compatible API
- Strong coding capabilities

### Flow

```
User question (CLI argument)
         ↓
agent.py loads .env.agent.secret
         ↓
POST /v1/chat/completions → Qwen Code API
         ↓
Parse response (choices[0].message.content)
         ↓
Output JSON: {"answer": "...", "tool_calls": []}
```

## Usage

### Basic Usage

```bash
uv run agent.py "What does REST stand for?"
```

### Output Format

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for LLM authentication | `my-secret-key` |
| `LLM_API_BASE` | Base URL of the LLM API | `http://10.93.26.97:42005/v1` |
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

Run the regression test:

```bash
uv run pytest tests/test_agent.py -v
```

## Future Improvements (Tasks 2-3)

- Add tools for reading files and querying APIs
- Implement agentic loop for multi-step reasoning
- Add system prompt with domain knowledge
