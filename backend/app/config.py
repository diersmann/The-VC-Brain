from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    name: str = "The VC Brain API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://vc_brain:vc_brain_dev@localhost:5432/vc_brain"

    # LLM provider
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.3

    cors_origins: str = "http://localhost:5173"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO / S3-compatible object storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "vc-brain-snapshots"
    minio_secure: bool = False

    # Source API keys
    github_token: str = ""
    producthunt_token: str = ""
    tavily_api_key: str = ""
    youtube_api_key: str = ""

    # Collection thresholds and limits
    signal_threshold: float = 0.45
    collection_concurrency: int = 4
    tavily_monthly_budget: int = 1000
    arxiv_min_citations: int = 10
    arxiv_coauthor_cap: int = 20
    website_seed_cap: int = 10
    persons_created_per_day: int = 200

    # Scoring agents
    agent_model: str = "gpt-4o"
    agent_concurrency: int = 2
    agent_max_tokens: int = 1000

    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_concurrency: int = 4

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
