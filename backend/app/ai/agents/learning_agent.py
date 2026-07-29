from collections import defaultdict
from typing import Any

from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.core.logging import get_logger

logger = get_logger(__name__)


class SpiderWebLearningAgent(BaseAgent):
    def __init__(self):
        super().__init__("learning_agent", "Spider web self-adapting learning system")
        self.subscribe_to("learn")
        self.subscribe_to("adapt")
        self.subscribe_to("spider_stats")
        self.subscribe_to("*")

        self.query_patterns = defaultdict(
            lambda: {"count": 0, "types": defaultdict(int), "avg_rating": 0, "ratings": []}
        )
        self.type_performance = defaultdict(lambda: {"count": 0, "avg_quality": 0, "avg_rating": 0})
        self.user_patterns = defaultdict(lambda: {"queries": 0, "types": defaultdict(int), "feedback": []})
        self.web_connections = defaultdict(lambda: defaultdict(float))
        self.gaps = []  # detected knowledge gaps

    async def process(self, message: Message) -> Any:
        msg_type = message.type
        payload = message.payload

        self._record_web_traffic(message)

        if msg_type == "learn":
            return await self.learn(payload)
        elif msg_type == "adapt":
            return await self.adapt(payload)
        elif msg_type == "spider_stats":
            return self.get_web_stats()
        elif msg_type == "full_cycle_result":
            return await self.learn_from_cycle(payload)
        else:
            self._observe(message)
            return {"observed": True}

    def _record_web_traffic(self, message: Message):
        sender = message.sender
        msg_type = message.type
        self.web_connections[sender][msg_type] += 1.0

    def _observe(self, message: Message):
        pattern_key = f"{message.sender}:{message.type}"
        self.long_term.learn_pattern(
            pattern_key,
            {
                "sender": message.sender,
                "type": message.type,
                "payload_keys": list(message.payload.keys()),
            },
        )

    async def learn(self, payload: dict) -> dict:
        query = payload.get("query", "")
        query_type = payload.get("type", "")
        rating = payload.get("rating", 0)
        quality = payload.get("quality", 0.0)
        user_id = payload.get("user_id")
        response = payload.get("response", "")

        if query:
            self.query_patterns[query]["count"] += 1
            self.query_patterns[query]["types"][query_type] += 1
            if rating > 0:
                self.query_patterns[query]["ratings"].append(rating)
                self.query_patterns[query]["avg_rating"] = sum(self.query_patterns[query]["ratings"]) / len(
                    self.query_patterns[query]["ratings"]
                )

            pattern_key = f"query:{query_type}:{query[:30]}"
            self.long_term.learn_pattern(
                pattern_key,
                {
                    "type": query_type,
                    "rating": rating,
                    "quality": quality,
                },
            )

        if query_type:
            tp = self.type_performance[query_type]
            tp["count"] += 1
            tp["avg_quality"] = (tp["avg_quality"] * (tp["count"] - 1) + quality) / tp["count"]
            if rating > 0:
                tp["avg_rating"] = (tp["avg_rating"] * (tp["count"] - 1) + rating) / tp["count"]

        if user_id:
            profile = self.get_user_profile(user_id)
            profile.record_feedback(query, rating, f"quality:{quality:.2f}")
            self.user_patterns[user_id]["queries"] += 1
            self.user_patterns[user_id]["types"][query_type] += 1
            if rating > 0:
                self.user_patterns[user_id]["feedback"].append(rating)

        self.log("learned", query_type=query_type, rating=rating, quality=quality)

        return {
            "learned": True,
            "query_type": query_type,
            "pattern_count": self.query_patterns[query]["count"] if query else 0,
            "type_performance": {
                k: {"count": v["count"], "avg_quality": round(v["avg_quality"], 3)}
                for k, v in self.type_performance.items()
            },
        }

    async def adapt(self, payload: dict) -> dict:
        adaptations = []

        low_performers = [t for t, d in self.type_performance.items() if d["count"] >= 3 and d["avg_quality"] < 0.5]
        for t in low_performers:
            adaptations.append(f"Boosting retrieval depth for low-performing type: {t}")

        if payload.get("detect_gaps", False):
            for q, data in self.query_patterns.items():
                if data["count"] >= 3 and data["avg_rating"] < 0.4:
                    gap = f"User query '{q[:50]}' consistently underperforms"
                    if gap not in self.gaps:
                        self.gaps.append(gap)
                        adaptations.append(f"New gap detected: {gap}")

        frequent_types = sorted(
            self.type_performance.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )
        if frequent_types:
            adaptations.append(f"Most frequent type: {frequent_types[0][0]} ({frequent_types[0][1]['count']} queries)")

        active_users = sorted(
            self.user_patterns.items(),
            key=lambda x: x[1]["queries"],
            reverse=True,
        )
        if active_users:
            top_user = active_users[0]
            adaptations.append(f"Most active user: {top_user[0]} ({top_user[1]['queries']} queries)")

        self.log("adapted", adaptations=adaptations[:5])

        return {
            "adapted": True,
            "adaptations": adaptations,
            "type_performance": {
                k: {
                    "count": v["count"],
                    "avg_quality": round(v["avg_quality"], 3),
                    "avg_rating": round(v["avg_rating"], 3),
                }
                for k, v in self.type_performance.items()
            },
            "gaps_detected": len(self.gaps),
            "gaps": self.gaps[-5:],
        }

    async def learn_from_cycle(self, payload: dict) -> dict:
        query = payload.get("query", "")
        classification = payload.get("classification", {})
        retrieval = payload.get("retrieval", {})
        prompt = payload.get("prompt", "")
        response = payload.get("response", "")
        verification = payload.get("verification", {})
        user_id = payload.get("user_id")

        qtype = classification.get("primary_type", "")
        quality = verification.get("quality_score", 0.5) if verification else 0.5
        rating = payload.get("rating", 0)

        learn_payload = {
            "query": query,
            "type": qtype,
            "rating": rating,
            "quality": quality,
            "user_id": user_id,
            "response": response,
        }
        await self.learn(learn_payload)

        if retrieval:
            strategies = retrieval.get("strategies_used", [])
            pattern_key = f"strategy:{qtype}:{'+'.join(strategies)}"
            self.long_term.learn_pattern(
                pattern_key,
                {
                    "type": qtype,
                    "strategies": strategies,
                    "total_results": retrieval.get("total_fused", 0),
                    "quality": quality,
                },
            )

        section_connections = classification.get("sections", [])
        if section_connections and qtype:
            for s in section_connections:
                self.long_term.learn_connection(
                    f"type:{qtype}",
                    f"section:{s}",
                    "QUERY_TYPE_REFERENCES_SECTION",
                )

        self.log("learned_from_cycle", type=qtype, quality=quality)

        return {
            "learned": True,
            "type": qtype,
            "quality": quality,
            "patterns_updates": 3,
        }

    def get_web_stats(self) -> dict:
        sender_summary = {}
        for sender, types in self.web_connections.items():
            sender_summary[sender] = {
                "total_messages": sum(types.values()),
                "types": dict(types),
            }

        type_stats = {}
        for t, d in self.type_performance.items():
            type_stats[t] = {
                "count": d["count"],
                "avg_quality": round(d["avg_quality"], 3),
                "avg_rating": round(d["avg_rating"], 3) if d["avg_rating"] else 0,
            }

        return {
            "agents": dict(sender_summary),
            "type_performance": type_stats,
            "total_patterns": len(self.query_patterns),
            "total_web_connections": sum(sum(v.values()) for v in self.web_connections.values()),
            "knowledge_gaps": self.gaps[-10:],
            "frequent_patterns": self.long_term.get_frequent_patterns(5)[:5],
            "strong_connections": self.long_term.get_strong_connections(3.0)[:5],
            "feedback_stats": self.feedback.get_stats(),
        }


learning_agent = SpiderWebLearningAgent()
