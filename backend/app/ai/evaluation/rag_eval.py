"""
RAG Evaluation Framework

Measures retrieval quality (precision, recall, MRR, NDCG) and generation quality
(faithfulness, relevance, completeness) using LLM-as-judge or heuristic scoring.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ScoreType(str, Enum):
    RETRIEVAL = "retrieval"
    GENERATION = "generation"
    END_TO_END = "end_to_end"


@dataclass
class EvalCase:
    query: str
    expected_answer: str
    expected_doc_ids: list[str] = field(default_factory=list)
    expected_sections: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    doc_ids: list[str]
    scores: list[float] = field(default_factory=list)
    latency_ms: float = 0.0


@dataclass
class GenerationResult:
    answer: str
    citations: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    token_count: int = 0


@dataclass
class EvalScore:
    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    faithfulness: float = 0.0
    relevance: float = 0.0
    completeness: float = 0.0
    answer_correctness: float = 0.0
    latency_ms: float = 0.0


def precision_at_k(retrieved: list[str], relevant: list[str], k: int = 5) -> float:
    retrieved_k = retrieved[:k]
    if not retrieved_k:
        return 0.0
    hits = sum(1 for doc_id in retrieved_k if doc_id in relevant)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: list[str], k: int = 5) -> float:
    if not relevant:
        return 0.0
    retrieved_k = retrieved[:k]
    hits = sum(1 for doc_id in retrieved_k if doc_id in relevant)
    return hits / len(relevant)


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    for i, doc_id in enumerate(retrieved, 1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: list[str], k: int = 5) -> float:
    import math

    retrieved_k = retrieved[:k]
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_k, 1):
        if doc_id in relevant:
            dcg += 1.0 / math.log2(i + 1)

    ideal_len = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_len + 1))

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def _token_overlap_score(prediction: str, reference: str) -> float:
    pred_tokens = set(prediction.lower().split())
    ref_tokens = set(reference.lower().split())
    if not ref_tokens:
        return 0.0
    overlap = pred_tokens & ref_tokens
    return len(overlap) / len(ref_tokens)


def evaluate_retrieval(
    retrieved: RetrievalResult,
    expected_doc_ids: list[str],
    k: int = 5,
) -> dict[str, float]:
    return {
        "precision_at_k": precision_at_k(retrieved.doc_ids, expected_doc_ids, k),
        "recall_at_k": recall_at_k(retrieved.doc_ids, expected_doc_ids, k),
        "mrr": mrr(retrieved.doc_ids, expected_doc_ids),
        "ndcg": ndcg_at_k(retrieved.doc_ids, expected_doc_ids, k),
    }


def evaluate_generation(
    generation: GenerationResult,
    expected_answer: str,
) -> dict[str, float]:
    faithfulness = _token_overlap_score(generation.answer, expected_answer)
    relevance = _token_overlap_score(generation.answer, expected_answer)
    completeness = min(1.0, len(generation.answer.split()) / max(1, len(expected_answer.split())))
    answer_correctness = _token_overlap_score(generation.answer, expected_answer)

    return {
        "faithfulness": faithfulness,
        "relevance": relevance,
        "completeness": completeness,
        "answer_correctness": answer_correctness,
    }


def evaluate_case(
    case: EvalCase,
    retrieval: Optional[RetrievalResult] = None,
    generation: Optional[GenerationResult] = None,
    k: int = 5,
) -> EvalScore:
    scores = EvalScore()

    if retrieval:
        ret = evaluate_retrieval(retrieval, case.expected_doc_ids, k)
        scores.precision_at_k = ret["precision_at_k"]
        scores.recall_at_k = ret["recall_at_k"]
        scores.mrr = ret["mrr"]
        scores.ndcg = ret["ndcg"]
        scores.latency_ms += retrieval.latency_ms

    if generation:
        gen = evaluate_generation(generation, case.expected_answer)
        scores.faithfulness = gen["faithfulness"]
        scores.relevance = gen["relevance"]
        scores.completeness = gen["completeness"]
        scores.answer_correctness = gen["answer_correctness"]
        scores.latency_ms += generation.latency_ms

    return scores


def load_eval_suite(path: str | Path) -> list[EvalCase]:
    data = json.loads(Path(path).read_text())
    cases = []
    for item in data:
        cases.append(
            EvalCase(
                query=item["query"],
                expected_answer=item["expected_answer"],
                expected_doc_ids=item.get("expected_doc_ids", []),
                expected_sections=item.get("expected_sections", []),
                metadata=item.get("metadata", {}),
            )
        )
    return cases


def run_eval_suite(
    eval_cases: list[EvalCase],
    retrieval_fn=None,
    generation_fn=None,
    k: int = 5,
) -> dict:
    all_scores: list[EvalScore] = []
    errors = 0

    for case in eval_cases:
        try:
            retrieval = retrieval_fn(case.query) if retrieval_fn else None
            generation = generation_fn(case.query) if generation_fn else None
            score = evaluate_case(case, retrieval, generation, k)
            all_scores.append(score)
        except Exception as exc:
            errors += 1
            print(f"Error evaluating case '{case.query[:50]}...': {exc}")

    if not all_scores:
        return {"error": "no cases evaluated", "cases": 0, "errors": errors}

    import statistics

    def avg(attr: str) -> float:
        vals = [getattr(s, attr) for s in all_scores]
        return statistics.mean(vals) if vals else 0.0

    return {
        "cases": len(all_scores),
        "errors": errors,
        "retrieval": {
            "precision_at_k": avg("precision_at_k"),
            "recall_at_k": avg("recall_at_k"),
            "mrr": avg("mrr"),
            "ndcg": avg("ndcg"),
        },
        "generation": {
            "faithfulness": avg("faithfulness"),
            "relevance": avg("relevance"),
            "completeness": avg("completeness"),
            "answer_correctness": avg("answer_correctness"),
        },
        "latency_ms": avg("latency_ms"),
    }


def save_report(report: dict, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2))
