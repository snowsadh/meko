import os

from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import find_dotenv

_ENV_FILE = find_dotenv(usecwd=True)
if _ENV_FILE:
    load_dotenv(_ENV_FILE, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE or None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    environment: str = "development"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/openhuman"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Agent job worker
    agent_worker_concurrency: int = 4
    agent_job_poll_interval_seconds: float = 1.0

    # Postgres checkpointer (Phase 4)
    checkpoint_database_url: str = ""

    # JWT authentication
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    @model_validator(mode="after")
    def validate_db_urls(self) -> "Settings":
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self

    # Encryption for bot tokens (AES-256-GCM, 32-byte key)
    encryption_key: str = ""
    encryption_key_previous: str = ""

    # Product credentials are deliberately independent of the coding client's key.
    meko_product_api_key: str = ""
    meko_mcp_url: str = "https://mcp.mekodata.ai/mcp"
    meko_api_url: str = "https://api.mekodata.ai/api/v1"
    meko_timeout_seconds: float = 60
    max_document_bytes: int = 5 * 1024 * 1024

    # OpenAI handles application replies and model-directed tool calls.
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"
    agent_max_tool_rounds: int = 4

    # Bot Gateway
    gateway_enabled: bool = False

    # Slack App Token (for socket mode)
    slack_app_token: str = ""

    # Slack OAuth
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_oauth_redirect_uri: str = ""

    # Slack identity mode
    slack_identity_mode: str = "fixed"

    # Fixed bot credentials
    slack_bot_hr_client_id: str = ""
    slack_bot_hr_client_secret: str = ""
    slack_bot_hr_app_token: str = ""
    slack_bot_support_client_id: str = ""
    slack_bot_support_client_secret: str = ""
    slack_bot_support_app_token: str = ""
    slack_bot_sales_client_id: str = ""
    slack_bot_sales_client_secret: str = ""
    slack_bot_sales_app_token: str = ""
    slack_bot_general_client_id: str = ""
    slack_bot_general_client_secret: str = ""
    slack_bot_general_app_token: str = ""
    slack_bot_legal_client_id: str = ""
    slack_bot_legal_client_secret: str = ""
    slack_bot_legal_app_token: str = ""

    # Frontend URL
    frontend_url: str = "http://localhost:3000"

    # MCP OAuth
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    notion_client_id: str = ""
    notion_client_secret: str = ""
    vercel_client_id: str = ""
    vercel_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    canva_client_id: str = ""
    canva_client_secret: str = ""
    mcp_oauth_redirect_uri: str = ""

    @property
    def mcp_oauth_credentials(self) -> dict[str, dict[str, str]]:
        creds: dict[str, dict[str, str]] = {}

        def _val(field: str, env: str) -> str:
            return field or os.getenv(env, "")

        if gid := _val(self.gmail_client_id, "GMAIL_CLIENT_ID"):
            creds["gmail"] = {
                "client_id": gid,
                "client_secret": _val(self.gmail_client_secret, "GMAIL_CLIENT_SECRET"),
            }
        if nid := _val(self.notion_client_id, "NOTION_CLIENT_ID"):
            creds["notion"] = {
                "client_id": nid,
                "client_secret": _val(self.notion_client_secret, "NOTION_CLIENT_SECRET"),
            }
        if vid := _val(self.vercel_client_id, "VERCEL_CLIENT_ID"):
            creds["vercel"] = {
                "client_id": vid,
                "client_secret": _val(self.vercel_client_secret, "VERCEL_CLIENT_SECRET"),
            }
        if ghid := _val(self.github_client_id, "GITHUB_CLIENT_ID"):
            creds["github"] = {
                "client_id": ghid,
                "client_secret": _val(self.github_client_secret, "GITHUB_CLIENT_SECRET"),
            }
        if cvid := _val(self.canva_client_id, "CANVA_CLIENT_ID"):
            creds["canva"] = {
                "client_id": cvid,
                "client_secret": _val(self.canva_client_secret, "CANVA_CLIENT_SECRET"),
            }
        return creds

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment.lower() in {"production", "prod"}:
            if not self.jwt_secret_key or self.jwt_secret_key == "change-me-in-production":
                raise ValueError(
                    "jwt_secret_key must be set to a strong random secret in production"
                )
            if not self.encryption_key or len(self.encryption_key) != 64:
                raise ValueError(
                    "encryption_key must be set to a 32-byte (64 hex character) "
                    "string in production"
                )
            if self.encryption_key_previous.strip():
                for i, part in enumerate(self.encryption_key_previous.split(",")):
                    part = part.strip()
                    if not part:
                        continue
                    try:
                        key = bytes.fromhex(part)
                    except ValueError:
                        raise ValueError(
                            f"encryption_key_previous entry #{i + 1} {part!r} "
                            f"is not valid hex"
                        ) from None
                    if len(key) != 32:
                        raise ValueError(
                            f"encryption_key_previous entry #{i + 1} {part!r} "
                            f"is not 32 bytes (64 hex chars)"
                        )
        return self


settings = Settings()
