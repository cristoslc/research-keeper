from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestMCPToolDefinitions:
    """Test that MCP tool definitions are correctly structured."""

    def test_tool_definitions_exist(self):
        from research_keeper.mcp_server import TOOL_DEFINITIONS

        expected_tools = {
            "rk_add",
            "rk_search",
            "rk_keyword_search",
            "rk_tags",
            "rk_investigate",
            "rk_rebuild",
            "rk_status",
        }
        tool_names = {t["name"] for t in TOOL_DEFINITIONS}
        assert expected_tools == tool_names

    def test_each_tool_has_description(self):
        from research_keeper.mcp_server import TOOL_DEFINITIONS

        for tool in TOOL_DEFINITIONS:
            assert "description" in tool
            assert len(tool["description"]) > 10

    def test_each_tool_has_input_schema(self):
        from research_keeper.mcp_server import TOOL_DEFINITIONS

        for tool in TOOL_DEFINITIONS:
            assert "inputSchema" in tool
            assert "type" in tool["inputSchema"]


class TestMCPToolHandlers:
    """Test tool handler dispatch."""

    def test_handle_rk_status(self, tmp_path: Path):
        from research_keeper.mcp_server import handle_tool_call

        # Mock the necessary components
        result = handle_tool_call("rk_status", {"root": str(tmp_path)})
        assert result is not None
        assert isinstance(result, str)

    def test_handle_unknown_tool(self):
        from research_keeper.mcp_server import handle_tool_call

        with pytest.raises(ValueError, match="Unknown tool"):
            handle_tool_call("rk_nonexistent", {})
