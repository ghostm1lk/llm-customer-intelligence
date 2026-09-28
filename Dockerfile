# Container image for the Customer Intelligence API (PDF §11 "Containerization").
# The LLM itself is NOT inside this image: it runs in Ollama (local mode) or on Groq (hosted mode).
FROM python:3.13-slim

WORKDIR /app

# Install dependencies first, so Docker can reuse this layer when only the code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Hosted mode: download the small embedding model now, so it is part of the image and
# is not downloaded again every time the server starts. os._exit(0) skips a harmless
# shutdown crash in the downloader's background threads.
ENV FASTEMBED_CACHE=/app/models_cache
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='/app/models_cache'); import os; os._exit(0)"

# Copy the application code, config and knowledge base.
COPY . .

# Local mode: where the container finds Ollama. host.docker.internal = "the computer running Docker".
# Override at run time with: docker run -e OLLAMA_HOST=http://other-host:11434 ...
ENV OLLAMA_HOST=http://host.docker.internal:11434

EXPOSE 8000

# Hosts like Render tell the app which port to use in $PORT; locally it falls back to 8000.
# 0.0.0.0 = accept connections from outside the container (127.0.0.1 would only accept from inside).
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
