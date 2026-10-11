import logging
from typing import Any

from app.services.intelligence.tools.base import Tool
from app.services.intelligence.tools.dna_lookup import dna_lookup_tool
from app.services.intelligence.tools.relationships_lookup import relationships_lookup_tool
from app.services.intelligence.tools.semantic_search import semantic_search_tool
from app.services.intelligence.tools.source_lookup import source_lookup_tool
from app.services.intelligence.tools.trends_lookup import trends_lookup_tool

logger = logging.getLogger("app.intelligence.tools")

ALL_TOOLS: list[Tool] = [
    semantic_search_tool,
    dna_lookup_tool,
    relationships_lookup_tool,
    trends_lookup_tool,
    source_lookup_tool,
]

TOOLS_BY_NAME: dict[str, Tool] = {tool.name: tool for tool in ALL_TOOLS}


def get_tool_specs() -> list[dict[str, Any]]:
    return [tool.spec() for tool in ALL_TOOLS]


async def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        logger.warning("Agent requested unknown tool '%s'", name)
        return {"error": f"Unknown tool: {name}"}

    try:
        return await tool.handler(arguments)
    except Exception as exc:  # a broken tool must never crash the agent loop
        logger.exception("Tool '%s' raised an exception", name)
        return {"error": f"Tool '{name}' failed: {exc}"}
