# Container image for the Customer Intelligence API (PDF §11 "Containerization").
# The LLM itself is NOT inside this image: it runs in Ollama, outside the container.
FROM python:3.13-slim

WORKDIR /app

# Install dependencies first, so Docker can reuse this layer when only the code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code, config and knowledge base.
COPY . .

# Where the container finds Ollama. host.docker.internal = "the computer running Docker".
# Override at run time with: docker run -e OLLAMA_HOST=http://other-host:11434 ...
ENV OLLAMA_HOST=http://host.docker.internal:11434

EXPOSE 8000

# 0.0.0.0 = accept connections from outside the container (127.0.0.1 would only accept from inside).
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
