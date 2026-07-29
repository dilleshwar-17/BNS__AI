import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "BNS_queries" / "BNS_QUERIES"


class TestRAGDataset:
    def test_dataset_exists(self):
        path = DATA_DIR / "bns_rag_dataset.jsonl"
        assert path.exists(), "RAG dataset not found"

    def test_dataset_has_entries(self):
        path = DATA_DIR / "bns_rag_dataset.jsonl"
        count = 0
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
                    entry = json.loads(line)
                    assert "id" in entry
                    assert "query" in entry
                    assert "answer" in entry
        assert count > 0, "No entries in RAG dataset"
        assert count > 2000, f"Expected >2000 entries, got {count}"

    def test_chapter_datasets_exist(self):
        for i in range(1, 21):
            path = DATA_DIR / f"chapter_{i:02d}.jsonl"
            assert path.exists(), f"Chapter {i} dataset not found"

    def test_chapters_have_entries(self):
        total = 0
        for i in range(1, 21):
            path = DATA_DIR / f"chapter_{i:02d}.jsonl"
            count = 0
            with path.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        count += 1
            total += count
        assert total > 0, "No entries across chapters"

    def test_dataset_includes_sections(self):
        path = DATA_DIR / "bns_rag_dataset.jsonl"
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    break
        assert "section" in entry, "Missing section field"
        assert "query_type" in entry, "Missing query_type field"


class TestPDFExtraction:
    def test_pdf_full_text_exists(self):
        path = DATA_DIR / "bns_full_pdf.txt"
        assert path.exists(), "PDF full text not found"
        text = path.read_text(encoding="utf-8")
        assert len(text) > 10000, f"PDF text too short: {len(text)} chars"

    def test_pdf_full_text_has_chapters(self):
        path = DATA_DIR / "bns_full_pdf.txt"
        text = path.read_text(encoding="utf-8")
        chapters = [l for l in text.split("\n") if l.strip().startswith("CHAPTER")]
        assert len(chapters) > 0, "No chapter markers found in PDF text"
