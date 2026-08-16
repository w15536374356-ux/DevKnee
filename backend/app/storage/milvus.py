# Milvus 连接 + 集合管理。
# chunk_id(VARCHAR 主键) 与 PostgreSQL chunks.id 一一对应，引用溯源靠它打通。
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.config import get_settings

_settings = get_settings()
_COLLECTION_NAME = _settings.milvus_collection
_DIM = _settings.embedding_dim


def connect_milvus() -> None:
    connections.connect(
        alias=_settings.milvus_alias,
        host=_settings.milvus_host,
        port=_settings.milvus_port,
    )


def disconnect_milvus() -> None:
    connections.disconnect(_settings.milvus_alias)


def ensure_collection() -> Collection:
    """获取或创建集合（幂等）。HNSW + COSINE 适合 bge 系列向量。"""
    connect_milvus()
    if utility.has_collection(_COLLECTION_NAME, using=_settings.milvus_alias):
        return Collection(_COLLECTION_NAME, using=_settings.milvus_alias)

    schema = CollectionSchema(
        fields=[
            FieldSchema("chunk_id", DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema("document_id", DataType.VARCHAR, max_length=64),
            FieldSchema("title", DataType.VARCHAR, max_length=512),
            FieldSchema("content", DataType.VARCHAR, max_length=8192),
            FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=_DIM),
        ],
        description="knowledge base chunks",
    )
    collection = Collection(_COLLECTION_NAME, schema=schema, using=_settings.milvus_alias)
    collection.create_index(
        "embedding",
        {"index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}},
    )
    collection.load()
    return collection


def insert_chunks(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    col = ensure_collection()
    col.insert(rows)
    col.flush()


def search_vectors(vector: list[float], top_k: int = 20) -> list[dict[str, Any]]:
    """向量检索，返回 [{chunk_id, document_id, title, content, score}]。"""
    try:
        col = ensure_collection()
    except Exception:
        # Milvus 不可用时上层降级为关键词检索
        return []
    hits = col.search(
        data=[vector],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"ef": 128}},
        limit=top_k,
        output_fields=["chunk_id", "document_id", "title", "content"],
        using=_settings.milvus_alias,
    )
    results = []
    for hit in hits[0]:
        entity = hit.entity
        results.append(
            {
                "chunk_id": entity.get("chunk_id"),
                "document_id": entity.get("document_id"),
                "title": entity.get("title") or "",
                "content": entity.get("content") or "",
                "score": float(hit.distance),
            }
        )
    return results


def delete_document_chunks(document_id: str) -> None:
    col = ensure_collection()
    col.delete(f'document_id == "{document_id}"')