#!/usr/bin/env python3
"""
Documentation Agent CLI - Call an LLM with tools.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
    All debug output goes to stderr.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Maximum tool calls per question
MAX_TOOL_CALLS = 10


def load_env():
    """Load environment variables from .env.agent.secret and .env.docker.secret."""
    # Load LLM config from .env.agent.secret
    env_path = Path(__file__).parent / ".env.agent.secret"
    if not env_path.exists():
        print(f"Error: {env_path} not found", file=sys.stderr)
        sys.exit(1)
    load_dotenv(env_path)
    
    # Also load .env.docker.secret for LMS_API_KEY if it exists
    docker_env_path = Path(__file__).parent / ".env.docker.secret"
    if docker_env_path.exists():
        load_dotenv(docker_env_path, override=False)


def get_llm_config():
    """Get LLM configuration from environment variables."""
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    if not all([api_key, api_base, model]):
        print("Error: Missing LLM configuration", file=sys.stderr)
        print(f"  LLM_API_KEY: {'set' if api_key else 'missing'}", file=sys.stderr)
        print(f"  LLM_API_BASE: {'set' if api_base else 'missing'}", file=sys.stderr)
        print(f"  LLM_MODEL: {'set' if model else 'missing'}", file=sys.stderr)
        sys.exit(1)

    return api_key, api_base, model


def get_api_config() -> tuple[str, str]:
    """Get API configuration from environment variables."""
    lms_api_key = os.getenv("LMS_API_KEY")
    api_base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

    if not lms_api_key:
        print("Error: Missing LMS_API_KEY", file=sys.stderr)
        print("  LMS_API_KEY: missing", file=sys.stderr)
        sys.exit(1)

    return lms_api_key, api_base_url


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent


def validate_path(path: str) -> tuple[bool, str]:
    """Validate that path is safe (no directory traversal)."""
    if not path:
        return False, "Path cannot be empty"
    if path.startswith("/"):
        return False, "Absolute paths are not allowed"
    if ".." in path:
        return False, "Directory traversal (..) is not allowed"
    return True, ""


def read_file(path: str) -> dict[str, Any]:
    """Read contents of a file."""
    valid, error = validate_path(path)
    if not valid:
        return {"success": False, "error": error, "content": ""}

    project_root = get_project_root()
    full_path = project_root / path

    if not full_path.exists():
        return {"success": False, "error": f"File not found: {path}", "content": ""}

    if not full_path.is_file():
        return {"success": False, "error": f"Not a file: {path}", "content": ""}

    try:
        content = full_path.read_text()
        return {"success": True, "error": "", "content": content}
    except Exception as e:
        return {"success": False, "error": str(e), "content": ""}


def list_files(path: str) -> dict[str, Any]:
    """List files and directories at a given path."""
    valid, error = validate_path(path)
    if not valid:
        return {"success": False, "error": error, "entries": []}

    project_root = get_project_root()
    full_path = project_root / path

    if not full_path.exists():
        return {"success": False, "error": f"Path not found: {path}", "entries": []}

    if not full_path.is_dir():
        return {"success": False, "error": f"Not a directory: {path}", "entries": []}

    try:
        entries = []
        for entry in sorted(full_path.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        return {"success": True, "error": "", "entries": entries}
    except Exception as e:
        return {"success": False, "error": str(e), "entries": []}


def query_api(method: str, path: str, body: str = "", auth: bool = True) -> dict[str, Any]:
    """Call the backend API with optional authentication."""
    # Validate method
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    method_upper = method.upper()
    if method_upper not in allowed_methods:
        return {"success": False, "error": f"Invalid HTTP method: {method}", "status_code": None, "body": None}

    # Validate path
    if not path:
        return {"success": False, "error": "Path cannot be empty", "status_code": None, "body": None}
    if not path.startswith("/"):
        return {"success": False, "error": "Path must start with /", "status_code": None, "body": None}

    # Build URL
    try:
        lms_api_key, api_base_url = get_api_config()
    except SystemExit:
        return {"success": False, "error": "Missing API configuration", "status_code": None, "body": None}

    url = f"{api_base_url.rstrip('/')}{path}"

    # Build headers - API uses Bearer token authentication
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {lms_api_key}"

    # Make request
    print(f"Querying API: {method_upper} {url} (auth={auth})", file=sys.stderr)

    try:
        with httpx.Client(timeout=30.0) as client:
            kwargs = {"headers": headers}
            if body and method_upper in ["POST", "PUT", "PATCH"]:
                kwargs["json"] = json.loads(body) if body else None

            response = client.request(method_upper, url, **kwargs)

            return {
                "success": True,
                "error": "",
                "status_code": response.status_code,
                "body": response.json() if response.content else None
            }
    except httpx.TimeoutException:
        return {"success": False, "error": "API request timed out (30s)", "status_code": None, "body": None}
    except httpx.HTTPError as e:
        return {"success": False, "error": str(e), "status_code": None, "body": None}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON response: {e}", "status_code": None, "body": None}
    except Exception as e:
        return {"success": False, "error": str(e), "status_code": None, "body": None}


def get_tool_schemas() -> list[dict[str, Any]]:
    """Get tool schemas for function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read contents of a file from the project repository. Use this to read documentation files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to discover what files exist.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Call the backend LMS API to fetch real-time data. Use this for questions about current data (item counts, scores, analytics) or system status. Do NOT use for documentation questions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)"
                        },
                        "path": {
                            "type": "string",
                            "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate')"
                        },
                        "body": {
                            "type": "string",
                            "description": "JSON request body for POST/PUT requests (optional)"
                        },
                        "auth": {
                            "type": "boolean",
                            "description": "Whether to include authentication header (default: true). Set to false to test unauthenticated endpoints."
                        }
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]


