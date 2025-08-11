FROM python:3.10-slim AS backend
WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .
EXPOSE 8080

# The CMD command now uses the PORT environment variable if it exists, otherwise it defaults to 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
