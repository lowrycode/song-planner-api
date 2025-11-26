from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    model_config = {
        "extra": "ignore",  # to allow for other variables in .env (e.g. test_db_url)
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
