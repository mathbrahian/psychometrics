from fastapi import FastAPI

app = FastAPI(title="extractor-vertex")


@app.get("/")
def hello():
    return {"message": "Hola mundo desde extractor-vertex"}


@app.get("/health")
def health():
    return {"status": "ok"}
