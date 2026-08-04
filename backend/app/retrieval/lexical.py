"""Lexical index (BM25) for hybrid retrieval.

Uses rank_bm25 for fast keyword search over chunk texts.
"""

from __future__ import annotations

import pickle
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np
from app.core.config import get_settings
from rank_bm25 import BM25Okapi

# Stopwords are excluded from lexical matching so that content-free queries
# (e.g. "best restaurant in delhi") do not produce spurious BM25 hits, which
# would otherwise defeat fail-closed gating.
_STOPWORDS = frozenset(
    """
    a an and are as at be by for from has have he her his in is it its
    of on or that the this to was were which with you your who whom what
    when where why how do does did not no but so than then them they she
    their there these those shall may shall be means under above about
    after before between during such any all also into over through unless
    until upon whether while per each
    """.split()
)


@dataclass
class LexicalRecord:
    chunk_id: uuid.UUID
    text: str
    metadata: dict


class LexicalIndex:
    """BM25 index over legal chunk texts with persistence."""

    def __init__(self, index_path: Optional[Path] = None) -> None:
        settings = get_settings()
        self._index_path = index_path or (settings.storage_dir / "lexical_index.pkl")
        self._corpus: List[LexicalRecord] = []
        self._bm25: Optional[BM25Okapi] = None
        self._load()

    def _tokenize(self, text: str) -> List[str]:
        return [t for t in re.findall(r"[a-zA-Z0-9]+", text.lower()) if t not in _STOPWORDS]

    def _load(self) -> None:
        if self._index_path.exists():
            with self._index_path.open("rb") as f:
                data = pickle.load(f)
            self._corpus = data["corpus"]
            self._bm25 = data["bm25"]
        else:
            self._corpus = []
            self._bm25 = None

    def _save(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        with self._index_path.open("wb") as f:
            pickle.dump({"corpus": self._corpus, "bm25": self._bm25}, f)

    def upsert(self, records: Sequence[LexicalRecord]) -> None:
        """Add or update records; rebuilds index."""
        new_ids = {r.chunk_id for r in records}
        # Keep only records not being replaced
        self._corpus = [r for r in self._corpus if r.chunk_id not in new_ids]
        self._corpus.extend(records)
        tokenized = [self._tokenize(r.text) for r in self._corpus]
        self._bm25 = BM25Okapi(tokenized)
        self._save()

    def delete(self, chunk_ids: Sequence[uuid.UUID]) -> None:
        ids = set(chunk_ids)
        self._corpus = [r for r in self._corpus if r.chunk_id not in ids]
        if self._corpus:
            tokenized = [self._tokenize(r.text) for r in self._corpus]
            self._bm25 = BM25Okapi(tokenized)
        else:
            self._bm25 = None
        self._save()

    def search(self, query: str, n_results: int = 20) -> List[tuple[LexicalRecord, float]]:
        if not self._bm25 or not self._corpus:
            return []
        scores = self._bm25.get_scores(self._tokenize(query))
        top_idx = np.argsort(scores)[::-1][:n_results]
        return [(self._corpus[i], float(scores[i])) for i in top_idx if scores[i] > 0]

    def count(self) -> int:
        return len(self._corpus)
