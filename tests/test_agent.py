"""
Regression tests for agent.py

These tests verify that the agent outputs valid JSON with the required fields
and uses tools correctly.
"""

import json
import subprocess
import sys
from pathlib import Path


def get_agent_path():
    """Get the path to agent.py."""
    return Path(__file__).parent.parent / "agent.py"


def run_agent(question: str) -> tuple[str, str, int]:
    """Run the agent and return stdout, stderr, and return code."""
    agent_path = get_agent_path()
    result = subprocess.run(
        [sys.executable, str(agent_path), question],
        capture_output=True,
        text=True,
        timeout=120,
        env={**subprocess.os.environ, "PYTHONPATH": str(Path(__file__).parent.parent)},
    )
    return result.stdout, result.stderr, result.returncode


class TestAgentOutput:
    """Tests for agent output format."""

    def test_agent_outputs_valid_json(self):
        """Test that agent outputs valid JSON."""
        stdout, stderr, returncode = run_agent("What is 2+2?")

        # Should exit with code 0
        assert returncode == 0, f"Agent failed: {stderr}"

        # Should output valid JSON
        try:
            output = json.loads(stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON output: {e}\nStdout: {stdout}\nStderr: {stderr}")

        assert isinstance(output, dict), "Output should be a JSON object"

    def test_agent_has_answer_field(self):
        """Test that agent output has 'answer' field."""
        stdout, stderr, returncode = run_agent("What does API stand for?")

        assert returncode == 0, f"Agent failed: {stderr}"
        output = json.loads(stdout)

        assert "answer" in output, "Missing 'answer' field in output"
        assert isinstance(output["answer"], str), "'answer' should be a string"
        assert len(output["answer"]) > 0, "'answer' should not be empty"

    def test_agent_has_source_field(self):
        """Test that agent output has 'source' field."""
        stdout, stderr, returncode = run_agent("Explain what REST is.")

        assert returncode == 0, f"Agent failed: {stderr}"
        output = json.loads(stdout)

        assert "source" in output, "Missing 'source' field in output"
        assert isinstance(output["source"], str), "'source' should be a string"

    def test_agent_has_tool_calls_field(self):
        """Test that agent output has 'tool_calls' field."""
        stdout, stderr, returncode = run_agent("Explain what REST is.")

        assert returncode == 0, f"Agent failed: {stderr}"
        output = json.loads(stdout)

        assert "tool_calls" in output, "Missing 'tool_calls' field in output"
        assert isinstance(output["tool_calls"], list), "'tool_calls' should be an array"


class TestDocumentationAgent:
    """Tests for documentation agent tool usage."""

    def test_agent_uses_read_file_for_merge_conflict(self):
        """Test that agent uses read_file tool for merge conflict question."""
        stdout, stderr, returncode = run_agent("How do you resolve a merge conflict?")

        assert returncode == 0, f"Agent failed: {stderr}"
        output = json.loads(stdout)

        # Should have tool calls
        assert len(output.get("tool_calls", [])) > 0, "Expected tool calls for documentation question"

        # Should use read_file
        tool_names = [tc.get("tool") for tc in output["tool_calls"]]
        assert "read_file" in tool_names, f"Expected 'read_file' in tool calls, got: {tool_names}"

        # Source should reference a git-related file (git.md or git-vscode.md)
        source = output.get("source", "")
        assert "git" in source.lower(), f"Expected 'git' in source, got: {source}"

    def test_agent_uses_list_files_for_wiki_question(self):
        """Test that agent uses list_files tool for wiki exploration."""
        stdout, stderr, returncode = run_agent("What files are in the wiki directory?")

        assert returncode == 0, f"Agent failed: {stderr}"
        output = json.loads(stdout)

        # Should have tool calls
        assert len(output.get("tool_calls", [])) > 0, "Expected tool calls for wiki question"

        # Should use list_files
        tool_names = [tc.get("tool") for tc in output["tool_calls"]]
        assert "list_files" in tool_names, f"Expected 'list_files' in tool calls, got: {tool_names}"
