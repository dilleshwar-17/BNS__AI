class Reranker:
    def rerank(self, results: list[dict], query: str) -> list[dict]:
        scored = []
        for r in results:
            text = r.get("text", "")
            score = r.get("score", 0)
            relevance = len(set(query.lower().split()) & set(text.lower().split())) / max(len(query.split()), 1)
            scored.append({**r, "rerank_score": score * 0.7 + relevance * 0.3})
        return sorted(scored, key=lambda x: x["rerank_score"], reverse=True)
