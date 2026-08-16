import asyncio
import hashlib
import logging
import uuid

from sqlalchemy import select

from core.rag.embedder import embed_documents
from ingestion.chunker import chunk_segments
from ingestion.parser import parse_document
from app.storage.db import AsyncSessionLocal
from app.storage.milvus import insert_chunks
from app.storage.models import Chunk, Document, IngestionStatus

logger = logging.getLogger(__name__)


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def ingest_document(doc_id: uuid.UUID, file_path: str) -> None:
    """同步入库主函数。embedding 失败不阻断（降级为纯关键词检索），记录告警。"""
    async with AsyncSessionLocal() as session:
        doc = await session.get(Document, doc_id)
        if doc is None:
            return

        try:
            await _set_status(session, doc, IngestionStatus.PARSING)
            segments = await asyncio.to_thread(parse_document, file_path)

            await _set_status(session, doc, IngestionStatus.CHUNKING)
            chunk_list = await asyncio.to_thread(chunk_segments, segments)

            vectors: list[list[float]] = []
            if chunk_list:
                await _set_status(session, doc, IngestionStatus.EMBEDDING)
                vectors = await asyncio.to_thread(
                    embed_documents, [c["content"] for c in chunk_list]
                )
                # 清理上一版本（重建索引时），避免脏数据
                await _delete_existing(doc.id)

            # PG 落库（chunk id 在 Python 侧生成，与 Milvus 主键一致）
            new_chunks: list[Chunk] = []
            for i, c in enumerate(chunk_list):
                new_chunks.append(
                    Chunk(
                        id=uuid.uuid4(),
                        document_id=doc.id,
                        chunk_index=i,
                        title=c.get("title") or "",
                        content=c["content"],
                        content_hash=compute_hash(c["content"]),
                        metadata_={"chunk_type": "paragraph"},
                    )
                )
            session.add_all(new_chunks)
            await session.flush()
            doc.chunk_count = len(new_chunks)

            # Milvus 写入（embedding 失败时 vectors 为空，跳过，关键词路仍可用）
            if vectors:
                await _set_status(session, doc, IngestionStatus.INDEXING)
                rows = [
                    {
                        "chunk_id": str(ch.id),
                        "document_id": str(doc.id),
                        "title": ch.title or "",
                        "content": ch.content,
                        "embedding": vec,
                    }
                    for ch, vec in zip(new_chunks, vectors)
                ]
                await asyncio.to_thread(insert_chunks, rows)

            doc.error = None
            await _set_status(session, doc, IngestionStatus.READY)
            logger.info("doc %s ingested: %d chunks", doc.id, len(new_chunks))
        except Exception as exc:  # noqa: BLE001
            doc.error = f"[ingest_failed] {exc}"[:2000]
            await _set_status(session, doc, IngestionStatus.FAILED)
            logger.exception("ingest document %s failed", doc_id)
            raise


async def _delete_existing(doc_id: uuid.UUID) -> None:
    """重建索引：清除该文档旧 chunk（PG 与 Milvus）。"""
    from app.storage.milvus import delete_document_chunks

    async with AsyncSessionLocal() as session:
        old = (await session.execute(select(Chunk).where(Chunk.document_id == doc_id))).scalars().all()
        for o in old:
            await session.delete(o)
        await session.commit()
    try:
        await asyncio.to_thread(delete_document_chunks, str(doc_id))
    except Exception:  # noqa: BLE001
        logger.warning("delete milvus chunks failed for doc %s", doc_id, exc_info=True)


async def _set_status(session, doc: Document, status: IngestionStatus) -> None:
    doc.status = status.value
    await session.commit()