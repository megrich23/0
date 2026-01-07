"""Base tool class and registry for agent tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Type, Callable
from datetime import datetime
from enum import Enum
import uuid


class ToolCategory(str, Enum):
    """Categories of tools available to agents."""
    RETRIEVAL = "retrieval"       # Knowledge base retrieval
    ANALYSIS = "analysis"         # Analysis and synthesis
    CREATION = "creation"         # Content creation
    MEMORY = "memory"             # Memory operations
    DISCUSSION = "discussion"     # Multi-agent collaboration


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    param_type: type
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any, **metadata) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata) -> "ToolResult":
        """Create a failed result."""
        return cls(success=False, data=None, error=error, metadata=metadata)


class BaseTool(ABC):
    """
    Base class for all tools.

    Tools are capabilities that agents can use to interact with
    external systems, retrieve information, or perform actions.
    """

    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.RETRIEVAL
    parameters: list[ToolParameter] = []

    def __init__(self, **dependencies):
        """
        Initialize the tool with dependencies.

        Args:
            **dependencies: Tool-specific dependencies (db session, providers, etc.)
        """
        self.dependencies = dependencies
        self._execution_count = 0
        self._total_execution_time_ms = 0.0

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult with data or error
        """
        pass

    def validate_args(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate tool arguments.

        Args:
            **kwargs: Arguments to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"

            if param.name in kwargs:
                value = kwargs[param.name]
                if not isinstance(value, param.param_type):
                    return False, f"Invalid type for {param.name}: expected {param.param_type.__name__}"

        return True, None

    async def __call__(self, **kwargs) -> ToolResult:
        """Execute the tool with timing and validation."""
        # Validate arguments
        is_valid, error = self.validate_args(**kwargs)
        if not is_valid:
            return ToolResult.fail(error)

        # Execute with timing
        start = datetime.utcnow()
        try:
            result = await self.execute(**kwargs)
        except Exception as e:
            result = ToolResult.fail(str(e))

        end = datetime.utcnow()
        execution_time = (end - start).total_seconds() * 1000
        result.execution_time_ms = execution_time

        # Update stats
        self._execution_count += 1
        self._total_execution_time_ms += execution_time

        return result

    def get_schema(self) -> dict:
        """Get the tool schema for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": self._type_to_json_type(p.param_type),
                        "description": p.description,
                    }
                    for p in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required]
            }
        }

    @staticmethod
    def _type_to_json_type(python_type: type) -> str:
        """Convert Python type to JSON schema type."""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        return type_map.get(python_type, "string")

    def __repr__(self) -> str:
        return f"<Tool {self.name} ({self.category.value})>"


class ToolRegistry:
    """Registry for managing available tools."""

    _instance: Optional["ToolRegistry"] = None
    _tools: dict[str, Type[BaseTool]] = {}
    _instances: dict[str, BaseTool] = {}

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, tool_class: Type[BaseTool]) -> Type[BaseTool]:
        """
        Register a tool class (decorator).

        Args:
            tool_class: Tool class to register

        Returns:
            The same tool class (for use as decorator)
        """
        cls._tools[tool_class.name] = tool_class
        return tool_class

    @classmethod
    def get_tool(cls, name: str, **dependencies) -> Optional[BaseTool]:
        """
        Get an instance of a tool.

        Args:
            name: Tool name
            **dependencies: Dependencies to inject

        Returns:
            Tool instance or None
        """
        # Check for existing instance
        cache_key = f"{name}_{hash(frozenset(dependencies.items()))}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]

        # Create new instance
        tool_class = cls._tools.get(name)
        if tool_class:
            instance = tool_class(**dependencies)
            cls._instances[cache_key] = instance
            return instance

        return None

    @classmethod
    def list_tools(cls, category: Optional[ToolCategory] = None) -> list[str]:
        """
        List available tools.

        Args:
            category: Optional category filter

        Returns:
            List of tool names
        """
        if category:
            return [
                name for name, tool in cls._tools.items()
                if tool.category == category
            ]
        return list(cls._tools.keys())

    @classmethod
    def get_schemas(cls, tool_names: list[str]) -> list[dict]:
        """
        Get schemas for multiple tools.

        Args:
            tool_names: List of tool names

        Returns:
            List of tool schemas
        """
        schemas = []
        for name in tool_names:
            tool_class = cls._tools.get(name)
            if tool_class:
                # Create temp instance to get schema
                temp = tool_class.__new__(tool_class)
                schemas.append(temp.get_schema())
        return schemas


# Decorator for registering tools
def register_tool(cls: Type[BaseTool]) -> Type[BaseTool]:
    """Decorator to register a tool class."""
    return ToolRegistry.register(cls)
