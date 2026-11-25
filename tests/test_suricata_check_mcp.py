"""Tests for the suricata-check MCP server."""

import re
import sys
import unittest.mock
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError
from suricata_check.utils.checker_typing import (
    Issue,
    OutputReport,
    OutputSummary,
    RuleReport,
)
from suricata_check.utils.rule import parse

import suricata_check_mcp

TEST_RULE_VALID = (
    "alert tcp $HOME_NET any -> $EXTERNAL_NET $HTTP_PORTS "
    '(msg:"Test HTTP rule"; flow:established,to_server; content:"GET"; '
    "http_method; sid:12345; rev:1;)"
)
TESTS_INVALID = (
    "",  # Empty string
    "   ",  # Whitespace only
)


@pytest.mark.parametrize("invalid_rule", TESTS_INVALID)
def test_analyze_rule_invalid_inputs(invalid_rule: str) -> None:
    """Ensure the function raises a ValueError for empty or non-string inputs."""
    with pytest.raises(
        ValueError,
        match=r".*invalid.*",
    ):
        suricata_check_mcp.analyze_rule(invalid_rule)


def test_analyze_rule_parse_failure() -> None:
    """Ensure the function raises a ValueError with an actionable message on parse failure."""
    rule_str = "this is definitely not a valid suricata rule"

    with pytest.raises(ValueError, match=r".*Failed to parse.*rule.*"):
        suricata_check_mcp.analyze_rule(rule_str)


def test_analyze_rule() -> None:
    """Ensure a valid rule is successfully parsed and analyzed by the actual library."""
    result = suricata_check_mcp.analyze_rule(TEST_RULE_VALID)
    assert isinstance(result, dict)


@pytest.mark.parametrize("tool_name", ["analyze_rule", "process_rules_file"])
def test_invalid_regex_arguments(tool_name: str) -> None:
    """Ensure invalid include and exclude regexes raise a ValueError naming the pattern."""
    tool = getattr(suricata_check_mcp, tool_name)
    with pytest.raises(ValueError, match=r".*Invalid include regular expression: \[.*"):
        tool(TEST_RULE_VALID, include=["["])
    with pytest.raises(ValueError, match=r".*Invalid exclude regular expression: \[.*"):
        tool(TEST_RULE_VALID, exclude=["["])


@pytest_asyncio.fixture
async def mcp_client() -> AsyncIterator[Client]:
    """Spins up the FastMCP server and attaches a test client.

    This fires up the server, completes the formal protocol initialization,
    and handles automatic teardown after the test finishes.
    """
    async with Client(suricata_check_mcp.mcp) as client:
        yield client


@pytest.mark.asyncio
async def test_server_tools(mcp_client: Client) -> None:
    """Verifies that the server boots up properly and registers the tools over MCP."""
    tools = await mcp_client.list_tools()

    assert len(tools) > 0
    assert any(tool.name == "analyze_rule" for tool in tools)
    assert any(tool.name == "process_rules_file" for tool in tools)
    assert any(tool.name == "list_checkers" for tool in tools)


@pytest.mark.parametrize("invalid_rule", TESTS_INVALID)
@pytest.mark.asyncio
async def test_server_analyze_rule_invalid(
    mcp_client: Client,
    invalid_rule: str,
) -> None:
    """Verifies executing the tool end-to-end through the running server transport."""
    with pytest.raises(
        ToolError,
        match=r".*invalid.*",
    ):
        await mcp_client.call_tool(
            "analyze_rule",
            arguments={"rule": invalid_rule},
        )


@pytest.mark.asyncio
async def test_server_analyze_rule(mcp_client: Client) -> None:
    """Verifies executing the tool end-to-end through the running server transport."""
    result = await mcp_client.call_tool(
        "analyze_rule",
        arguments={"rule": TEST_RULE_VALID},
    )

    # Verify the server handled the request without crashing and returned data
    assert result is not None


@pytest.mark.asyncio
async def test_server_analyze_rule_invalid_include(mcp_client: Client) -> None:
    """Verifies that invalid include regexes surface as a ToolError over MCP."""
    with pytest.raises(ToolError, match=r".*Invalid include regular expression.*"):
        await mcp_client.call_tool(
            "analyze_rule",
            arguments={"rule": TEST_RULE_VALID, "include": ["["]},
        )


@pytest.mark.asyncio
async def test_server_list_checkers(mcp_client: Client) -> None:
    """Verifies that the list_checkers tool returns real checker data over MCP."""
    result = await mcp_client.call_tool("list_checkers", {})

    # Use the structured content rather than `result.data`: the typed data object is
    # deserialized differently across fastmcp versions (e.g., 3.0.0 returns an opaque `Root`).
    assert result.structured_content is not None
    checkers = result.structured_content["checkers"]
    names = [checker["name"] for checker in checkers]
    assert "MandatoryChecker" in names
    assert all(
        re.fullmatch(r"[A-Z]{1,}[0-9]{3}", code)
        for checker in checkers
        for code in checker["codes"]
    )


