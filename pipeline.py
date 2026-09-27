"""
pipeline.py - runs one customer message through the whole system.

    message -> LLM extraction -> rule-based decision -> retrieval -> grounded response -> final JSON

Usage:
    python pipeline.py "I was charged twice for the same transaction"
"""

import json
import sys
import time

from decision import clean_intents, decide, load_config
from llm import MODEL_NAME, extract, generate_response
from logger import log_request
from retriever import retrieve


def process(message, config):
    """Run the pipeline on one message, time it, and log it (including failures)."""
    start = time.perf_counter()
    try:
        result = run_pipeline(message, config)
    except Exception as error:
        latency = time.perf_counter() - start
        log_request(message, None, latency, MODEL_NAME, error=repr(error))
        raise  # still crash loudly after logging, so the problem is not hidden

    latency = time.perf_counter() - start
    log_request(message, result, latency, MODEL_NAME)
    return result


def run_pipeline(message, config):
    """Process one message and return the combined result as a dictionary."""
    # 1. Understanding layer (LLM)
    extraction = extract(message, config["intent_descriptions"])
    extraction.intents = clean_intents(extraction.intents, config)

    # 2. Decision layer (rules)
    decision = decide(extraction.intents, extraction.priority, config)

    # 3. Knowledge layer (RAG): skip retrieval when we don't know what the customer wants.
    if decision["suggested_action"] == "Request more info":
        chunks = []
    else:
        chunks = retrieve(message)

    response = generate_response(
        message, chunks, decision["routing"], decision["suggested_action"]
    )

    # List each source file once, in the order it was retrieved.
    sources = []
    for chunk in chunks:
        if chunk["source"] not in sources:
            sources.append(chunk["source"])

    # Combine everything into the final output (PDF §5).
    result = extraction.model_dump()          # Pydantic object -> dictionary
    result["routing"] = decision["routing"]
    result["suggested_action"] = decision["suggested_action"]
    result["response"] = response
    result["sources"] = sources
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python pipeline.py "customer message here"')
        sys.exit(1)

    config = load_config()
    message = sys.argv[1]
    result = process(message, config)
    print(json.dumps(result, indent=2))
