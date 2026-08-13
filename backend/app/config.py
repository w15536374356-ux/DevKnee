from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 应用 ----
    app_env: str = "development"
    debug: bool = True
    db_auto_create: bool = True 
    project_name: str = "企业级智能知识探索助手"
    cors_origins: str = "http://localhost:5173" 

    # ---- PostgreSQL ----
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge"
    )

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379/0"

    # ---- Milvus ----
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_alias: str = "default"
    milvus_collection: str = "knowledge_chunks"

    # ---- Embedding / Rerank 
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dim: int = 512
    rerank_model: str = "BAAI/bge-reranker-base"
    rerank_top_n: int = 50

    # LLM 
    llm_api_base: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_max_tokens: int = 2048
    mock_llm: bool = True 

    # ---- 检索参数 ----
    retriever_top_k: int = 8
    rerank_top_n: int = 30  

    # ---- Celery ----
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ---- 数据目录 ----
    data_dir: str = "./data"
    upload_dir: str = "./data/uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache #调用一次,保存为缓存,下次使用直接调用,优化
def get_settings() -> Settings:
    return Settings()
