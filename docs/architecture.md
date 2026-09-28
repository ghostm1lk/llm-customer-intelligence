# Architecture

## Request flow

```mermaid
flowchart TD
    IN["Customer message<br/>(CLI: pipeline.py · API: POST /process-customer-message)"]
    CFG[("config/taxonomy.yaml<br/>intents, definitions, teams, rules")]
    KB[("data/kb/*.md<br/>12 policy documents")]

    IN --> U
    subgraph PIPE ["pipeline.py"]
        U["1 · Understanding layer — llm.extract()<br/>Qwen3.5-4B via Ollama<br/>JSON schema enforced (Pydantic)"]
        G["clean_intents()<br/>drop 'Unclear' if a real intent exists"]
        D["2 · Decision layer — decision.decide()<br/>rule-based routing + suggested action"]
        K["3 · Knowledge layer — retriever.retrieve()<br/>nomic-embed-text + Chroma, top-3 chunks"]
        R["Response generation — llm.generate_response()<br/>grounded in retrieved policy, cites sources"]
        U --> G --> D
        D -- "Escalate / Respond" --> K --> R
        D -- "Request more info<br/>(no retrieval)" --> R
    end

    CFG -. "intent definitions" .-> U
    CFG -. "routing and escalation rules" .-> D
    KB -. "chunked and embedded" .-> K

    R --> OUT["JSON output<br/>intents · issue_type · priority · entities ·<br/>routing · suggested_action · response · sources"]
    PIPE --> LOG[("logger.py → logs/requests.jsonl<br/>input, output, latency, errors")]
```

## Layers (PDF §8)

| PDF layer | Implementation |
|---|---|
| 1. Input Layer | `pipeline.py` (CLI), `app.py` (FastAPI, input validated by Pydantic) |
| 2. Prompt Engineering Layer | `llm.build_system_prompt()` — role, intent definitions from the taxonomy, priority guide |
| 3. LLM Reasoning Layer | `llm.extract()` — Qwen3.5-4B, temperature 0, thinking off |
| 4. Retrieval Layer (Vector DB) | `retriever.py` — 71 chunks, nomic-embed-text embeddings, Chroma (cosine) |
| 5. Output Structuring Layer | Ollama constrained decoding with the Pydantic JSON schema + `model_validate_json` |
| 6. Logging Layer | `logger.py` — one JSON line per request, including failures |

The decision layer (`decision.py`) sits between reasoning and retrieval: the LLM **extracts**, deterministic rules **decide**.

**Two backends.** The diagram shows local mode. With `LLM_PROVIDER=groq`, `llm.py` calls `openai/gpt-oss-20b` on Groq (strict JSON schema), and `retriever.py` uses `bge-small-en-v1.5` in-process (fastembed) with an in-memory search instead of Ollama + Chroma. The decision rules, prompts, logging and API are identical in both modes. The React web app in `frontend/` calls the same API.

## Deployment

```mermaid
flowchart LR
    subgraph MAC ["Development (MacBook, Apple Silicon)"]
        O1["Ollama app (native)<br/>uses the M2 GPU"]
        A1["API container<br/>docker run -p 8000:8000"]
        A1 -- "host.docker.internal:11434" --> O1
    end
    subgraph SRV ["On-premise server (docker compose)"]
        O2["ollama container<br/>(GPU)"]
        A2["api container"]
        A2 -- "ollama:11434" --> O2
    end
    subgraph RND ["Public demo (Render, free plan)"]
        W["Static site<br/>React web app<br/>customer-intel-cgsp.onrender.com"]
        A3["Web service (Docker)<br/>API + fastembed<br/>customer-intel-w6ht.onrender.com"]
        W -- "VITE_API_URL<br/>(allowed by CORS)" --> A3
    end
    A3 -- "GROQ_API_KEY" --> G["Groq API<br/>openai/gpt-oss-20b"]
```

The public demo uses `LLM_PROVIDER=groq`, so its API container needs no GPU and fits Render's free plan (512 MB RAM). The web app is served separately as static files, so it loads instantly even while the API is waking up from sleep.

The model always runs as a **separate service** from the API: the API image stays small, the model can use a GPU, and either can be updated or scaled without rebuilding the other. The API only needs the `OLLAMA_HOST` environment variable to find it.
