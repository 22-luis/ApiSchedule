FROM python:3.10-slim AS backend
WORKDIR /app
COPY backend/ApiSchedule/ ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
