import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

MEMORY_DIR = Path(__file__).resolve().parent.parent / "data" / "memory"


class LongTermMemory:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.patterns_path = MEMORY_DIR / "patterns.json"
        self.connections_path = MEMORY_DIR / "connections.json"
        self.patterns = self._load(self.patterns_path, {})
        self.connections = self._load(self.connections_path, [])

    def _load(self, path: Path, default):
        if path.exists():
            try:
                with path.open() as f:
                    return json.load(f)
            except Exception:
                return default
        return default

    def _save(self, path: Path, data):
        with path.open("w") as f:
            json.dump(data, f, indent=2)

    def learn_pattern(self, pattern_key: str, context: dict):
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = {
                "count": 0,
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "contexts": [],
            }
        self.patterns[pattern_key]["count"] += 1
        self.patterns[pattern_key]["last_seen"] = datetime.now(timezone.utc).isoformat()
        self.patterns[pattern_key]["contexts"].append(context)
        if len(self.patterns[pattern_key]["contexts"]) > 20:
            self.patterns[pattern_key]["contexts"] = self.patterns[pattern_key]["contexts"][-20:]
        self._save(self.patterns_path, self.patterns)

    def learn_connection(self, source: str, target: str, connection_type: str, weight: float = 1.0):
        existing = None
        for c in self.connections:
            if c["source"] == source and c["target"] == target and c["type"] == connection_type:
                existing = c
                break
        if existing:
            existing["weight"] = min(existing["weight"] + weight, 10.0)
            existing["last_seen"] = datetime.now(timezone.utc).isoformat()
        else:
            self.connections.append(
                {
                    "source": source,
                    "target": target,
                    "type": connection_type,
                    "weight": weight,
                    "first_seen": datetime.now(timezone.utc).isoformat(),
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                }
            )
        self._save(self.connections_path, self.connections)

    def get_pattern(self, pattern_key: str) -> dict | None:
        return self.patterns.get(pattern_key)

    def get_connections(self, node: str, connection_type: str | None = None) -> list[dict]:
        results = []
        for c in self.connections:
            if c["source"] == node or c["target"] == node:
                if connection_type is None or c["type"] == connection_type:
                    results.append(c)
        return sorted(results, key=lambda x: x["weight"], reverse=True)

    def get_frequent_patterns(self, min_count: int = 3) -> list[tuple]:
        return [
            (k, v)
            for k, v in sorted(self.patterns.items(), key=lambda x: x[1]["count"], reverse=True)
            if v["count"] >= min_count
        ]

    def get_strong_connections(self, min_weight: float = 2.0) -> list[dict]:
        return [c for c in self.connections if c["weight"] >= min_weight]
