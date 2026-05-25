import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "LLM-Gateway"
    DEBUG: bool = False
    
    # Provider Secret Keys
    GEMINI_API_KEY: str
    
    # Infrastructure Backends
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Default Token Bucket Parameters (Can be made dynamic per team later)
    DEFAULT_RATE_LIMIT_RPM: int = 60  # Requests Per Minute allowed
    DEFAULT_BURST_CAPACITY: int = 10  # Maximum burst capacity of the bucket

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        extra="ignore"
    )

settings = Settings()