from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str

    database_url: str

    minio_endpoint: str
    minio_bucket_name: str
    minio_access_key: str
    minio_secret_key: str

    jwt_secret_key: str = "change_this_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore[arg-type]