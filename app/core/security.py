import hashlib
import uuid
from typing import Dict, Optional

SESSIONS: Dict[str, int] = {}


def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return get_password_hash(password) == password_hash


def create_session(user_id: int) -> str:
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = user_id
    return session_id


def delete_session(session_id: Optional[str]) -> bool:
    if session_id and session_id in SESSIONS:
        del SESSIONS[session_id]
        return True
    return False


def get_user_id_from_session(session_id: Optional[str]) -> Optional[int]:
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]
    return None
