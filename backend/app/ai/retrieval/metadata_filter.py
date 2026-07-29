class MetadataFilter:
    def apply(self, results: list[dict], filters: dict | None = None) -> list[dict]:
        if not filters:
            return results
        filtered = []
        for r in results:
            meta = r.get("metadata", {})
            match = all(meta.get(k) == v for k, v in filters.items())
            if match:
                filtered.append(r)
        return filtered
