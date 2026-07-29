class UserMemory:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.interests: list[str] = []
        self.frequent_acts: list[str] = []
        self.preferences: dict = {}

    def record_interest(self, topic: str):
        if topic not in self.interests:
            self.interests.append(topic)
            if len(self.interests) > 20:
                self.interests.pop(0)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "interests": self.interests,
            "frequent_acts": self.frequent_acts,
            "preferences": self.preferences,
        }
