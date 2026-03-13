"""
Regression tests for agent.py

These tests verify that the agent outputs valid JSON with the required fields.
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
        timeout=60,
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

    def test_agent_has_tool_calls_field(self):
        """Test that agent output has 'tool_calls' field."""
        stdout, stderr, returncode = run_agent("Explain what REST is.")

        assert returncode == 0, f"Agent failed: {stderr}"
        output = json.loads(stdout)

        assert "tool_calls" in output, "Missing 'tool_calls' field in output"
        assert isinstance(output["tool_calls"], list), "'tool_calls' should be an array"

    def test_agent_response_is_not_empty(self):
        """Test that agent provides a non-empty answer."""
        stdout, stderr, returncode = run_agent("What is the capital of France?")

        assert returncode == 0, f"Agent failed: {stderr}"
        output = json.loads(stdout)

        assert output.get("answer"), "Answer should not be empty"
        # Basic sanity check - should mention Paris
        assert "paris" in output["answer"].lower(), f"Expected 'Paris' in answer, got: {output['answer']}"
