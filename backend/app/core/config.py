from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Grupo EPA | Conciliação Bancária"
    database_url: str = "sqlite:///./epa_dev.db"
    secret_key: str = "development-only-change-before-deploy"
    access_token_minutes: int = 480
    max_upload_mb: int = 20
    storage_path: str = "./storage"
    allowed_origins: str = "http://localhost:5173"
    auth_mode: str = "development"
    environment: str = "development"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
