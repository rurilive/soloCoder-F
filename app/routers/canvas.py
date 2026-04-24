import json
from typing import List
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.models import CanvasAction

router = APIRouter()


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.async_session() as session:
        yield session


class ActionCreate(BaseModel):
    canvas_id: str
    action_type: str
    action_data: dict


class ActionResponse(BaseModel):
    id: int
    canvas_id: str
    action_type: str
    action_data: dict
    sequence: int

    class Config:
        from_attributes = True


@router.post("/actions", response_model=ActionResponse)
async def create_action(
    action: ActionCreate,
    db: AsyncSession = Depends(get_db)
):
    last_sequence = await crud.get_last_sequence(db, action.canvas_id)
    new_sequence = last_sequence + 1
    
    db_action = await crud.create_action(
        db,
        canvas_id=action.canvas_id,
        action_type=action.action_type,
        action_data=action.action_data,
        sequence=new_sequence
    )
    
    return ActionResponse(
        id=db_action.id,
        canvas_id=db_action.canvas_id,
        action_type=db_action.action_type,
        action_data=json.loads(db_action.action_data),
        sequence=db_action.sequence
    )


@router.get("/actions/{canvas_id}", response_model=List[ActionResponse])
async def get_actions(
    canvas_id: str,
    limit: int = None,
    db: AsyncSession = Depends(get_db)
):
    actions = await crud.get_actions(db, canvas_id, limit)
    
    return [
        ActionResponse(
            id=action.id,
            canvas_id=action.canvas_id,
            action_type=action.action_type,
            action_data=json.loads(action.action_data),
            sequence=action.sequence
        )
        for action in actions
    ]


@router.get("/actions/{canvas_id}/count")
async def get_action_count(
    canvas_id: str,
    db: AsyncSession = Depends(get_db)
):
    count = await crud.get_action_count(db, canvas_id)
    return {"canvas_id": canvas_id, "count": count}


@router.delete("/actions/{canvas_id}/from/{sequence}")
async def delete_actions_from(
    canvas_id: str,
    sequence: int,
    db: AsyncSession = Depends(get_db)
):
    deleted = await crud.delete_actions_from(db, canvas_id, sequence)
    return {"canvas_id": canvas_id, "deleted_count": deleted}


@router.delete("/actions/{canvas_id}")
async def clear_canvas(
    canvas_id: str,
    db: AsyncSession = Depends(get_db)
):
    deleted = await crud.clear_canvas(db, canvas_id)
    return {"canvas_id": canvas_id, "cleared_count": deleted}
