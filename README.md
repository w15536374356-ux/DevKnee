# my-rag · 企业级智能知识探索助手

一个基于 **RAG + 对话树 + Agent** 的智能知识探索助手，目标是从零构建一个完整的 AI 应用后端，而不是简单调用 LLM API

## 技术栈

| 技术 | 用途 |
|---|---|
| FastAPI | Web API 框架 |
| SQLAlchemy 2.0 (Async) | 异步 ORM，操作 PostgreSQL |
| asyncpg | PostgreSQL 异步驱动 |
| pydantic-settings | 环境变量统一配置 |
| PostgreSQL (Docker) | 结构化数据存储 |
| Python 3.11+ | 开发语言 |
| git / GitHub | 版本管理 |

> 后续会陆续加入：Milvus、DeepSeek LLM、BGE Embedding / Reranker、Redis、Docker Compose等

## 项目结构（当前）

```
my-rag/
├── .gitignore
├── README.md
└── backend/
    ├── .env                 # 本地配置（不进 git）
    ├── requirements.txt
    └── app/
        ├── __init__.py
        ├── main.py          # 应用入口：生命周期 + CORS + 路由装配
        ├── config.py        # 统一配置入口（pydantic-settings）
        ├── api/
        │   ├── __init__.py
        │   └── v1/
        │       ├── __init__.py
        │       └── router.py # 路由聚合点 + 健康检查
        ├── storage/          # 数据层
        │   ├── __init__.py
        │   ├── db.py        # 异步引擎 + 会话工厂
        │   └── init_db.py   # 启动自动建库（pg_trgm 扩展）
        ├── core/             # 业务核心层（今天建目录，后续每天加文件）
        │   ├── __init__.py
        │   ├── rag/         # RAG 检索/重排/管线
        │   ├── llm/         # LLM 客户端
        │   ├── prompt/      # Prompt 拼装
        │   └── observability/ # 可观测（request_id / 耗时）
        ├── ingestion/        # 文档处理
        └── schemas/          # API 模型
```
## 数据模型（5 张表）

| 表 | 职责 |
|---|---|
| `conversations` | 对话（树根锚点 + 最大深度） |
| `messages` | 消息节点（`parent_message_id` 自引用形成对话树，含 `depth`/`branch_path` 列） |
| `context_snapshots` | 会话快照（摘要 + 关键引用，分支上下文继承用） |
| `documents` | 上传的源文档（去重哈希 + 入库状态机） |
| `chunks` | 文档切块文本（pg_trgm 关键词索引 + 向量外链到 Milvus） |


## 环境要求

- Python ≥ 3.11
- Docker（用于运行 PostgreSQL）
- PostgreSQL 容器：本机 5433 端口，库名 `knowledge`，用户/密码 `postgres/postgres`

## 如何启动

```bash
# 1. 启动数据库（首次）
docker run --name my-rag-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=knowledge -p 5433:5432 -d postgres:16

# 2. 启动后端
cd backend
python -m venv .venv
.venv\Scripts\activate            
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后访问：

- 健康检查：http://127.0.0.1:8000/api/v1/health → {"status":"ok"}
- 接口文档：http://127.0.0.1:8000/docs

## 当前进度- 
- ✅ FastAPI 项目骨架与分层
- ✅ 健康检查接口（`/api/v1/health`）
- ✅ 统一配置入口（环境变量 > .env > 默认值）
- ✅ SQLAlchemy 2.0 异步引擎 + 会话工厂
- ✅ 启动自动建库：`pg_trgm` 扩展
- ✅ Git 初始化与 GitHub 上传
- ✅ FastAPI 项目骨架与分层
- ✅ 健康检查接口
- ✅ 统一配置入口（环境变量 > .env > 默认值）
- ✅ SQLAlchemy 2.0 异步引擎 + 会话工厂
- ✅ 数据模型：5 张表（对话树 + 文档入库，D1 加列、D5 砍 blocks）
- ✅ Alembic 迁移：alembic upgrade head 建库

