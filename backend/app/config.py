from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str

    database_url: str

    minio_endpoint: str
    minio_bucket_name: str
    minio_access_key: str
    minio_secret_key: str

    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore[arg-type]