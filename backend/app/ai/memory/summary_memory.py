class SummaryMemory:
    def __init__(self):
        self.summaries: dict[str, str] = {}

    def add_summary(self, session_id: str, summary: str):
        self.summaries[session_id] = summary

    def get_summary(self, session_id: str) -> str | None:
        return self.summaries.get(session_id)
