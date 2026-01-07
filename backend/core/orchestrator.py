"""Orchestrator for coordinating multi-agent workflows."""

import asyncio
import uuid
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from backend.agents.base import (
    BaseAgent,
    AgentContext,
    AgentResult,
    AgentRole,
    ValidationError,
    ExecutionError
)
from backend.core.providers import ProviderFactory


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    step_id: str
    agent_role: AgentRole
    task: str
    constraints: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)  # step_ids this depends on
    status: str = "pending"
    result: Optional[AgentResult] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowDefinition:
    """Definition of a workflow."""
    workflow_id: str
    name: str
    description: str
    steps: list[WorkflowStep]
    global_constraints: dict = field(default_factory=dict)
    allowed_sources: list[str] = field(default_factory=list)
    strict_mode: bool = True


@dataclass
class WorkflowExecution:
    """State of a workflow execution."""
    execution_id: str
    workflow: WorkflowDefinition
    status: WorkflowStatus
    current_step: Optional[str] = None
    artifacts: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Orchestrator:
    """
    Orchestrator coordinates multi-agent workflows.

    Responsibilities:
    - Breaking tasks into steps
    - Assigning agents to steps
    - Managing dependencies
    - Collecting and passing artifacts
    - Handling errors and retries
    - Validating constraints
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self.executions: dict[str, WorkflowExecution] = {}
        self.agents: dict[AgentRole, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent for use in workflows.

        Args:
            agent: Agent to register
        """
        self.agents[agent.role] = agent

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        context: Optional[dict] = None
    ) -> WorkflowExecution:
        """
        Execute a workflow.

        Args:
            workflow: Workflow definition to execute
            context: Additional context for the workflow

        Returns:
            Completed workflow execution

        Raises:
            ExecutionError: If workflow execution fails
        """
        execution = WorkflowExecution(
            execution_id=str(uuid.uuid4()),
            workflow=workflow,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.utcnow(),
            artifacts=context or {}
        )

        self.executions[execution.execution_id] = execution

        try:
            # Execute steps in dependency order
            await self._execute_steps(execution)

            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.errors.append(str(e))
            execution.completed_at = datetime.utcnow()
            raise ExecutionError(f"Workflow failed: {e}", "orchestrator", {"execution_id": execution.execution_id})

        return execution

    async def _execute_steps(self, execution: WorkflowExecution) -> None:
        """
        Execute workflow steps in dependency order.

        Args:
            execution: Workflow execution to process
        """
        workflow = execution.workflow
        completed_steps = set()

        while len(completed_steps) < len(workflow.steps):
            # Find steps that are ready to execute
            ready_steps = [
                step for step in workflow.steps
                if step.step_id not in completed_steps
                and all(dep in completed_steps for dep in step.dependencies)
                and step.status == "pending"
            ]

            if not ready_steps:
                # Check if we're stuck (circular dependencies or all failed)
                remaining = len(workflow.steps) - len(completed_steps)
                if remaining > 0:
                    raise ExecutionError(
                        f"Workflow stuck: {remaining} steps remaining but none ready",
                        "orchestrator"
                    )
                break

            # Execute ready steps in parallel
            tasks = [
                self._execute_step(step, execution)
                for step in ready_steps
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for step, result in zip(ready_steps, results):
                if isinstance(result, Exception):
                    step.status = "failed"
                    execution.errors.append(f"Step {step.step_id} failed: {result}")
                    raise result
                else:
                    completed_steps.add(step.step_id)

    async def _execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution
    ) -> AgentResult:
        """
        Execute a single workflow step.

        Args:
            step: Step to execute
            execution: Workflow execution context

        Returns:
            Agent result
        """
        # Get the appropriate agent
        agent = self.agents.get(step.agent_role)
        if not agent:
            raise ExecutionError(
                f"No agent registered for role: {step.agent_role}",
                "orchestrator"
            )

        # Build agent context
        context = AgentContext(
            task=step.task,
            constraints={
                **execution.workflow.global_constraints,
                **step.constraints
            },
            artifacts=execution.artifacts,
            allowed_sources=execution.workflow.allowed_sources,
            strict_mode=execution.workflow.strict_mode
        )

        # Validate context
        is_valid, error = agent.validate_context(context)
        if not is_valid:
            raise ValidationError(error, agent.__class__.__name__)

        # Execute
        step.status = "running"
        step.started_at = datetime.utcnow()
        execution.current_step = step.step_id

        try:
            result = await agent.execute(context)

            step.result = result
            step.status = "completed" if result.success else "failed"
            step.completed_at = datetime.utcnow()

            # Store artifacts
            if result.success and result.output:
                execution.artifacts[step.step_id] = result.output

            return result

        except Exception as e:
            step.status = "failed"
            step.completed_at = datetime.utcnow()
            raise ExecutionError(f"Step execution failed: {e}", agent.__class__.__name__)

    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """
        Get the status of a workflow execution.

        Args:
            execution_id: ID of the execution

        Returns:
            Workflow execution if found
        """
        return self.executions.get(execution_id)

    def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a running workflow execution.

        Args:
            execution_id: ID of the execution to cancel

        Returns:
            True if cancelled, False if not found or already completed
        """
        execution = self.executions.get(execution_id)
        if not execution or execution.status not in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
            return False

        execution.status = WorkflowStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        return True


# Pre-defined workflow templates

def create_essay_workflow(
    prompt: str,
    constraints: dict,
    allowed_sources: list[str],
    strict_mode: bool = True
) -> WorkflowDefinition:
    """
    Create a workflow for essay generation.

    Args:
        prompt: Essay prompt
        constraints: Constraints (wordcount, tone, etc.)
        allowed_sources: List of allowed source IDs
        strict_mode: Whether to operate in strict source-only mode

    Returns:
        Workflow definition
    """
    workflow_id = str(uuid.uuid4())

    steps = [
        WorkflowStep(
            step_id="plan",
            agent_role=AgentRole.PLANNER,
            task=f"Create an outline for: {prompt}",
            constraints=constraints
        ),
        WorkflowStep(
            step_id="research",
            agent_role=AgentRole.RESEARCH,
            task="Find evidence for each section of the outline",
            dependencies=["plan"]
        ),
        WorkflowStep(
            step_id="draft",
            agent_role=AgentRole.WRITER,
            task="Write the essay draft based on outline and evidence",
            dependencies=["plan", "research"],
            constraints=constraints
        ),
        WorkflowStep(
            step_id="critique_structure",
            agent_role=AgentRole.CRITIC,
            task="Critique the structural quality of the draft",
            dependencies=["draft"]
        ),
        WorkflowStep(
            step_id="critique_style",
            agent_role=AgentRole.CRITIC,
            task="Critique the style and voice of the draft",
            dependencies=["draft"]
        ),
        WorkflowStep(
            step_id="revise",
            agent_role=AgentRole.WRITER,
            task="Revise the draft based on critique",
            dependencies=["draft", "critique_structure", "critique_style"],
            constraints=constraints
        ),
        WorkflowStep(
            step_id="fact_check",
            agent_role=AgentRole.FACT_CHECKER,
            task="Verify citations and check for unsupported claims",
            dependencies=["revise"]
        ),
    ]

    return WorkflowDefinition(
        workflow_id=workflow_id,
        name="Essay Generation",
        description=f"Generate essay: {prompt[:100]}...",
        steps=steps,
        global_constraints=constraints,
        allowed_sources=allowed_sources,
        strict_mode=strict_mode
    )


def create_philosophy_reading_workflow(
    doc_id: str,
    depth: str = "detailed"
) -> WorkflowDefinition:
    """
    Create a workflow for philosophy text absorption.

    Args:
        doc_id: Document ID to process
        depth: Depth of analysis (quick, medium, detailed)

    Returns:
        Workflow definition
    """
    workflow_id = str(uuid.uuid4())

    steps = [
        WorkflowStep(
            step_id="summarize",
            agent_role=AgentRole.TUTOR,
            task=f"Create layered summaries of document {doc_id}",
            constraints={"depth": depth}
        ),
        WorkflowStep(
            step_id="extract_arguments",
            agent_role=AgentRole.TUTOR,
            task="Extract key arguments and premises",
            dependencies=["summarize"]
        ),
        WorkflowStep(
            step_id="find_objections",
            agent_role=AgentRole.TUTOR,
            task="Generate potential objections and critiques",
            dependencies=["extract_arguments"]
        ),
        WorkflowStep(
            step_id="create_notes",
            agent_role=AgentRole.TUTOR,
            task="Create atomic notes (zettels) for key concepts",
            dependencies=["summarize", "extract_arguments"]
        ),
        WorkflowStep(
            step_id="generate_flashcards",
            agent_role=AgentRole.TUTOR,
            task="Generate recall prompts and flashcards",
            dependencies=["summarize", "extract_arguments", "find_objections"]
        ),
    ]

    return WorkflowDefinition(
        workflow_id=workflow_id,
        name="Philosophy Reading",
        description=f"Process philosophy document {doc_id}",
        steps=steps,
        global_constraints={"depth": depth},
        allowed_sources=[doc_id],
        strict_mode=True
    )


def create_brainstorming_workflow(
    topic: str,
    mode: str = "explore",
    constraints: dict = None,
    include_critique: bool = True,
    include_research: bool = True,
) -> WorkflowDefinition:
    """
    Create a workflow for brainstorming with multi-agent collaboration.

    This workflow:
    1. Brainstorms initial ideas from knowledge base and memory
    2. Optionally researches to find supporting evidence
    3. Optionally critiques ideas for weaknesses
    4. Synthesizes final ideas with connections

    Args:
        topic: Topic to brainstorm
        mode: Brainstorming mode (explore, synthesize, challenge, analogize, elaborate)
        constraints: Additional constraints (depth, sources, perspectives)
        include_critique: Whether to include critique step
        include_research: Whether to include research step

    Returns:
        Workflow definition
    """
    workflow_id = str(uuid.uuid4())
    constraints = constraints or {}

    steps = [
        # Initial brainstorming
        WorkflowStep(
            step_id="brainstorm_initial",
            agent_role=AgentRole.BRAINSTORMER,
            task=f"Brainstorm ideas on: {topic}",
            constraints={
                "mode": mode,
                "depth": constraints.get("depth", 2),
                "sources": constraints.get("sources", ["philosophy", "culture", "notes", "concepts"]),
            }
        ),
    ]

    # Optional research step
    if include_research:
        steps.append(
            WorkflowStep(
                step_id="research_evidence",
                agent_role=AgentRole.RESEARCH,
                task="Find evidence and sources to support or challenge the brainstormed ideas",
                dependencies=["brainstorm_initial"],
                constraints={"focus_on_ideas": True}
            )
        )

    # Optional critique step
    if include_critique:
        critique_deps = ["brainstorm_initial"]
        if include_research:
            critique_deps.append("research_evidence")

        steps.append(
            WorkflowStep(
                step_id="critique_ideas",
                agent_role=AgentRole.CRITIC,
                task="Critique the brainstormed ideas: identify strengths, weaknesses, and gaps",
                dependencies=critique_deps,
                constraints={"critique_type": "brainstorm"}
            )
        )

    # Final synthesis
    synthesis_deps = ["brainstorm_initial"]
    if include_research:
        synthesis_deps.append("research_evidence")
    if include_critique:
        synthesis_deps.append("critique_ideas")

    steps.append(
        WorkflowStep(
            step_id="synthesize_final",
            agent_role=AgentRole.BRAINSTORMER,
            task="Synthesize final ideas incorporating research and critique feedback",
            dependencies=synthesis_deps,
            constraints={
                "mode": "synthesize",
                "depth": 3,
            }
        )
    )

    return WorkflowDefinition(
        workflow_id=workflow_id,
        name="Brainstorming Session",
        description=f"Brainstorm on: {topic[:100]}...",
        steps=steps,
        global_constraints=constraints,
        allowed_sources=constraints.get("allowed_sources", []),
        strict_mode=constraints.get("strict_mode", False)  # Less strict for brainstorming
    )


def create_essay_with_brainstorming_workflow(
    prompt: str,
    constraints: dict,
    allowed_sources: list[str],
    strict_mode: bool = True
) -> WorkflowDefinition:
    """
    Create an essay workflow that starts with brainstorming.

    This extended workflow:
    1. Brainstorms ideas and angles for the essay
    2. Plans the essay structure based on brainstormed ideas
    3. Researches evidence
    4. Drafts the essay
    5. Critiques and revises
    6. Fact-checks

    Args:
        prompt: Essay prompt
        constraints: Constraints (wordcount, tone, etc.)
        allowed_sources: List of allowed source IDs
        strict_mode: Whether to operate in strict source-only mode

    Returns:
        Workflow definition
    """
    workflow_id = str(uuid.uuid4())

    steps = [
        # Brainstorming phase
        WorkflowStep(
            step_id="brainstorm",
            agent_role=AgentRole.BRAINSTORMER,
            task=f"Brainstorm ideas and angles for: {prompt}",
            constraints={
                "mode": "explore",
                "depth": 2,
                "sources": ["philosophy", "culture", "notes", "concepts"],
            }
        ),
        # Planning informed by brainstorming
        WorkflowStep(
            step_id="plan",
            agent_role=AgentRole.PLANNER,
            task=f"Create an outline for: {prompt}",
            dependencies=["brainstorm"],
            constraints=constraints
        ),
        # Research
        WorkflowStep(
            step_id="research",
            agent_role=AgentRole.RESEARCH,
            task="Find evidence for each section of the outline",
            dependencies=["plan"]
        ),
        # Draft
        WorkflowStep(
            step_id="draft",
            agent_role=AgentRole.WRITER,
            task="Write the essay draft based on outline and evidence",
            dependencies=["plan", "research"],
            constraints=constraints
        ),
        # Parallel critiques
        WorkflowStep(
            step_id="critique_structure",
            agent_role=AgentRole.CRITIC,
            task="Critique the structural quality of the draft",
            dependencies=["draft"]
        ),
        WorkflowStep(
            step_id="critique_style",
            agent_role=AgentRole.CRITIC,
            task="Critique the style and voice of the draft",
            dependencies=["draft"]
        ),
        # Revision
        WorkflowStep(
            step_id="revise",
            agent_role=AgentRole.WRITER,
            task="Revise the draft based on critique",
            dependencies=["draft", "critique_structure", "critique_style"],
            constraints=constraints
        ),
        # Fact check
        WorkflowStep(
            step_id="fact_check",
            agent_role=AgentRole.FACT_CHECKER,
            task="Verify citations and check for unsupported claims",
            dependencies=["revise"]
        ),
    ]

    return WorkflowDefinition(
        workflow_id=workflow_id,
        name="Essay Generation with Brainstorming",
        description=f"Generate essay with brainstorming: {prompt[:100]}...",
        steps=steps,
        global_constraints=constraints,
        allowed_sources=allowed_sources,
        strict_mode=strict_mode
    )
