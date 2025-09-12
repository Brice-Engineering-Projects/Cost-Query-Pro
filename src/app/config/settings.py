"""src/app/config/settings.py"""

import os
import logging
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, RedisDsn, Field, ConfigDict
from typing import Optional


# ------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cost_query_pro.log')
    ]
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
    """Main application settings composed of specialized setting classes"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.general = GeneralSettings()
        self.database = DatabaseSettings()
        self.session = SessionSettings()
        self.auth = AuthSettings()

    # Backward compatibility properties
    @property
    def secret_key(self) -> str:
        return self.general.secret_key

    @property
    def environment(self) -> str:
        return self.general.environment

    @property
    def fastapi_debug(self) -> bool:
        return self.general.fastapi_debug

    @property
    def testing(self) -> bool:
        return self.general.testing

    @property
    def database_url(self) -> Optional[PostgresDsn]:
        return self.database.database_url

    @property
    def test_database_url(self) -> Optional[PostgresDsn]:
        return self.database.test_database_url

    @property
    def allow_admin_signup(self) -> bool:
        return self.auth.allow_admin_signup

    @allow_admin_signup.setter
    def allow_admin_signup(self, value: bool):
        self.auth.allow_admin_signup = value

    model_config = ConfigDict(env_file=".env")

settings = Settings()
