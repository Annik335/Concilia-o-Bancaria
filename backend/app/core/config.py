from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import shutil
from pathlib import Path

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

# Tesseract is resolved portably: Docker/Linux uses PATH, Windows can set TESSERACT_CMD.
# Do not hard-code a workstation path; native text PDFs must work even when OCR is absent.
try:
    import pytesseract
    _tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if _tesseract_cmd:
        resolved = shutil.which(_tesseract_cmd) or (_tesseract_cmd if Path(_tesseract_cmd).is_file() else None)
        if resolved:
            pytesseract.pytesseract.tesseract_cmd = resolved
except Exception:
    # OCR import reports a clear diagnostic only when OCR is actually requested.
    pass
