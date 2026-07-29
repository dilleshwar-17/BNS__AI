class ContextBuilder:
    def build(self, results: list[dict], max_chars: int = 4000) -> str:
        parts = []
        chars = 0
        for r in results:
            text = r.get("text", "")
            if not text:
                continue
            tag = r.get("source", "unknown")
            entry = f"[{tag}] {text[:400]}"
            if chars + len(entry) > max_chars:
                break
            parts.append(entry)
            chars += len(entry)
        return "\n\n".join(parts)
