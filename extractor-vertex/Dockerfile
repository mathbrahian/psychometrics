# Se construye desde la raíz del repositorio, para poder copiar la librería compartida:
#   docker build -f extractor-vertex/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY libs/questionnaire-core /opt/questionnaire-core
COPY extractor-vertex/requirements.txt .
RUN pip install --no-cache-dir /opt/questionnaire-core -r requirements.txt

COPY extractor-vertex/app ./app

EXPOSE 8080

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
