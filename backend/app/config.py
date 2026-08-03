from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    name: str = "The VC Brain API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://vc_brain:vc_brain_dev@localhost:5432/vc_brain"

    # LLM provider
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_max_tokens: int = Field(default=4096, ge=1, le=32_000)
    llm_temperature: float = Field(default=0.3, ge=0, le=2)

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
    signal_threshold: float = Field(default=0.45, ge=0, le=1)
    collection_concurrency: int = Field(default=4, ge=1, le=64)
    tavily_monthly_budget: int = Field(default=1000, ge=0)
    arxiv_min_citations: int = Field(default=10, ge=0)
    arxiv_coauthor_cap: int = Field(default=20, ge=0)
    website_seed_cap: int = Field(default=10, ge=1, le=100)
    website_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    persons_created_per_day: int = Field(default=200, ge=1)

    # Untrusted inbound pitch uploads
    upload_max_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    upload_max_pages: int = Field(default=100, ge=1)
    upload_max_text_chars: int = Field(default=50_000, ge=1)
    upload_malware_scanner: str = ""
    upload_scan_timeout_seconds: int = Field(default=30, ge=1)

    # Scoring agents
    agent_model: str = "gpt-4o"
    agent_concurrency: int = Field(default=2, ge=1, le=64)
    agent_max_tokens: int = Field(default=1000, ge=1, le=32_000)
    agent_monthly_budget: int = Field(default=100, ge=0)

    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_concurrency: int = Field(default=4, ge=1, le=64)

    # Deal lifecycle
    contact_threshold: float = Field(default=0.65, ge=0, le=1)
    pipeline_stuck_after_minutes: int = Field(default=30, ge=1)
    pipeline_batch_size: int = Field(default=5, ge=1, le=100)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
