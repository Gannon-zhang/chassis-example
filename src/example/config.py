from __future__ import annotations

from pydantic_settings import SettingsConfigDict

from chassis_core.config import ChassisConfig


class ExampleConfig(ChassisConfig):
    """Example configuration with PostgreSQL and Redis.

    Extends ChassisConfig with sensible defaults for the Docker Compose
    environment. Override via environment variables:

        CHASSIS_DATABASE_URL=postgresql+asyncpg://user:pass@host/db
        CHASSIS_REDIS_URL=redis://host:6379
    """

    model_config = SettingsConfigDict(env_prefix="CHASSIS_", extra="allow")

    database_url: str = "postgresql+asyncpg://chassis:chassis@localhost:5432/chassis_example"
    redis_url: str = "redis://localhost:6379"
    app_name: str = "Book Library API"
    app_version: str = "0.1.0"
