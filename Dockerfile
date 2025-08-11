FROM python:3.10-slim AS backend

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

RUN adduser --disabled-password appuser && chown -R appuser /app
USER appuser

CMD sh -c 'uvicorn app.main:app --host 0.0.0.0 --port $PORT'
