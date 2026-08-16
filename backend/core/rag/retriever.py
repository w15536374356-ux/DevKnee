# 混合检索：Milvus 向量 + PostgreSQL pg_trgm 关键词（对中文有效），RRF 融合，BGE 精排
import asyncio
import logging
from dataclasses import dataclass, field

from sqlalchemy import text

from app.config import get_settings
from core.observability import tracing
from app.storage.db import AsyncSessionLocal
from app.storage.milvus import search_vectors

logger = logging.getLogger(__name__)

TOP_VECTOR = 20
TOP_KEYWORD = 20
RRF_K = 60


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    content: str
    source: str = "keyword"  # vector / keyword
    score: float = 0.0
    references: list[int] = field(default_factory=list)


async def retrieve(question: str) -> list[RetrievedChunk]:
    """入口：返回 rerank 后的 top-k 检索块。"""
    settings = get_settings()
    vector_hits: list[RetrievedChunk] = []
    keyword_hits: list[RetrievedChunk] = []

    # 1) 向量路
    try:
        from core.rag.embedder import embed_query

        tracing.mark("embed_query")
        qvec = await asyncio.to_thread(embed_query, question)
        tracing.mark("vector_search")
        raw = await asyncio.to_thread(search_vectors, qvec, TOP_VECTOR)
        vector_hits = [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                title=r["title"],
                content=r["content"],
                source="vector",
                score=r["score"],
            )
            for r in raw
        ]
    except Exception:  # noqa: BLE001
        logger.warning("vector retrieval failed, fallback to keyword only", exc_info=True)
        tracing.mark("vector_search_failed")

    # 2) 关键词路（pg_trgm 相似度，走 GIN 索引 kNN）
    try:
        tracing.mark("keyword_search")
        keyword_hits = await _keyword_search(question, TOP_KEYWORD)
    except Exception:  # noqa: BLE001
        logger.warning("keyword search failed", exc_info=True)
        tracing.mark("keyword_search_failed")

    # 3) RRF 融合
    tracing.mark("rrf_fuse")
    fused = _rrf_fuse(vector_hits, keyword_hits)

    # 4) BGE 精排（对融合后小候选集打分）
    tracing.mark("rerank")
    ranked = await _rerank(question, fused)
    tracing.mark("retrieve_done")
    return ranked[: settings.retriever_top_k]


async def _keyword_search(question: str, top: int) -> list[RetrievedChunk]:
    """pg_trgm kNN：ORDER BY content <-> query，GIN(gin_trgm_ops) 加速，对中文有效。"""
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id, document_id, title, content
                    FROM chunks
                    ORDER BY content <-> :q
                    LIMIT :top
                    """
                ),
                {"q": question, "top": top},
            )
        ).fetchall()
    return [
        RetrievedChunk(
            chunk_id=str(r.id),
            document_id=str(r.document_id),
            title=r.title or "",
            content=r.content,
            source="keyword",
        )
        for r in rows
    ]


def _rrf_fuse(*ranked_lists: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion：按名次加权求和，兼顾两路的排序信号。"""
    scores: dict[str, float] = {}
    best: dict[str, RetrievedChunk] = {}
    for hits in ranked_lists:
        for rank, hit in enumerate(hits):
            key = hit.chunk_id
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
            if key not in best:
                best[key] = hit
    ordered = sorted(scores.items(), key=lambda kv: -kv[1])
    fused = [best[key] for key, _ in ordered]
    for i, hit in enumerate(fused):
        hit.score = scores[hit.chunk_id]
    return fused


async def _rerank(question: str, fused: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """BGE Reranker 精排；rerank 不可用时原序截断（降级）。"""
    if not fused:
        return fused
    try:
        from core.rag.reranker import rerank

        settings = get_settings()
        candidates = fused[: settings.rerank_top_n]
        scores = await asyncio.to_thread(
            rerank, question, [c.content for c in candidates]
        )
        ranked = sorted(zip(candidates, scores), key=lambda x: -x[1])
        for hit, s in ranked:
            hit.score = float(s)
        return [hit for hit, _ in ranked]
    except Exception:  # noqa: BLE001
        logger.warning("rerank unavailable, return fused order", exc_info=True)
        return fused