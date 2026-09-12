from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://dhansaathi:dhansaathi@localhost:5433/dhansaathi"
    model_version: str = "1.0.0"
    data_locality: str = "strict"
    enforce_consent: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
