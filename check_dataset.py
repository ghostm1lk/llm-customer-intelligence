"""
check_dataset.py - checks data/messages.jsonl against the PDF's §7 requirements.

Run:
    python check_dataset.py
"""

import json
import os

from decision import load_config


def load_messages(path="data/messages.jsonl"):
    """Read the JSONL file: one JSON object per line -> a list of dictionaries."""
    messages = []
    with open(path) as file:
        for line in file:
            line = line.strip()
            if line == "":
                continue
            messages.append(json.loads(line))
    return messages


if __name__ == "__main__":
    config = load_config()
    messages = load_messages()

    total = len(messages)
    multi_intent = 0
    ambiguous = 0
    requires_retrieval = 0
    has_relevant_doc = 0
    high_or_critical = 0
    intent_counts = {}

    for message in messages:
        # Every label must be a real intent and every doc must exist.
        for intent in message["intents"]:
            assert intent in config["intents"], message["id"] + ": unknown intent " + intent
            if intent not in intent_counts:
                intent_counts[intent] = 0
            intent_counts[intent] = intent_counts[intent] + 1
        for doc in message["relevant_docs"]:
            doc_path = os.path.join("data", "kb", doc)
            assert os.path.exists(doc_path), message["id"] + ": missing doc " + doc

        if len(message["intents"]) > 1:
            multi_intent = multi_intent + 1
        if message["ambiguous"]:
            ambiguous = ambiguous + 1
        if message["requires_retrieval"]:
            assert len(message["relevant_docs"]) > 0, message["id"] + ": requires retrieval but has no doc"
            requires_retrieval = requires_retrieval + 1
        if len(message["relevant_docs"]) > 0:
            has_relevant_doc = has_relevant_doc + 1
        if message["priority"] in ["High", "Critical"]:
            high_or_critical = high_or_critical + 1

    print("Total messages:     ", total, "(PDF: 30-100)")
    print("Multi-intent:       ", multi_intent)
    print("High/Critical:      ", high_or_critical)
    print("Ambiguous:          ", ambiguous, "(PDF: at least 10)")
    print("Requires retrieval: ", requires_retrieval, "(PDF: at least 5)")
    print("Has a relevant doc: ", has_relevant_doc, "(used to evaluate retrieval)")
    print()
    print("Messages per intent:")
    for intent in intent_counts:
        print("   ", intent, ":", intent_counts[intent])

    assert 30 <= total <= 100, "Dataset must have 30-100 messages"
    assert ambiguous >= 10, "Need at least 10 ambiguous messages"
    assert requires_retrieval >= 5, "Need at least 5 messages that require retrieval"
    print()
    print("Dataset check passed.")