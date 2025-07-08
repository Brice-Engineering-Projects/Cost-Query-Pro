"""app/config/settings.py"""

import logging
from pydantic import BaseSettings, PostgresDsn, RedisDsn, Field
from typing import Optional

# ------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('budget_app.log')
    ]
)

# ------------------------------------------------------------
# Pydantic Settings
# ------------------------------------------------------------

class Settings(BaseSettings):
    # General
    secret_key: str = Field("default_secret_key", env="SECRET_KEY")
    environment: str = Field("production", env="ENVIRONMENT")
    debug: bool = Field(False, env="FASTAPI_DEBUG")
    testing: bool = Field(False, env="TESTING")

    # Database
    database_url: Optional[PostgresDsn] = Field(None, env="DATABASE_URL")
    dev_database_url: Optional[PostgresDsn] = Field(None, env="DEV_DATABASE_URL")
    test_database_url: Optional[PostgresDsn] = Field(None, env="TEST_DATABASE_URL")

    # Redis / Session
    session_type: str = Field("filesystem", env="SESSION_TYPE")
    session_permanent: bool = Field(False, env="SESSION_PERMANENT")
    redis_url: Optional[RedisDsn] = Field("redis://localhost:6379/0", env="REDIS_URL")

    # SQLAlchemy Engine Options
    pool_size: int = Field(20, env="DB_POOL_SIZE")
    pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(1800, env="DB_POOL_RECYCLE")
    max_overflow: int = Field(10, env="DB_MAX_OVERFLOW")

    class Config:
        env_file = ".env"


settings = Settings()
