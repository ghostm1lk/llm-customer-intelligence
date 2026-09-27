# LLM-Based Customer Intelligence System

An AI assistant for bank customer-service teams. It reads a customer message and returns structured, explainable intelligence: **what the customer wants, how urgent it is, which team should handle it, what to do next, and a draft reply grounded in the bank's policies**.

Built for the PIO-TECH Internship Program (Task 3). Runs fully locally with a small open-source LLM.

```text
Input:  "I was charged twice for the same transaction and I need this resolved immediately. If not, I will escalate."
```
```json
{
  "intents": ["Billing Issue", "Refund Request", "Complaint"],
  "issue_type": "Duplicate charge",
  "priority": "High",
  "entities": ["duplicate transaction", "escalation threat"],
  "routing": "Billing Department",
  "suggested_action": "Escalate",
  "response": "I understand your concern about the duplicate charge and will forward your request to our Billing Department for immediate review [duplicate_charges.md]. ...",
  "sources": ["duplicate_charges.md"]
}
```

## How it works

| Layer | What it does | File |
|---|---|---|
| **Understanding** | The LLM extracts intents, issue type, priority and entities. Output is forced into a JSON schema. | `llm.py` |
| **Decision** | Deterministic rules turn intents + priority into a routing team and a suggested action. | `decision.py`, `config/taxonomy.yaml` |
| **Knowledge (RAG)** | Retrieves the most relevant policy passages from a vector database. | `retriever.py`, `data/kb/` |
| **Response** | The LLM drafts a short reply using only the retrieved policy text and cites the source. | `llm.py` |
| **Logging** | Every request (input, output, latency, errors) is appended to `logs/requests.jsonl`. | `logger.py` |

**Design idea: the LLM extracts, the rules decide.** Routing and escalation are business rules, so they live in code and config where they are predictable, testable and explainable. The small LLM only does what it is good at: reading language.

See [docs/architecture.md](docs/architecture.md) for the full diagram.

## Tech stack

Python 3.13 · [Ollama](https://ollama.com) · Qwen3.5-4B · nomic-embed-text · Chroma · Pydantic · FastAPI · Docker

## Project structure

```text
├── app.py                  FastAPI app: POST /process-customer-message, GET /health
├── pipeline.py             Runs the full pipeline for one message (also usable as a CLI)
├── llm.py                  Extraction prompt + JSON schema, grounded response generation
├── decision.py             Rule-based routing and suggested action
├── retriever.py            Chunking, embeddings and Chroma search over data/kb/
├── logger.py               Request logging
├── evaluate.py             Evaluation (PDF §10)
├── check_dataset.py        Validates the dataset against the PDF §7 requirements
├── config/taxonomy.yaml    Intents, definitions, teams and escalation rules (editable)
├── data/messages.jsonl     60 labeled customer messages
├── data/kb/                12 policy documents (fictional bank "Nova Bank")
├── eval/                   Evaluation results for each version
├── docs/                   Architecture diagram and evaluation report
├── Dockerfile, docker-compose.yml, requirements.txt
```

## Setup

**1. Install Ollama** from [ollama.com/download](https://ollama.com/download) (macOS 14+), start it, and download the models:

```bash
ollama pull qwen3.5:4b          # LLM, ~3.4 GB
ollama pull nomic-embed-text    # embedding model, ~270 MB
```

**2. Install the Python dependencies:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Build the vector database and run the self-checks:**

```bash
python retriever.py        # indexes data/kb/ into chroma_db/ (rerun after editing data/kb/)
python decision.py         # checks the routing rules
python check_dataset.py    # checks the dataset
```

## Usage

**Command line**

```bash
python pipeline.py "My card was stolen this morning, please block it!"
```

**REST API**

```bash
python -m uvicorn app:app --reload
```

Open http://127.0.0.1:8000/docs for interactive documentation, or:

```bash
curl -X POST http://127.0.0.1:8000/process-customer-message \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the interest rate for a personal loan?"}'
```

| Status | Meaning |
|---|---|
| 200 | Analysis returned |
| 422 | Invalid input (empty, missing, or over 2000 characters) |
| 503 | Model service unavailable (e.g. Ollama not running) |

## Docker

The model runs as a separate service (Ollama); the container holds the API, rules, knowledge base and vector database.

**On a Mac** (Ollama runs natively so it can use the Apple GPU):

```bash
docker build -t customer-intel .
docker run -p 8000:8000 customer-intel
```

**On a Linux server** (both as containers):

```bash
docker compose up -d --build
docker compose exec ollama ollama pull qwen3.5:4b
docker compose exec ollama ollama pull nomic-embed-text
```

The API finds the model through the `OLLAMA_HOST` environment variable.

## Configuration

All business rules are in [`config/taxonomy.yaml`](config/taxonomy.yaml), no code changes needed:

- `intents` — every intent and the team it routes to
- `intent_descriptions` — the definition the LLM sees for each intent
- `team_order` — which team wins when a message has several intents (highest risk first)
- `escalate_teams`, `escalate_priorities` — when to escalate
- `default_team`, `unclear_intent` — fallbacks for vague messages

## Evaluation

```bash
caffeinate -i python evaluate.py     # ~15 min on a MacBook Air M2 (caffeinate keeps the Mac awake)
```

Final results (v3) on 60 labeled messages:

| Metric | Result |
|---|---|
| Routing accuracy | 96.7% |
| Suggested action accuracy | 91.7% |
| Intent F1 | 0.866 |
| Priority accuracy | 78.3% |
| Retrieval hit@3 | 83.0% |
| Replies with no invented numbers | 100% |
| Consistency (same input → same output) | 100% |
| Complete structured outputs | 100% |

Full results, the three improvement iterations, error analysis and limitations: **[docs/evaluation_report.md](docs/evaluation_report.md)**.

## Key design decisions

- **Local model (Qwen3.5-4B via Ollama).** No customer data leaves the machine and there are no API costs; small enough for an 8 GB laptop.
- **Constrained JSON decoding.** The model cannot produce invalid JSON or an unknown priority, instead of retrying on bad output.
- **Rules for decisions.** Fraud always escalates, even when the customer writes calmly and the model rates it Low.
- **Safety guard.** If the model marks a message both *Unclear* and a real intent, *Unclear* is dropped, so a fraud report is never answered with "please give more details".
- **Grounded replies.** The reply may only use facts from the retrieved policies and must cite them; evaluation checks that no fee, deadline or rate is invented.
- **Temperature 0.** Deterministic, reproducible outputs.

## PDF requirements

| Requirement | Where |
|---|---|
| §4 Understanding, Decision and Knowledge layers | `llm.py`, `decision.py`, `retriever.py` |
| §6 CLI / API input, JSON enforced, RAG, configurable taxonomy, logging | `pipeline.py`, `app.py`, `llm.py`, `retriever.py`, `config/`, `logger.py` |
| §7 Dataset (30–100 messages, ≥10 ambiguous, ≥5 needing retrieval) | `data/messages.jsonl` (60 / 13 / 24) |
| §8 Modular pipeline | see [docs/architecture.md](docs/architecture.md) |
| §10 Evaluation | `evaluate.py`, [docs/evaluation_report.md](docs/evaluation_report.md) |
| §11 REST API, Docker, observability | `app.py`, `Dockerfile`, `docker-compose.yml`, `logger.py` |
| §12 Deliverables | this repository |

## Author

Waleed Abdellatif — Computer Science, German Jordanian University
