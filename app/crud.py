import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.models import CanvasAction


async def create_action(
    session: AsyncSession,
    canvas_id: str,
    action_type: str,
    action_data: dict,
    sequence: int = 0
) -> CanvasAction:
    action = CanvasAction(
        canvas_id=canvas_id,
        action_type=action_type,
        action_data=json.dumps(action_data),
        sequence=sequence
    )
    session.add(action)
    await session.commit()
    await session.refresh(action)
    return action


async def get_actions(
    session: AsyncSession,
    canvas_id: str,
    limit: Optional[int] = None
) -> List[CanvasAction]:
    query = select(CanvasAction).where(
        CanvasAction.canvas_id == canvas_id
    ).order_by(CanvasAction.sequence)
    
    if limit:
        query = query.limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()


async def get_action_count(
    session: AsyncSession,
    canvas_id: str
) -> int:
    query = select(func.count(CanvasAction.id)).where(
        CanvasAction.canvas_id == canvas_id
    )
    result = await session.execute(query)
    return result.scalar() or 0


async def get_last_sequence(
    session: AsyncSession,
    canvas_id: str
) -> int:
    query = select(CanvasAction).where(
        CanvasAction.canvas_id == canvas_id
    ).order_by(CanvasAction.sequence.desc()).limit(1)
    
    result = await session.execute(query)
    last_action = result.scalar_one_or_none()
    return last_action.sequence if last_action else -1


async def delete_actions_from(
    session: AsyncSession,
    canvas_id: str,
    from_sequence: int
) -> int:
    query = delete(CanvasAction).where(
        CanvasAction.canvas_id == canvas_id,
        CanvasAction.sequence >= from_sequence
    )
    result = await session.execute(query)
    await session.commit()
    return result.rowcount


async def clear_canvas(
    session: AsyncSession,
    canvas_id: str
) -> int:
    query = delete(CanvasAction).where(
        CanvasAction.canvas_id == canvas_id
    )
    result = await session.execute(query)
    await session.commit()
    return result.rowcount
