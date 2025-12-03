from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "LinkLock"

    # MongoDB
    MONGO_URI: str
    MONGO_DB_NAME: str

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
