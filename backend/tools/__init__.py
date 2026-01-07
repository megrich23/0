"""Tools for agent capabilities.

This module provides tools that agents can use to interact with
external systems, retrieve information, and perform actions.

Tool Categories:
- RETRIEVAL: Knowledge base retrieval (semantic_search, get_passage)
- MEMORY: Memory operations (get_notes, get_concepts)
- ANALYSIS: Analysis and synthesis (brainstorm, find_idea_connections)
- CREATION: Content creation
- DISCUSSION: Multi-agent collaboration
"""

from .base import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ToolCategory,
    ToolRegistry,
    register_tool,
)

from .semantic_search import (
    SemanticSearchTool,
    GetPassageTool,
    GetNotesTool,
    GetConceptsTool,
    SearchResult,
)

from .brainstorming import (
    BrainstormingTool,
    BrainstormingMode,
    BrainstormIdea,
    BrainstormSession,
    IdeaConnectionTool,
)


__all__ = [
    # Base
    "BaseTool",
    "ToolResult",
    "ToolParameter",
    "ToolCategory",
    "ToolRegistry",
    "register_tool",
    # Semantic Search
    "SemanticSearchTool",
    "GetPassageTool",
    "GetNotesTool",
    "GetConceptsTool",
    "SearchResult",
    # Brainstorming
    "BrainstormingTool",
    "BrainstormingMode",
    "BrainstormIdea",
    "BrainstormSession",
    "IdeaConnectionTool",
]


def get_tool(name: str, **dependencies) -> BaseTool | None:
    """
    Get a tool instance by name.

    Args:
        name: Tool name
        **dependencies: Dependencies to inject (db_session, providers, etc.)

    Returns:
        Tool instance or None if not found
    """
    return ToolRegistry.get_tool(name, **dependencies)


def list_tools(category: ToolCategory | None = None) -> list[str]:
    """
    List available tools.

    Args:
        category: Optional category filter

    Returns:
        List of tool names
    """
    return ToolRegistry.list_tools(category)


def get_tool_schemas(tool_names: list[str]) -> list[dict]:
    """
    Get JSON schemas for tools (for LLM function calling).

    Args:
        tool_names: List of tool names

    Returns:
        List of tool schemas
    """
    return ToolRegistry.get_schemas(tool_names)
