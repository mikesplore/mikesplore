from bot.app.assembly_voice import ASSEMBLY_AGENT_URL, assembly_tools


def test_assembly_agent_endpoint_and_flat_tool_schema():
    assert ASSEMBLY_AGENT_URL == "wss://agents.assemblyai.com/v1/ws"
    tools = assembly_tools()
    assert tools
    assert all(tool["type"] == "function" for tool in tools)
    assert all("name" in tool and "parameters" in tool for tool in tools)
    assert all("function" not in tool for tool in tools)


def test_assembly_tools_include_verified_portfolio_capabilities():
    names = {tool["name"] for tool in assembly_tools()}
    assert {"get_profile", "list_entries", "list_public_assets"}.issubset(names)
    assert not {"create_admin_operation", "request_upload"}.intersection(names)
