from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import Base, engine
from app.api.routes import router
from app.models import entities  # noqa: F401 - registers SQLAlchemy models

import pytesseract
import sys

# Aponta o pytesseract para o caminho correto no Windows
if sys.platform == "win32":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
    if settings.environment.lower() == "development" and settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title=settings.app_name, version="1.0.0", description="API de conciliação bancária do Grupo EPA", lifespan=lifespan)
origins = [x.strip() for x in settings.allowed_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET","POST","PATCH","DELETE"], allow_headers=["Authorization","Content-Type"])
app.include_router(router)

@app.get("/")
def root():
    return {"application": settings.app_name, "api": "/docs", "status": "online"}
