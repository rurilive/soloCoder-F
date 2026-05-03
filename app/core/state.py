from typing import Dict, Set
from datetime import datetime
from fastapi import WebSocket

active_connections: Dict[str, Set[WebSocket]] = {}
room_last_activity: Dict[str, datetime] = {}
