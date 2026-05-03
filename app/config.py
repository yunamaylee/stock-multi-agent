from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    fmp_api_key: str
    perplexity_api_key: str
    chroma_db_path: str
    app_env: str
    app_port: int

    class Config:
        env_file = ".env"


settings = Settings()