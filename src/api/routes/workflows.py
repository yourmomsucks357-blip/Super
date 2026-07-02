from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from src.workflow.dsl import WorkflowDSL, WorkflowConfig
from src.workflow.engine import workflow_engine

router = APIRouter(prefix="/workflows", tags=["workflows"])

# In-memory workflow registry
_workflows: Dict[str, WorkflowConfig] = {}

# Seed the default SAFLA workflow on startup
_default = WorkflowDSL.default_workflow()
_workflows[_default.workflow_id] = _default


class WorkflowCreateRequest(BaseModel):
    name: str
    description: str = ""
    dsl_yaml: Optional[str] = None  # if provided, parse from DSL


class WorkflowRunRequest(BaseModel):
    inputs: Dict[str, Any] = {}


class ResumeRequest(BaseModel):
    approved: bool = True
    feedback: str = ""


# ── CRUD ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_workflows():
    return [
        {"workflow_id": w.workflow_id, "name": w.name, "description": w.description,
         "node_count": len(w.nodes), "edge_count": len(w.edges)}
        for w in _workflows.values()
    ]


@router.post("")
async def create_workflow(req: WorkflowCreateRequest):
    if req.dsl_yaml:
        try:
            config = WorkflowDSL.from_yaml(req.dsl_yaml)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"DSL parse error: {exc}")
    else:
        config = WorkflowDSL.default_workflow()
        config.name = req.name
        config.description = req.description
    _workflows[config.workflow_id] = config
    return {"workflow_id": config.workflow_id, "name": config.name}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    config = _workflows.get(workflow_id)
    if not config:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "workflow_id": config.workflow_id,
        "name": config.name,
        "description": config.description,
        "flow_state": config.flow_state,
        "nodes": [
            {"id": n.id, "type": n.type.value, "label": n.label,
             "config": n.config, "depends_on": n.depends_on, "position": n.position}
            for n in config.nodes
        ],
        "edges": [
            {"source": e.source, "target": e.target, "condition": e.condition}
            for e in config.edges
        ],
        "dsl_yaml": WorkflowDSL.to_yaml(config),
    }


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    if workflow_id not in _workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    del _workflows[workflow_id]
    return {"deleted": workflow_id}


# ── Execution ────────────────────────────────────────────────────────────────

@router.post("/{workflow_id}/run")
async def run_workflow(workflow_id: str, req: WorkflowRunRequest):
    config = _workflows.get(workflow_id)
    if not config:
        raise HTTPException(status_code=404, detail="Workflow not found")
    run = await workflow_engine.run(config, inputs=req.inputs)
    return {
        "run_id": run.run_id,
        "status": run.status,
        "outputs": run.outputs,
        "flow_state": run.flow_state,
        "error": run.error,
        "paused_at": run.paused_at,
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = workflow_engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": run.run_id,
        "workflow_id": run.workflow_id,
        "status": run.status,
        "outputs": run.outputs,
        "error": run.error,
        "paused_at": run.paused_at,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.post("/runs/{run_id}/resume")
async def resume_run(run_id: str, req: ResumeRequest):
    run = workflow_engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "paused":
        raise HTTPException(status_code=400, detail=f"Run is not paused (status: {run.status})")
    await workflow_engine.resume(run_id, {"approved": req.approved, "feedback": req.feedback})
    return {"run_id": run_id, "resumed": True}


@router.get("")
async def list_runs():
    return [
        {"run_id": r.run_id, "workflow_id": r.workflow_id, "status": r.status,
         "created_at": r.created_at.isoformat()}
        for r in workflow_engine.list_runs()
    ]
