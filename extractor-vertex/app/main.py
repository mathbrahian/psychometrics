import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="extractor-vertex")

cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def hello():
    return {"message": "Hola mundo desde extractor-vertex"}


@app.get("/health")
def health():
    return {"status": "ok"}
