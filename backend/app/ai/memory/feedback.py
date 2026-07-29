from collections import defaultdict
from datetime import datetime, timezone

from app.core.logging import get_logger

logger = get_logger(__name__)


class FeedbackTracker:
    def __init__(self):
        self.feedback: list[dict] = []
        self.query_scores: defaultdict[str, list[int]] = defaultdict(list)
        self.threshold = 0.6

    def record(self, query: str, response: str, rating: int, quality_score: float, user_id: str | None = None):
        entry = {
            "query": query,
            "response_preview": response[:200],
            "rating": rating,
            "quality_score": quality_score,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.feedback.append(entry)
        self.query_scores[query].append(rating)
        logger.debug("feedback_recorded", rating=rating, quality=quality_score)

    def get_average_for_query(self, query: str) -> float:
        scores = self.query_scores.get(query, [])
        return sum(scores) / len(scores) if scores else 0.0

    def get_recent(self, n: int = 20) -> list[dict]:
        return self.feedback[-n:]

    def get_low_quality(self, threshold: float | None = None) -> list[dict]:
        t = threshold or self.threshold
        return [f for f in self.feedback if f["quality_score"] < t]

    def is_learned_pattern(self, query: str, min_occurrences: int = 3) -> bool:
        return len(self.query_scores.get(query, [])) >= min_occurrences

    def get_improvement_areas(self) -> list[str]:
        areas = []
        for query, scores in self.query_scores.items():
            avg = sum(scores) / len(scores)
            if avg < self.threshold and len(scores) >= 2:
                areas.append(query)
        return areas[:10]

    def get_stats(self) -> dict:
        all_ratings = [f["rating"] for f in self.feedback]
        if not all_ratings:
            return {"total": 0, "avg_rating": 0}
        return {
            "total": len(self.feedback),
            "avg_rating": sum(all_ratings) / len(all_ratings),
            "low_quality_count": len(self.get_low_quality()),
            "unique_queries": len(self.query_scores),
        }
