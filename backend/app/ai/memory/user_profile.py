import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

PROFILE_DIR = Path(__file__).resolve().parent.parent / "data" / "profiles"


class UserProfile:
    def __init__(self, user_id: str):
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        self.user_id = user_id
        self.filepath = PROFILE_DIR / f"{user_id}.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.filepath.exists():
            try:
                return json.loads(self.filepath.read_text())
            except Exception:
                pass
        return {
            "user_id": self.user_id,
            "preferred_modes": {},
            "frequent_topics": {},
            "frequent_sections": {},
            "complexity_preference": "medium",
            "feedback_history": [],
            "session_count": 0,
            "last_active": None,
            "created": datetime.now(timezone.utc).isoformat(),
        }

    def _save(self):
        self.filepath.write_text(json.dumps(self.data, indent=2))

    def record_query(self, query_type: str, topic: str = "", sections: list[int] | None = None):
        self.data["session_count"] += 1
        self.data["last_active"] = datetime.now(timezone.utc).isoformat()
        self.data["preferred_modes"][query_type] = self.data["preferred_modes"].get(query_type, 0) + 1
        if topic:
            self.data["frequent_topics"][topic] = self.data["frequent_topics"].get(topic, 0) + 1
        if sections:
            for s in sections:
                key = str(s)
                self.data["frequent_sections"][key] = self.data["frequent_sections"].get(key, 0) + 1
        self._save()

    def record_feedback(self, query: str, rating: int, response_quality: str = ""):
        self.data["feedback_history"].append(
            {
                "query": query,
                "rating": rating,
                "quality": response_quality,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        if len(self.data["feedback_history"]) > 100:
            self.data["feedback_history"] = self.data["feedback_history"][-100:]
        self._save()

    def get_preferred_mode(self) -> str:
        if not self.data["preferred_modes"]:
            return "legal_guidance"
        return max(self.data["preferred_modes"], key=self.data["preferred_modes"].get)

    def get_top_topics(self, n: int = 5) -> list[str]:
        sorted_topics = sorted(
            self.data["frequent_topics"].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [t[0] for t in sorted_topics[:n]]

    def get_feedback_stats(self) -> dict:
        history = self.data.get("feedback_history", [])
        if not history:
            return {"avg_rating": 0, "count": 0}
        ratings = [h["rating"] for h in history]
        return {
            "avg_rating": sum(ratings) / len(ratings),
            "count": len(ratings),
            "max_rating": max(ratings),
            "min_rating": min(ratings),
        }
