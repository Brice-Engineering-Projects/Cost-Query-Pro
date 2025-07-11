"""app/config/settings.py"""

import os
import logging
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, RedisDsn, Field
from typing import Optional


# -----------------------------------------------------------
# Auth setup
# -----------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


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

class Settings(BaseSettings):
    # General
    secret_key: str = Field("default_secret_key", env="SECRET_KEY")
    environment: str = Field("production", env="ENVIRONMENT")
    fastapi_debug: bool = Field(False, env="FASTAPI_DEBUG")
    testing: bool = Field(False, env="TESTING")

    # Database URLs
    database_url: Optional[PostgresDsn] = Field(None, env="DATABASE_URL")
    dev_database_url: Optional[PostgresDsn] = Field(None, env="DEV_DATABASE_URL")
    test_database_url: Optional[PostgresDsn] = Field(None, env="TEST_DATABASE_URL")

    # Redis / Session
    session_type: str = Field("filesystem", env="SESSION_TYPE")
    session_permanent: bool = Field(False, env="SESSION_PERMANENT")
    redis_url: Optional[RedisDsn] = Field("redis://localhost:6379/0", env="REDIS_URL")

    # SQLAlchemy Engine Options
    db_pool_size: int = Field(20, env="DB_POOL_SIZE")
    db_pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(1800, env="DB_POOL_RECYCLE")
    db_max_overflow: int = Field(10, env="DB_MAX_OVERFLOW")

    # Auth0
    auth0_client_id: Optional[str] = Field(None, env="AUTH0_CLIENT_ID")
    auth0_client_secret: Optional[str] = Field(None, env="AUTH0_CLIENT_SECRET")
    auth0_domain: Optional[str] = Field(None, env="AUTH0_DOMAIN")
    auth0_callback_url: Optional[str] = Field(None, env="AUTH0_CALLBACK_URL")
    auth0_audience: Optional[str] = Field(None, env="AUTH0_AUDIENCE")

    class Config:
        env_file = ".env"


settings = Settings()
