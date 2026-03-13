# Task 2 Plan: The Documentation Agent

## Overview

Extend the agent from Task 1 with tools (`read_file`, `list_files`) and an agentic loop to answer questions by reading the project wiki.

## Tool Definitions

### `read_file`

**Purpose:** Read contents of a file from the project repository.

**Parameters:**
- `path` (string, required) — relative path from project root

**Returns:** File contents as string, or error message if file doesn't exist.

**Security:** Reject paths containing `../` to prevent directory traversal.

### `list_files`

**Purpose:** List files and directories at a given path.

**Parameters:**
- `path` (string, required) — relative directory path from project root

**Returns:** Newline-separated listing of entries.

**Security:** Reject paths containing `../` to prevent directory traversal.

## Tool Schema (OpenAI Function Calling Format)

```json
[
  {
    "name": "read_file",
    "description": "Read contents of a file",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative path from project root"}
      },
      "required": ["path"]
    }
  },
  {
    "name": "list_files",
    "description": "List files in a directory",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative directory path from project root"}
      },
      "required": ["path"]
    }
  }
]
```

## Agentic Loop

```
1. Send user question + tool schemas to LLM
2. Parse LLM response:
   - If tool_calls present:
     a. Execute each tool
     b. Append tool results to messages
     c. Send back to LLM
     d. Repeat (max 10 iterations)
   - If no tool_calls (final answer):
     a. Extract answer from message content
     b. Extract source from the last read_file path
     c. Output JSON and exit
```

## System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to discover wiki files when needed
2. Use `read_file` to read relevant wiki files
3. Include source references (file path + section anchor) in answers
4. Call tools iteratively until it has enough information

## Output Format

```json
{
  "answer": "...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Security

- Validate paths: reject `../` or absolute paths
- Only allow paths within project root
- Maximum 10 tool calls per question (prevent infinite loops)

## Testing

Add 2 regression tests:
1. Question about merge conflicts → expects `read_file` in tool_calls, `wiki/git-workflow.md` in source
2. Question about wiki files → expects `list_files` in tool_calls
