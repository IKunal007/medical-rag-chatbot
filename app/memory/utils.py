def build_memory_aware_query(query: str, memory: list):
    if not memory:
        return query

    last_user_turns = [
        m["content"] for m in memory if m["role"] == "user"
    ]

    context = " ".join(last_user_turns[-2:])
    return f"{context}\nCurrent question: {query}"