def test_list_checkers() -> None:
    """Ensure available checkers from the core are listed with their issue codes."""
    output = suricata_check_mcp.list_checkers()

    assert len(output.checkers) > 0
    mandatory = next(
        checker for checker in output.checkers if checker.name == "MandatoryChecker"
    )
    assert mandatory.enabled_by_default is True
    assert len(mandatory.codes) > 0
    assert all(re.fullmatch(r"[A-Z]{1,}[0-9]{3}", code) for code in mandatory.codes)


@pytest.mark.asyncio
async def test_server_instructions(mcp_client: Client) -> None:
    """Verifies that the server describes its workflow to clients through its instructions."""
    # fastmcp 3.0.x exposes the initialization result, whereas newer versions expose `instructions`.
    initialize_result = mcp_client.initialize_result
    instructions = (
        initialize_result.instructions
        if initialize_result is not None
        else getattr(mcp_client, "instructions", None)
    )
    assert instructions == suricata_check_mcp.mcp.instructions
    assert instructions is not None
    for tool_name in ("analyze_rule", "process_rules_file", "list_checkers"):
        assert tool_name in instructions


def test_process_rules_file(tmp_path: Path) -> None:
    """Ensure the per-rule reports of the core are mapped into the result."""
    # Create a dummy rules file
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text("rule test { pass { }\n}")

    # Mock process_rules_file to return a controlled OutputReport
    parsed_rule = parse(TEST_RULE_VALID)
    assert parsed_rule is not None
    rule_report = RuleReport(rule=parsed_rule, line_begin=2, line_end=2)
    rule_report.add_issue(
        Issue(code="C100", message="Test issue.", checker="BestChecker"),
    )

    mock_summary = OutputSummary(
        overall_summary={
            "Total Issues": 1,
            "Suppressed Issues": 0,
            "Rules with Issues": 1,
            "Rules without Issues": 0,
        },
        issues_by_group={"test_checker": 1},
        issues_by_type={"test_checker": {"test_code": 1}},
    )
    mock_output = OutputReport(rules=[rule_report], summary=mock_summary)

    with unittest.mock.patch(
        "suricata_check.process_rules_file",
        return_value=mock_output,
    ) as mock_proc:
        result = suricata_check_mcp.process_rules_file(str(rules_file))

    expected_report = {
        "rule": parsed_rule.raw,
        "lines": {"begin": 2, "end": 2},
        "issues": [
            {"code": "C100", "message": "Test issue.", "checker": "BestChecker"},
        ],
    }
    assert result["rules"] == [expected_report]
    assert result["summary"] == mock_summary.to_dict()
    assert result["issues_by_group"] == mock_summary.issues_by_group
    assert result["issues_by_type"] == mock_summary.issues_by_type
    mock_proc.assert_called_once()


VALID_RULES_FILE = Path(__file__).parent / "data" / "valid.rules"


def test_process_rules_file_real() -> None:
    """Ensure a real rules file is processed end-to-end by the actual library without mocking."""
    result = suricata_check_mcp.process_rules_file(str(VALID_RULES_FILE))

    assert len(result["rules"]) == 1
    assert result["rules"][0]["lines"] == {"begin": 1, "end": 1}
    assert result["summary"] is not None
    assert set(result["summary"]) == {
        "overall_summary",
        "issues_by_group",
        "issues_by_type",
    }
    assert result["issues_by_group"] == result["summary"]["issues_by_group"]


@pytest.mark.asyncio
async def test_stdio_server_end_to_end() -> None:
    """Verifies the server works when launched as a subprocess over the stdio transport.

    Unlike the in-memory client used by the other tests, this exercises the actual entry
    point, including the startup import of extensions, which prevents tool calls from
    hanging on Windows when an extension imports native modules on a worker thread.
    """
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "suricata_check_mcp"],
        cwd=str(Path(__file__).parent.parent),
    )
    async with Client(transport, timeout=120) as client:
        tools = await client.list_tools()
        assert {"analyze_rule", "list_checkers", "process_rules_file"} <= {
            tool.name for tool in tools
        }

        analyze_result = await client.call_tool(
            "analyze_rule",
            arguments={"rule": TEST_RULE_VALID},
        )
        assert analyze_result.is_error is False

        process_result = await client.call_tool(
            "process_rules_file",
            arguments={"rules": str(VALID_RULES_FILE)},
        )
        assert process_result.is_error is False
        assert process_result.structured_content is not None
        assert len(process_result.structured_content["rules"]) == 1