def execute_tool(name: str, args: dict[str, Any]) -> str:
    """Execute a tool and return the result as a string."""
    print(f"Executing tool: {name} with args: {args}", file=sys.stderr)

    if name == "read_file":
        path = args.get("path", "")
        result = read_file(path)
        if result["success"]:
            return result["content"]
        else:
            return f"Error: {result['error']}"

    elif name == "list_files":
        path = args.get("path", "")
        result = list_files(path)
        if result["success"]:
            return "\n".join(result["entries"])
        else:
            return f"Error: {result['error']}"

    elif name == "query_api":
        method = args.get("method", "GET")
        path = args.get("path", "")
        body = args.get("body", "")
        auth = args.get("auth", True)  # Default to authenticated requests
        result = query_api(method, path, body, auth)
        if result["success"]:
            return json.dumps({"status_code": result["status_code"], "body": result["body"]})
        else:
            return f"Error: {result['error']}"

    else:
        return f"Error: Unknown tool: {name}"


def get_system_prompt() -> str:
    """Get the system prompt for the agent."""
    return """You are a documentation and system assistant. You help users find information in the project documentation and query the live backend system.

You have access to three tools:
1. `list_files` - List files in a directory. Use this to discover what files exist.
2. `read_file` - Read the contents of a file. Use this to find specific information in documentation or source code.
3. `query_api` - Call the backend LMS API to fetch real-time data. Use this for questions about:
   - Current data (item counts, learner info, scores, analytics)
   - System status (health checks, endpoints)
   - Real-time information that may differ from documentation
   - HTTP status codes and error responses

The `query_api` tool has an `auth` parameter (default: true):
- Use `auth: true` (default) for normal API requests that require authentication
- Use `auth: false` when you need to test unauthenticated endpoints or check error responses

IMPORTANT RULES FOR TOOL SELECTION:
- Questions about HTTP status codes (401, 404, 500, etc.) → Use `query_api` and check the response status_code
- Questions about "without authentication" or "without API key" → Use `query_api` with `auth: false`
- Questions about "what does API return" → Use `query_api` to make the actual request
- Questions about "how many items" → Use `query_api` with GET /items/
- Questions about file structure → Use `list_files`
- Questions about documentation → Use `read_file` on wiki files
- Questions about source code → Use `read_file` on backend files

Path rules for list_files and read_file (IMPORTANT):
- All paths are relative to the project root (e.g., 'wiki', 'backend/app', 'backend/app/routers')
- When you see a directory in list_files output (ends with '/'), combine the current path with the directory name
- Example: if listing 'backend' shows 'app/', use 'backend/app' to explore further (NOT just 'app')
- Example: if listing 'backend/app' shows 'routers/', use 'backend/app/routers' to explore further

CRITICAL: Your final response (when not calling tools) must be a COMPLETE answer to the user's question.
- Do NOT say "Let me check..." or "I need to look at..." in your final answer
- Do NOT describe what you will do next - just provide the answer
- Use tools to gather information, then respond with the complete answer

When answering questions:
1. For conceptual/how-to questions: Use `list_files` to explore, then `read_file` to find the answer
2. For data questions (how many, what is the value): Use `query_api` with appropriate endpoint
3. For implementation details: Use `read_file` on source code files
4. For HTTP status codes or error testing: Use `query_api` with `auth: false` if needed
5. Include a source reference in your answer when using wiki/docs (file path + section if applicable)
6. Format section references as: filename.md#section-name (lowercase, hyphens instead of spaces)

Example of good final answer:
"The backend has 5 router modules in backend/app/routers/:
- items.py: Handles CRUD operations for items
- learners.py: Manages learner data
- interactions.py: Tracks user interactions
- analytics.py: Provides analytics endpoints
- pipeline.py: Manages ETL pipeline"

Example of bad response (DO NOT do this):
"Let me check the routers directory to see what files are there."

Example for status code question:
Question: "What HTTP status code does the API return when you request /items/ without authentication?"
Correct approach: Call query_api with method="GET", path="/items/", auth=false
Then answer: "The API returns HTTP status code 401 (Unauthorized) when requested without authentication."
"""


