from collections import defaultdict, deque

# session_id -> deque of messages
_chat_memory = defaultdict(lambda: deque(maxlen=6))

def add_turn(session_id: str, role: str, content: str):
    _chat_memory[session_id].append({
        "role": role,
        "content": content
    })

def get_memory(session_id: str):
    return list(_chat_memory.get(session_id, []))
