# SahaAI CFO – FastAPI + Uvicorn
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main_cfo.py cfo_api.py .
COPY static_cfo/ static_cfo/

# Run as non-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

# GEMINI_API_KEY must be set at runtime (e.g. via docker-compose env_file or -e)
CMD ["uvicorn", "main_cfo:app", "--host", "0.0.0.0", "--port", "8001"]
