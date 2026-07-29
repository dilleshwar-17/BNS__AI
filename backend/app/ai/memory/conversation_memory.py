from collections import deque


class ConversationMemory:
    def __init__(self, max_turns: int = 20):
        self.messages: deque = deque(maxlen=max_turns)

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_history(self) -> list[dict]:
        return list(self.messages)

    def clear(self):
        self.messages.clear()

    def to_prompt(self) -> str:
        return "\n".join(f"{m['role']}: {m['content']}" for m in self.messages)
