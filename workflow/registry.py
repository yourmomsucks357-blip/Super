from typing import Dict
from .dsl import WorkflowConfig, WorkflowDSL

class WorkflowRegistry:
    _workflows: Dict[str, WorkflowConfig] = {}

    @classmethod
    def register(cls, config: WorkflowConfig):
        cls._workflows[config.workflow_id] = config

    @classmethod
    def get(cls, workflow_id: str) -> WorkflowConfig:
        return cls._workflows.get(workflow_id)

    @classmethod
    def list_all(cls):
        return list(cls._workflows.values())

    @classmethod
    def delete(cls, workflow_id: str):
        if workflow_id in cls._workflows:
            del cls._workflows[workflow_id]

# Seed with default
_default = WorkflowDSL.default_workflow()
WorkflowRegistry.register(_default)
