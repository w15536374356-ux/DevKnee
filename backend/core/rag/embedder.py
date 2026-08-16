from  functools import lru_cache
from  app.config import get_settings

QUERY="查询用文字"

#单例缓存工厂
@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(get_settings().embedding_model)


#批量处理,将数据存到向量库
def embed_document(text:list[str])->list[list[float]]:
    if not text:
        return []
    model=_model()
    vector=model.encode(
        text,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32
    )
    return [x.tolist() for x in vector]


#返回用户单条询问并检索向量,配合后续检索召回k个
# 工具:用户提问检索器
def embed_query(text:list[str])->list[float]:
    model=_model()
    vector=model.encode(
        [QUERY+text],
        normalize_embeddings=True,
        show_progress_bar=False
    )
    return vector[0].tolist



model=_model()
print(model)
print(type(model))