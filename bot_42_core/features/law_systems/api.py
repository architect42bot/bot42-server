# features/law_systems/api.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any, Dict
from .storage import LAWDB
from .ai_bridge import law_context_snapshot, explain_conflict, suggest_restorative_steps

router = APIRouter(tags=["law"])

@router.get("/law/stats")
def law_stats() -> Dict[str, Any]:
    return LAWDB.stats()

@router.get("/law/context")
def law_context() -> Dict[str, Any]:
    return law_context_snapshot()

@router.get("/law/conflicts")
def law_conflicts() -> Any:
    return LAWDB.conflicts

@router.get("/law/conflicts/{conflict_id}")
def law_conflict(conflict_id: int) -> Any:
    c = LAWDB.get_conflict_by_id(conflict_id)
    if not c:
        raise HTTPException(404, "Conflict not found")
    return c

@router.get("/law/conflicts/{conflict_id}/explain")
def law_conflict_explain(conflict_id: int) -> Dict[str, Any]:
    s = explain_conflict(conflict_id)
    if not s:
        raise HTTPException(404, "Conflict not found")
    return {"id": conflict_id, "explanation": s}

@router.get("/law/conflicts/{conflict_id}/restorative-plan")
def law_conflict_plan(conflict_id: int) -> Any:
    plan = suggest_restorative_steps(conflict_id)
    if not plan:
        raise HTTPException(404, "Conflict not found")
    return plan