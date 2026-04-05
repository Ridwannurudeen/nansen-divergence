"""Tests for MCP tool handlers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_get_divergence_signals_returns_list():
    from nansen_divergence.mcp_tools import handle_get_divergence_signals
    result = handle_get_divergence_signals({})
    assert isinstance(result, list)


def test_get_divergence_signals_filters_by_phase():
    from nansen_divergence.mcp_tools import handle_get_divergence_signals
    result = handle_get_divergence_signals({"phase": "ACCUMULATION"})
    for item in result:
        assert item["phase"] == "ACCUMULATION"


def test_get_signal_performance_returns_stats():
    from nansen_divergence.mcp_tools import handle_get_signal_performance
    result = handle_get_signal_performance({})
    assert isinstance(result, dict)
    assert "win_rate" in result
    assert "total_signals" in result


def test_tool_definitions_have_required_fields():
    from nansen_divergence.mcp_tools import TOOL_DEFINITIONS
    assert len(TOOL_DEFINITIONS) == 2
    for tool in TOOL_DEFINITIONS:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
