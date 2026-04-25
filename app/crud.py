import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, update
from app.models import CanvasAction, User, Canvas


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


async def create_user(
    session: AsyncSession,
    username: str,
    password_hash: str,
    user_type: str = "normal"
) -> User:
    user = User(
        username=username,
        password_hash=password_hash,
        user_type=user_type
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_username(
    session: AsyncSession,
    username: str
) -> Optional[User]:
    query = select(User).where(User.username == username)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession,
    user_id: int
) -> Optional[User]:
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def create_canvas(
    session: AsyncSession,
    canvas_id: str,
    owner_id: Optional[int] = None,
    is_private: bool = False
) -> Canvas:
    canvas = Canvas(
        canvas_id=canvas_id,
        owner_id=owner_id,
        is_private=is_private
    )
    session.add(canvas)
    await session.commit()
    await session.refresh(canvas)
    return canvas


async def get_canvas(
    session: AsyncSession,
    canvas_id: str
) -> Optional[Canvas]:
    query = select(Canvas).where(Canvas.canvas_id == canvas_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_user_canvases(
    session: AsyncSession,
    owner_id: int
) -> List[Canvas]:
    query = select(Canvas).where(Canvas.owner_id == owner_id)
    result = await session.execute(query)
    return result.scalars().all()


async def get_user_canvas_count(
    session: AsyncSession,
    owner_id: int
) -> int:
    query = select(func.count(Canvas.id)).where(Canvas.owner_id == owner_id)
    result = await session.execute(query)
    return result.scalar() or 0


async def update_canvas_activity(
    session: AsyncSession,
    canvas_id: str
) -> Optional[Canvas]:
    canvas = await get_canvas(session, canvas_id)
    if canvas:
        canvas.last_active_at = datetime.utcnow()
        await session.commit()
        await session.refresh(canvas)
    return canvas


async def get_inactive_canvases(
    session: AsyncSession,
    seconds: int = 60
) -> List[Canvas]:
    cutoff = datetime.utcnow() - timedelta(seconds=seconds)
    query = select(Canvas).where(
        Canvas.last_active_at < cutoff,
        Canvas.canvas_id != "default"
    )
    result = await session.execute(query)
    return result.scalars().all()


async def delete_canvas(
    session: AsyncSession,
    canvas_id: str
) -> int:
    await clear_canvas(session, canvas_id)
    query = delete(Canvas).where(Canvas.canvas_id == canvas_id)
    result = await session.execute(query)
    await session.commit()
    return result.rowcount
