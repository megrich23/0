"""Base agent class and supporting types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
import uuid

from backend.core.providers import BaseProvider


class AgentRole(str, Enum):
    """Roles that agents can have."""
    PLANNER = "planner"
    RESEARCH = "research"
    WRITER = "writer"
    CRITIC = "critic"
    FACT_CHECKER = "fact_checker"
    CURATOR = "curator"
    TUTOR = "tutor"
    BRAINSTORMER = "brainstormer"


@dataclass
class ToolUse:
    """Record of a tool being used by an agent."""
    tool_name: str
    arguments: dict
    result: Any
    timestamp: str


@dataclass
class AgentContext:
    """
    Context provided to an agent for execution.

    Contains all the information an agent needs to perform its task.
    """
    task: str
    constraints: dict = field(default_factory=dict)
    artifacts: dict = field(default_factory=dict)
    allowed_tools: list[str] = field(default_factory=list)
    allowed_sources: list[str] = field(default_factory=list)
    strict_mode: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from an agent execution."""
    success: bool
    output: Any
    tool_uses: list[ToolUse] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    error: Optional[str] = None
    tokens_used: int = 0
    duration_seconds: float = 0.0


class BaseAgent(ABC):
    """
    Base class for all agents in the system.

    Each agent:
    - Has a specific role
    - Uses an LLM provider
    - Has access to specific tools
    - Operates within constraints
    - Produces traceable results
    """

    def __init__(
        self,
        role: AgentRole,
        provider: BaseProvider,
        system_prompt: str,
        tools: Optional[list] = None
    ):
        """
        Initialize the agent.

        Args:
            role: The agent's role
            provider: LLM provider to use
            system_prompt: Base system prompt for this agent
            tools: List of tools this agent can access
        """
        self.role = role
        self.provider = provider
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.execution_id: Optional[str] = None

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent's task.

        Args:
            context: Execution context with task and constraints

        Returns:
            Result of the execution
        """
        pass

    def validate_context(self, context: AgentContext) -> tuple[bool, Optional[str]]:
        """
        Validate that the context is appropriate for this agent.

        Args:
            context: Context to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if agent has required tools
        missing_tools = set(self.get_required_tools()) - set(context.allowed_tools)
        if missing_tools:
            return False, f"Missing required tools: {missing_tools}"

        # Strict mode validation
        if context.strict_mode and not context.allowed_sources:
            if self.requires_sources():
                return False, "Strict mode requires allowed_sources to be specified"

        return True, None

    def get_required_tools(self) -> list[str]:
        """
        Get list of tools required by this agent.

        Returns:
            List of required tool names
        """
        return []

    def requires_sources(self) -> bool:
        """
        Check if this agent requires source documents.

        Returns:
            True if sources are required
        """
        return False

    async def _call_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Call the LLM provider.

        Args:
            prompt: User prompt
            system: System prompt override
            **kwargs: Additional arguments for generation

        Returns:
            Generated text
        """
        from backend.core.providers import GenerationRequest

        request = GenerationRequest(
            prompt=prompt,
            system=system or self.system_prompt,
            **kwargs
        )

        response = await self.provider.generate(request)
        return response.text

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self.role} provider={self.provider.config.model}>"


class AgentError(Exception):
    """Base exception for agent errors."""

    def __init__(self, message: str, agent: str, context: Optional[dict] = None):
        self.message = message
        self.agent = agent
        self.context = context or {}
        super().__init__(self.message)


class ValidationError(AgentError):
    """Raised when agent context validation fails."""
    pass


class ExecutionError(AgentError):
    """Raised when agent execution fails."""
    pass
