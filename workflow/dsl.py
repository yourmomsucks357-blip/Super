"""
Workflow DSL — YAML-serializable schema for agent workflow definitions.

Node reference syntax:  {{#node_id.field#}}
Loop start node schema: ${parentNodeId}start

Supported node types:
    start            Input parameters, initialise $flow.state
    agent            Run a registered agent type
    memory_retrieval Pull from the memory system (MaTTS)
    outcome_judgment Self-judgment → success / failure branch
    condition        Conditional routing (expression-based)
    loop             Iterative sub-graph; start node = ${parentId}start
    human_approval   Pause-and-resume human-in-the-loop gate
    fail_branch      Error isolation: exposes error_message + error_type
    safla_consolidation Trigger SAFLA confidence update + strategy distillation

Error handling strategies per node:
    fail-branch      Route execution to the fail_branch node
    default-value    Return a predefined fallback value
    abort            Halt execution immediately
    retry            Re-queue the node up to retry_limit times
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
import yaml


class NodeType(str, Enum):
    START              = "start"
    AGENT              = "agent"
    MEMORY_RETRIEVAL   = "memory_retrieval"
    OUTCOME_JUDGMENT   = "outcome_judgment"
    CONDITION          = "condition"
    LOOP               = "loop"
    HUMAN_APPROVAL     = "human_approval"
    FAIL_BRANCH        = "fail_branch"
    SAFLA_CONSOLIDATION = "safla_consolidation"


class ErrorStrategy(str, Enum):
    FAIL_BRANCH    = "fail-branch"
    DEFAULT_VALUE  = "default-value"
    ABORT          = "abort"
    RETRY          = "retry"


@dataclass
class ErrorHandling:
    strategy:       ErrorStrategy       = ErrorStrategy.FAIL_BRANCH
    default_value:  Optional[Any]       = None
    retry_limit:    int                 = 3
    error_variable: str                 = "error_message"
    error_type_var: str                 = "error_type"


@dataclass
class NodeDef:
    id:           str                    = field(default_factory=lambda: str(uuid.uuid4()))
    type:         NodeType               = NodeType.AGENT
    label:        str                    = ""
    config:       Dict[str, Any]         = field(default_factory=dict)
    depends_on:   List[str]              = field(default_factory=list)
    on_error:     Optional[ErrorHandling] = None
    # Visual position for node-graph UI
    position:     Dict[str, float]       = field(default_factory=lambda: {"x": 0.0, "y": 0.0})


@dataclass
class EdgeDef:
    source:     str            = ""
    target:     str            = ""
    condition:  Optional[str]  = None   # "success" | "failure" | expression string


@dataclass
class WorkflowConfig:
    """Top-level DSL container."""
    workflow_id:    str            = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str            = "1.0"
    name:           str            = "Untitled Workflow"
    description:    str            = ""
    nodes:          List[NodeDef]  = field(default_factory=list)
    edges:          List[EdgeDef]  = field(default_factory=list)
    # $flow.state initial values
    flow_state:     Dict[str, Any] = field(default_factory=dict)


class WorkflowDSL:
    """Serialize / deserialize WorkflowConfig to/from YAML DSL."""

    @staticmethod
    def to_yaml(config: WorkflowConfig) -> str:
        data: Dict[str, Any] = {
            "schema_version": config.schema_version,
            "id": config.workflow_id,
            "name": config.name,
            "description": config.description,
            "flow_state": config.flow_state,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type.value,
                    "label": n.label,
                    "config": n.config,
                    "depends_on": n.depends_on,
                    "position": n.position,
                    **({"on_error": {
                        "strategy": n.on_error.strategy.value,
                        "default_value": n.on_error.default_value,
                        "retry_limit": n.on_error.retry_limit,
                        "error_variable": n.on_error.error_variable,
                    }} if n.on_error else {}),
                }
                for n in config.nodes
            ],
            "edges": [
                {"from": e.source, "to": e.target,
                 **({"condition": e.condition} if e.condition else {})}
                for e in config.edges
            ],
        }
        return yaml.dump(data, sort_keys=False, allow_unicode=True)

    @staticmethod
    def from_yaml(raw: str) -> WorkflowConfig:
        data = yaml.safe_load(raw)
        nodes = [
            NodeDef(
                id=n["id"],
                type=NodeType(n["type"]),
                label=n.get("label", ""),
                config=n.get("config", {}),
                depends_on=n.get("depends_on", []),
                position=n.get("position", {"x": 0.0, "y": 0.0}),
                on_error=ErrorHandling(
                    strategy=ErrorStrategy(n["on_error"]["strategy"]),
                    default_value=n["on_error"].get("default_value"),
                    retry_limit=n["on_error"].get("retry_limit", 3),
                    error_variable=n["on_error"].get("error_variable", "error_message"),
                ) if "on_error" in n else None,
            )
            for n in data.get("nodes", [])
        ]
        edges = [
            EdgeDef(
                source=e["from"],
                target=e["to"],
                condition=e.get("condition"),
            )
            for e in data.get("edges", [])
        ]
        return WorkflowConfig(
            workflow_id=data.get("id", str(uuid.uuid4())),
            schema_version=data.get("schema_version", "1.0"),
            name=data.get("name", "Untitled Workflow"),
            description=data.get("description", ""),
            nodes=nodes,
            edges=edges,
            flow_state=data.get("flow_state", {}),
        )

    @staticmethod
    def default_workflow() -> WorkflowConfig:
        """Returns the canonical SAFLA execution workflow from the spec."""
        n_start   = NodeDef(id="start",   type=NodeType.START,              label="Task Initiation",      position={"x": 400, "y": 50})
        n_mem     = NodeDef(id="mem",     type=NodeType.MEMORY_RETRIEVAL,    label="Memory Retrieval (MaTTS)", config={"top_k": 5}, depends_on=["start"], position={"x": 400, "y": 180})
        n_exec    = NodeDef(id="exec",    type=NodeType.AGENT,               label="Agent Execution",      config={"agent_type": "assistant"}, depends_on=["mem"], position={"x": 400, "y": 310})
        n_judge   = NodeDef(id="judge",   type=NodeType.OUTCOME_JUDGMENT,    label="Outcome Self-Judgment", depends_on=["exec"], position={"x": 400, "y": 440})
        n_distill = NodeDef(id="distill", type=NodeType.SAFLA_CONSOLIDATION, label="Distill Procedural Strategy", config={"branch": "success"}, depends_on=["judge"], position={"x": 200, "y": 570})
        n_guard   = NodeDef(id="guard",   type=NodeType.SAFLA_CONSOLIDATION, label="Extract Negative Guardrail",  config={"branch": "failure"}, depends_on=["judge"], position={"x": 600, "y": 570})
        n_consol  = NodeDef(id="consol",  type=NodeType.SAFLA_CONSOLIDATION, label="Consolidation & SAFLA",       depends_on=["distill", "guard"], position={"x": 400, "y": 700})

        return WorkflowConfig(
            name="SAFLA Execution Workflow",
            description="Canonical task → memory → execution → judgment → SAFLA loop",
            nodes=[n_start, n_mem, n_exec, n_judge, n_distill, n_guard, n_consol],
            edges=[
                EdgeDef("start",   "mem"),
                EdgeDef("mem",     "exec"),
                EdgeDef("exec",    "judge"),
                EdgeDef("judge",   "distill", condition="success"),
                EdgeDef("judge",   "guard",   condition="failure"),
                EdgeDef("distill", "consol"),
                EdgeDef("guard",   "consol"),
            ],
        )
