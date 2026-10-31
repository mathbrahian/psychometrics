from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="extractor-vertex")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def hello():
    return {"message": "Hola mundo desde extractor-vertex"}


@app.get("/health")
def health():
    return {"status": "ok"}
