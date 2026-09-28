"""
fastapi app for the customer intelligence api.

    POST /process-customer-message   analyse one message
    GET  /health                     status + active model
    GET  /docs                       swagger ui

the web app in frontend/ runs on a different origin, hence the cors setup.
run: python -m uvicorn app:app --reload
"""

import os
import threading
import time
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from decision import load_config
from llm import MODEL_NAME, PROVIDER
from pipeline import process
from retriever import build_index


config = load_config()

# warm up the in-memory index so the first visitor doesn't pay for it.
# a request that arrives before it's done just builds the index itself.
if PROVIDER == "groq":
    threading.Thread(target=build_index, daemon=True).start()

app = FastAPI(
    title="Customer Intelligence API",
    description="Analyzes a bank customer message: intents, priority, routing, action and a grounded reply.",
    version="1.2",
)

# comma-separated frontend origins, defaults to the vite dev server
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---- rate limiting
# protects the free groq quota on the public demo.
# note: kept in memory, so it resets on restart and only works with a single instance.
MAX_PER_MINUTE_PER_VISITOR = 5
MAX_PER_DAY_PER_VISITOR = 50
MAX_PER_DAY_TOTAL = 400        # 2 llm calls per message, stays under groq's free daily cap

request_times_by_visitor = {}  # ip -> timestamps
request_times_all = []


def get_visitor_ip(request):
    # behind render's proxy the real client ip is in x-forwarded-for
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def keep_recent(times, now, seconds):
    recent = []
    for t in times:
        if now - t < seconds:
            recent.append(t)
    return recent


def count_recent(times, now, seconds):
    return len(keep_recent(times, now, seconds))


def check_rate_limit(ip):
    global request_times_all
    now = time.time()
    one_day = 24 * 60 * 60

    request_times_all = keep_recent(request_times_all, now, one_day)
    if len(request_times_all) >= MAX_PER_DAY_TOTAL:
        raise HTTPException(status_code=429, detail="The demo has reached its daily limit. Please come back tomorrow.")

    visitor_times = keep_recent(request_times_by_visitor.get(ip, []), now, one_day)
    if count_recent(visitor_times, now, 60) >= MAX_PER_MINUTE_PER_VISITOR:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute and try again.")
    if len(visitor_times) >= MAX_PER_DAY_PER_VISITOR:
        raise HTTPException(status_code=429, detail="You have reached today's limit for this demo. Thanks for trying it!")

    visitor_times.append(now)
    request_times_by_visitor[ip] = visitor_times
    request_times_all.append(now)


# ---- request / response models

class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, examples=["I was charged twice for the same transaction."])


class AnalysisResponse(BaseModel):
    """the output format from the task spec, plus the policy files used."""
    intents: List[str]
    issue_type: str
    priority: str
    entities: List[str]
    routing: str
    suggested_action: str
    response: str
    sources: List[str]


# ---- endpoints

@app.get("/", include_in_schema=False)
def home():
    return {"message": "Customer Intelligence API. See /docs for the endpoints."}


@app.get("/health")
def health():
    """status and the active model."""
    return {"status": "ok", "provider": PROVIDER, "model": MODEL_NAME}


@app.post("/process-customer-message", response_model=AnalysisResponse)
def process_customer_message(body: MessageRequest, request: Request):
    """analyse one customer message: intents, priority, routing, next action and a draft reply."""
    message = body.message.strip()
    if message == "":
        raise HTTPException(status_code=422, detail="Message must not be empty.")

    check_rate_limit(get_visitor_ip(request))

    try:
        result = process(message, config)
    except Exception as error:
        # usually ollama isn't running or the groq key is wrong.
        # details go to the server log, not to the visitor.
        print("Pipeline error:", repr(error))
        raise HTTPException(status_code=503, detail="The analysis service is temporarily unavailable.")
    return result
