"""
Composite relevance scoring for memory retrieval (MaTTS).

    R(q, m) = α_q * sim(q_token, m) + α_c * confidence + α_u * norm(usage)

where:
    α_q = memory_retrieval_similarity_weight
    α_c = memory_retrieval_confidence_weight
    α_u = memory_retrieval_usage_weight
"""
from typing import List
from .models import MemoryItem, RetrievalResult
from src.config import settings


def _token_similarity(query: str, text: str) -> float:
    """Jaccard similarity over token sets."""
    q = set(query.lower().split())
    t = set(text.lower().split())
    if not q or not t:
        return 0.0
    return len(q & t) / len(q | t)


def _norm_usage(usage: int, max_usage: int) -> float:
    if max_usage == 0:
        return 0.0
    return min(1.0, usage / max_usage)


def score_item(query: str, item: MemoryItem, max_usage: int = 1) -> RetrievalResult:
    corpus = item.content + " " + item.title + " " + " ".join(item.tags)
    sim        = _token_similarity(query, corpus)
    sim_c      = settings.memory_retrieval_similarity_weight * sim
    conf_c     = settings.memory_retrieval_confidence_weight * item.confidence
    usage_c    = settings.memory_retrieval_usage_weight * _norm_usage(item.usage_count, max_usage)
    return RetrievalResult(
        item=item,
        relevance_score=sim_c + conf_c + usage_c,
        similarity=sim,
        confidence_contribution=conf_c,
        usage_contribution=usage_c,
    )


def retrieve(query: str, items: List[MemoryItem], top_k: int = 5) -> List[RetrievalResult]:
    if not items:
        return []
    max_u = max((i.usage_count for i in items), default=1) or 1
    results = [score_item(query, i, max_u) for i in items]
    results.sort(key=lambda r: r.relevance_score, reverse=True)
    return results[:top_k]
