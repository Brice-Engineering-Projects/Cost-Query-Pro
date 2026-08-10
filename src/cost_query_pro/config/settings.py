"""src/cost_query_pro/config/settings.py"""

import logging
from typing import Optional

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

# ------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("cost_query_pro.log")],
)

# ------------------------------------------------------------
# Pydantic Settings
# ------------------------------------------------------------


class GeneralSettings(BaseSettings):
    """General application settings"""

    secret_key: str = Field(..., min_length=32)
    environment: str = Field("development")
    fastapi_debug: bool = Field(False)
    testing: bool = Field(False)


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""

    database_url: Optional[PostgresDsn] = Field(None)
    dev_database_url: Optional[PostgresDsn] = Field(None)
    test_database_url: Optional[PostgresDsn] = Field(None)

    # SQLAlchemy Engine Options
    db_pool_size: int = Field(20)
    db_pool_timeout: int = Field(30)
    db_pool_recycle: int = Field(1800)
    db_max_overflow: int = Field(10)


class SessionSettings(BaseSettings):
    """Session and Redis configuration"""

    session_type: str = Field("filesystem")
    session_permanent: bool = Field(False)
    redis_url: Optional[RedisDsn] = Field(None)


class AuthSettings(BaseSettings):
    """Authentication configuration"""

    model_config = SettingsConfigDict(populate_by_name=True)

    # Auth0 settings
    auth0_client_id: Optional[str] = Field(None)
    auth0_client_secret: Optional[str] = Field(None)
    auth0_domain: Optional[str] = Field(None)
    auth0_callback_url: Optional[str] = Field(None)
    auth0_audience: Optional[str] = Field(None)

    # Auth config
    access_token_expire_minutes: int = Field(60)
    algorithm: str = Field("HS256")
    allow_admin_signup: bool = Field(False)


class Settings(BaseSettings):
    """Main application settings with all configuration fields"""

    # General settings
    secret_key: str = Field(..., min_length=32)
    environment: str = Field("development")
    fastapi_debug: bool = Field(False)
    testing: bool = Field(False)
    api_base_url: str = "http://127.0.0.1:8000/api/v1"

    # Database settings
    database_url: Optional[PostgresDsn] = Field(None)
    dev_database_url: Optional[PostgresDsn] = Field(None)
    test_database_url: Optional[PostgresDsn] = Field(None)
    db_pool_size: int = Field(20)
    db_pool_timeout: int = Field(30)
    db_pool_recycle: int = Field(1800)
    db_max_overflow: int = Field(10)

    # Session settings
    session_type: str = Field("filesystem")
    session_permanent: bool = Field(False)
    redis_url: Optional[RedisDsn] = Field(None)

    # Auth settings
    auth0_client_id: Optional[str] = Field(None)
    auth0_client_secret: Optional[str] = Field(None)
    auth0_domain: Optional[str] = Field(None)
    auth0_callback_url: Optional[str] = Field(None)
    auth0_audience: Optional[str] = Field(None)
    access_token_expire_minutes: int = Field(60)
    algorithm: str = Field("HS256")
    allow_admin_signup: bool = Field(False)
    password_min_length: int = Field(8)

    # LLM provider settings
    anthropic_api_key: Optional[str] = Field(None)
    openai_api_key: Optional[str] = Field(None)
    llm_provider: str = Field("claude")  # "claude" | "openai"
    claude_model: str = Field("claude-sonnet-4-6")
    openai_model: str = Field("gpt-4o")
    agent_prompt_version: str = Field("1.0.0")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_prefix="",
        populate_by_name=True,
    )

    # Convenience property accessors for organized access
    @property
    def general(self) -> GeneralSettings:
        """Access general settings as a grouped object"""
        return GeneralSettings(
            secret_key=self.secret_key,
            environment=self.environment,
            fastapi_debug=self.fastapi_debug,
            testing=self.testing,
        )

    @property
    def database(self) -> DatabaseSettings:
        """Access database settings as a grouped object"""
        return DatabaseSettings(
            database_url=self.database_url,
            dev_database_url=self.dev_database_url,
            test_database_url=self.test_database_url,
            db_pool_size=self.db_pool_size,
            db_pool_timeout=self.db_pool_timeout,
            db_pool_recycle=self.db_pool_recycle,
            db_max_overflow=self.db_max_overflow,
        )

    @property
    def session(self) -> SessionSettings:
        """Access session settings as a grouped object"""
        return SessionSettings(
            session_type=self.session_type,
            session_permanent=self.session_permanent,
            redis_url=self.redis_url,
        )

    @property
    def auth(self) -> AuthSettings:
        """Access auth settings as a grouped object"""
        return AuthSettings(
            auth0_client_id=self.auth0_client_id,
            auth0_client_secret=self.auth0_client_secret,
            auth0_domain=self.auth0_domain,
            auth0_callback_url=self.auth0_callback_url,
            auth0_audience=self.auth0_audience,
            access_token_expire_minutes=self.access_token_expire_minutes,
            algorithm=self.algorithm,
            allow_admin_signup=self.allow_admin_signup,
        )


settings = Settings()  # type: ignore[call-arg]
