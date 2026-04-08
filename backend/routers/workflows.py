"""No-Code Workflows — visual workflow builder for non-developers."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from typing import Optional, Any
import uuid

from ..database import get_db, WorkflowDef

router = APIRouter()

# Built-in workflow templates
TEMPLATES = [
    {
        "id": "email-summarize",
        "name": "Email Summarizer",
        "description": "Summarize incoming emails and extract action items",
        "steps": [
            {"type": "trigger", "event": "email_received"},
            {"type": "ai", "action": "summarize", "prompt": "Summarize this email and list action items"},
            {"type": "output", "target": "task_list"},
        ],
    },
    {
        "id": "doc-qa",
        "name": "Document Q&A",
        "description": "Answer questions from your knowledge base",
        "steps": [
            {"type": "trigger", "event": "question_asked"},
            {"type": "knowledge", "action": "search"},
            {"type": "ai", "action": "answer", "prompt": "Using this context, answer the question"},
            {"type": "output", "target": "response"},
        ],
    },
    {
        "id": "verify-paste",
        "name": "Auto-Verify",
        "description": "Automatically verify any AI output you paste",
        "steps": [
            {"type": "trigger", "event": "content_pasted"},
            {"type": "verify", "action": "score"},
            {"type": "output", "target": "trust_badge"},
        ],
    },
]


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    steps: list[dict]


@router.get("/templates")
async def list_templates():
    """Get built-in workflow templates."""
    return TEMPLATES


@router.post("")
async def create_workflow(workflow: WorkflowCreate, db=Depends(get_db)):
    """Create a new workflow."""
    w = WorkflowDef(
        name=workflow.name,
        description=workflow.description,
        steps=workflow.steps,
    )
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return {"id": w.id, "name": w.name, "created": True}


@router.get("")
async def list_workflows(db=Depends(get_db)):
    """List all workflows."""
    result = await db.execute(select(WorkflowDef))
    items = result.scalars().all()
    return [
        {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "steps": len(w.steps),
            "enabled": w.enabled,
        }
        for w in items
    ]


@router.post("/{workflow_id}/run")
async def run_workflow(workflow_id: str, input_data: dict = None, db=Depends(get_db)):
    """Execute a workflow with input data."""
    result = await db.execute(select(WorkflowDef).where(WorkflowDef.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Simulate workflow execution
    execution_log = []
    for i, step in enumerate(workflow.steps):
        execution_log.append({
            "step": i + 1,
            "type": step.get("type"),
            "status": "completed",
            "output": f"Step {i+1} ({step.get('type')}) executed successfully",
        })

    return {
        "workflow_id": workflow_id,
        "name": workflow.name,
        "status": "completed",
        "steps_executed": len(workflow.steps),
        "log": execution_log,
    }
