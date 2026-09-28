# api image. the llm isn't in here: it runs in ollama (local) or on groq (hosted).
FROM python:3.13-slim

WORKDIR /app

# deps first so code changes don't reinstall everything
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# bake the embedding model into the image instead of downloading it on every cold start.
# os._exit(0) avoids a harmless crash in the hf downloader's threads on exit.
ENV FASTEMBED_CACHE=/app/models_cache
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='/app/models_cache'); import os; os._exit(0)"

COPY . .

# local mode: ollama running on the host machine
ENV OLLAMA_HOST=http://host.docker.internal:11434

EXPOSE 8000

# render sets $PORT, locally it's 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
