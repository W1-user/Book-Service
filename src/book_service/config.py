import os
from pathlib import Path
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()
ENGINE = os.getenv("SQLALCHEMY_URL")
BASEDIR = Path(__file__).parent.parent

class DBSettings(BaseModel):
    engine: str = ENGINE
    echo: bool = True
    expire_on_commit: bool = False

class AuthSettings(BaseModel):
    private_key_path: Path = BASEDIR / "book_service" / "certs" / "private-key.pem"
    public_key_path: Path = BASEDIR / "book_service" / "certs" / "public-key.pem"
    algorithm: str = "RS256"

    #minutes
    expire_access_token: int = 15

    #days
    expire_refresh_token: int = 30

class Settings(BaseSettings):
    default_prefix: str = "/api/v1"
    db: DBSettings = DBSettings()
    auth: AuthSettings = AuthSettings()


settings = Settings()
