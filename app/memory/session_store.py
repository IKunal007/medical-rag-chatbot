# app/memory/session_store.py
from typing import Any, Dict

# In-memory session state
_session_state: Dict[str, Dict[str, Any]] = {}


def set_session_value(session_id: str, key: str, value: Any) -> None:
    if session_id not in _session_state:
        _session_state[session_id] = {}
    _session_state[session_id][key] = value


def get_session_value(session_id: str, key: str, default=None):
    return _session_state.get(session_id, {}).get(key, default)


def clear_session(session_id: str):
    _session_state.pop(session_id, None)
