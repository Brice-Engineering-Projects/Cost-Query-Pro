"""src/cost_query_pro/config/settings.py"""

import logging
from typing import Optional

from pydantic import ConfigDict, Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings

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

    secret_key: str = Field("default_secret_key", env="SECRET_KEY")
    environment: str = Field("production", env="ENVIRONMENT")
    fastapi_debug: bool = Field(False, env="FASTAPI_DEBUG")
    testing: bool = Field(False, env="TESTING")


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""

    database_url: Optional[PostgresDsn] = Field(None, env="DATABASE_URL")
    dev_database_url: Optional[PostgresDsn] = Field(None, env="DEV_DATABASE_URL")
    test_database_url: Optional[PostgresDsn] = Field(None, env="TEST_DATABASE_URL")

    # SQLAlchemy Engine Options
    db_pool_size: int = Field(20, env="DB_POOL_SIZE")
    db_pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(1800, env="DB_POOL_RECYCLE")
    db_max_overflow: int = Field(10, env="DB_MAX_OVERFLOW")


class SessionSettings(BaseSettings):
    """Session and Redis configuration"""

    session_type: str = Field("filesystem", env="SESSION_TYPE")
    session_permanent: bool = Field(False, env="SESSION_PERMANENT")
    redis_url: Optional[RedisDsn] = Field("redis://localhost:6379/0", env="REDIS_URL")


class AuthSettings(BaseSettings):
    """Authentication configuration"""

    # Auth0 settings
    auth0_client_id: Optional[str] = Field(None, env="AUTH0_CLIENT_ID")
    auth0_client_secret: Optional[str] = Field(None, env="AUTH0_CLIENT_SECRET")
    auth0_domain: Optional[str] = Field(None, env="AUTH0_DOMAIN")
    auth0_callback_url: Optional[str] = Field(None, env="AUTH0_CALLBACK_URL")
    auth0_audience: Optional[str] = Field(None, env="AUTH0_AUDIENCE")

    # Auth config
    access_token_expire_minutes: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = Field("HS256", env="ALGORITHM")
    allow_admin_signup: bool = Field(default=False, alias="ALLOW_ADMIN_SIGNUP")


class Settings(BaseSettings):
    """Main application settings with all configuration fields"""

    # General settings
    secret_key: str = Field("default_secret_key", env="SECRET_KEY")
    environment: str = Field("production", env="ENVIRONMENT")
    fastapi_debug: bool = Field(False, env="FASTAPI_DEBUG")
    testing: bool = Field(False, env="TESTING")
    api_base_url: str = "http://127.0.0.1:8000/api/v1"

    # Database settings
    database_url: Optional[PostgresDsn] = Field(None, env="DATABASE_URL")
    dev_database_url: Optional[PostgresDsn] = Field(None, env="DEV_DATABASE_URL")
    test_database_url: Optional[PostgresDsn] = Field(None, env="TEST_DATABASE_URL")
    db_pool_size: int = Field(20, env="DB_POOL_SIZE")
    db_pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(1800, env="DB_POOL_RECYCLE")
    db_max_overflow: int = Field(10, env="DB_MAX_OVERFLOW")

    # Session settings
    session_type: str = Field("filesystem", env="SESSION_TYPE")
    session_permanent: bool = Field(False, env="SESSION_PERMANENT")
    redis_url: Optional[RedisDsn] = Field("redis://localhost:6379/0", env="REDIS_URL")

    # Auth settings
    auth0_client_id: Optional[str] = Field(None, env="AUTH0_CLIENT_ID")
    auth0_client_secret: Optional[str] = Field(None, env="AUTH0_CLIENT_SECRET")
    auth0_domain: Optional[str] = Field(None, env="AUTH0_DOMAIN")
    auth0_callback_url: Optional[str] = Field(None, env="AUTH0_CALLBACK_URL")
    auth0_audience: Optional[str] = Field(None, env="AUTH0_AUDIENCE")
    access_token_expire_minutes: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    algorithm: str = Field("HS256", env="ALGORITHM")
    allow_admin_signup: bool = Field(default=False, alias="ALLOW_ADMIN_SIGNUP")

    model_config = ConfigDict(env_file=".env")

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


settings = Settings()
