from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class AppSettings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "interview-ai"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    default_model_name: str = "claude-3-5-sonnet-latest"
    websocket_heartbeat_seconds: int = 30

    feishu_app_id: str = Field(default="", alias="FEISHU_APP_ID")
    feishu_app_secret: str = Field(default="", alias="FEISHU_APP_SECRET")
    feishu_base_url: str = Field(default="https://open.feishu.cn", alias="FEISHU_BASE_URL")
    feishu_table_app_token: str = Field(default="", alias="FEISHU_TABLE_APP_TOKEN")
    feishu_table_session: str = Field(default="", alias="FEISHU_TABLE_SESSION")

    supervisor_prompt_path: Path = ROOT_DIR / "configs/prompts/supervisor.txt"
    hr_prompt_path: Path = ROOT_DIR / "configs/prompts/hr_agent.txt"
    tech_prompt_path: Path = ROOT_DIR / "configs/prompts/tech_agent.txt"
    manager_prompt_path: Path = ROOT_DIR / "configs/prompts/manager_agent.txt"

    def load_prompt(self, path: Path) -> str:
        return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()

