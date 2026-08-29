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
            "create_rc_4wd_drivetrain_animation",
            "get_cad_status",
            "viewer_help",
            "get_cad_preview",
            "get_cad_views",
            "get_cad_model_source",
            "inspect_cad_geometry",
            "detect_cad_interference",
            "list_cad_components",
            "inspect_component_clearance",
            "show_cad_job",
            "list_cad_model_sources",
            "search_cad_model_sources",
        } <= names
        result = await client.call_tool("viewer_help", {})
        assert result.structured_content["result"].startswith("最終オブジェクト")
