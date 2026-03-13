#!/usr/bin/env python3
"""
Agent CLI - Call an LLM from code.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "tool_calls": []}
    All debug output goes to stderr.
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def load_env():
    """Load environment variables from .env.agent.secret."""
    env_path = Path(__file__).parent / ".env.agent.secret"
    if not env_path.exists():
        print(f"Error: {env_path} not found", file=sys.stderr)
        sys.exit(1)
    load_dotenv(env_path)


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


def call_llm(question: str, api_key: str, api_base: str, model: str) -> str:
    """Call the LLM API and return the answer."""
    url = f"{api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer questions concisely and accurately.",
            },
            {"role": "user", "content": question},
        ],
    }

    print(f"Calling LLM at {url}...", file=sys.stderr)
    print(f"Model: {model}", file=sys.stderr)
    print(f"Question: {question}", file=sys.stderr)

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            answer = data["choices"][0]["message"]["content"]
            print(f"LLM response received", file=sys.stderr)
            return answer

    except httpx.TimeoutException:
        print("Error: LLM request timed out (60s)", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as e:
        print(f"Error: HTTP error: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, IndexError) as e:
        print(f"Error: Unexpected LLM response format: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load configuration
    load_env()
    api_key, api_base, model = get_llm_config()

    # Call LLM
    answer = call_llm(question, api_key, api_base, model)

    # Output JSON
    result = {"answer": answer, "tool_calls": []}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
