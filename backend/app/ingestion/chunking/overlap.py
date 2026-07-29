class OverlapHandler:
    def add_overlap(self, chunks: list[dict], overlap_size: int = 50) -> list[dict]:
        for i in range(1, len(chunks)):
            prev_text = chunks[i - 1]["text"]
            chunks[i]["text"] = prev_text[-overlap_size:] + chunks[i]["text"]
        return chunks