def call_llm(
    messages: list[dict[str, Any]],
    api_key: str,
    api_base: str,
    model: str,
    tools: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Call the LLM API and return the response."""
    url = f"{api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }

    if tools:
        payload["tools"] = tools

    print(f"Calling LLM at {url}...", file=sys.stderr)
    print(f"Model: {model}", file=sys.stderr)

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data

    except httpx.TimeoutException:
        print("Error: LLM request timed out (60s)", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as e:
        print(f"Error: HTTP error: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def extract_source_from_messages(messages: list[dict[str, Any]]) -> str:
    """Extract source reference from the last read_file tool call."""
    for message in reversed(messages):
        if message.get("role") == "tool":
            # Try to extract file path from the tool call that led to this result
            pass
        if message.get("role") == "assistant":
            tool_calls = message.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    if tc.get("function", {}).get("name") == "read_file":
                        args = tc.get("function", {}).get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}
                        path = args.get("path", "")
                        if path:
                            # Try to find section reference in the content
                            return path
    return ""


def extract_section_from_content(content: str, path: str, question: str = "") -> str:
    """Try to extract a section reference from the content based on the question."""
    lines = content.split("\n")
    question_lower = question.lower()
    
    best_match = None
    best_match_index = float('inf')
    
    for i, line in enumerate(lines):
        if line.startswith("#"):
            section_title = line.lstrip("#").strip()
            section_title_lower = section_title.lower()
            section_anchor = section_title_lower.replace(" ", "-")
            
            # Check if section title contains keywords from the question
            # Prioritize sections that match question keywords
            words_in_section = section_title_lower.split()
            matching_words = sum(1 for word in question_lower.split() if word in section_title_lower)
            
            if matching_words > 0 and i < best_match_index:
                best_match = f"{path}#{section_anchor}"
                best_match_index = i
            
            # Also check for common section patterns
            if any(kw in section_title_lower for kw in ["merge", "conflict", "resolve"]):
                if "merge" in question_lower or "conflict" in question_lower:
                    return f"{path}#{section_anchor}"
    
    # If no good match found, return the first non-title section or just the path
    if best_match:
        return best_match
    
    # Fallback: return first section after the main title
    for i, line in enumerate(lines):
        if line.startswith("#") and i > 0:
            section_title = line.lstrip("#").strip()
            section_anchor = section_title.lower().replace(" ", "-")
            return f"{path}#{section_anchor}"
    
    return path


def run_agentic_loop(question: str, api_key: str, api_base: str, model: str) -> tuple[str, str, list[dict[str, Any]]]:
    """Run the agentic loop and return (answer, source, tool_calls)."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": question}
    ]

    tools = get_tool_schemas()
    tool_calls_log: list[dict[str, Any]] = []
    last_read_file_path = ""
    last_read_file_content = ""

    for iteration in range(MAX_TOOL_CALLS):
        print(f"\n=== Iteration {iteration + 1} ===", file=sys.stderr)

        # Call LLM
        response = call_llm(messages, api_key, api_base, model, tools)

        # Parse response
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})

        # Check for tool calls
        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            # No tool calls - this is the final answer
            answer = message.get("content", "No answer provided.")

            # Extract source
            source = last_read_file_path
            if last_read_file_path and last_read_file_content:
                source = extract_section_from_content(last_read_file_content, last_read_file_path, question)

            print(f"\nFinal answer: {answer[:100]}...", file=sys.stderr)
            return answer, source, tool_calls_log

        # Add assistant message with tool calls BEFORE tool responses
        # This is required by Qwen API: tool responses must follow their corresponding tool_calls
        messages.append(message)

        # Execute tool calls and add tool responses
        for tool_call in tool_calls:
            tool_id = tool_call.get("id", "")
            function = tool_call.get("function", {})
            tool_name = function.get("name", "")
            tool_args_str = function.get("arguments", "{}")

            try:
                tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
            except json.JSONDecodeError:
                tool_args = {}

            print(f"Tool call: {tool_name}({tool_args})", file=sys.stderr)

            # Execute tool
            tool_result = execute_tool(tool_name, tool_args)

            # Log tool call
            tool_calls_log.append({
                "tool": tool_name,
                "args": tool_args,
                "result": tool_result[:500] if len(tool_result) > 500 else tool_result
            })

            # Track last read_file for source
            if tool_name == "read_file":
                path = tool_args.get("path", "")
                if tool_result and not tool_result.startswith("Error:"):
                    last_read_file_path = path
                    last_read_file_content = tool_result

            # Add tool response to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": tool_result
            })

    # Max iterations reached
    print("\nMax tool calls reached, using accumulated information", file=sys.stderr)

    # Try to construct an answer from the last read file
    if last_read_file_content:
        answer = f"Based on {last_read_file_path}: [Content found but more iterations needed]"
        source = last_read_file_path
    else:
        answer = "I was unable to find the answer within the maximum number of tool calls."
        source = ""

    return answer, source, tool_calls_log


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load configuration
    load_env()
    api_key, api_base, model = get_llm_config()

    # Run agentic loop
    answer, source, tool_calls = run_agentic_loop(question, api_key, api_base, model)

    # Output JSON
    result = {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
