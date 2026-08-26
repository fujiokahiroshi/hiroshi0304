import pytest
from mcp import Client

from cad_workbench.server import mcp


@pytest.mark.anyio
async def test_mcp_lists_and_calls_tools() -> None:
    async with Client(mcp) as client:
        listing = await client.list_tools()
        names = {tool.name for tool in listing.tools}
        assert {
            "create_cad_model",
            "create_bevel_gear_animation",
            "create_differential_animation",
            "create_gear_animation",
            "get_cad_status",
            "viewer_help",
        } <= names
        result = await client.call_tool("viewer_help", {})
        assert result.structured_content["result"].startswith("最終オブジェクト")
