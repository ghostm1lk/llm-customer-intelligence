"""
evaluation over the labeled dataset in data/messages.jsonl.

measures:
    output quality   intent exact match + precision/recall/f1, priority, routing,
                     action accuracy, completeness
    retrieval        hit@1 / hit@3 against the labeled docs
    groundedness     reply cites a source, and has no numbers that aren't in the
                     retrieved policy text or the message
    consistency      same message 3x -> same output, reworded message -> same decision

writes eval/results.jsonl (per message) and eval/summary.json.
takes ~10-15 min on an m2 air: python evaluate.py
"""

import json
import os
import re
import time

from check_dataset import load_messages
from decision import load_config
from pipeline import process
from retriever import retrieve


RESULTS_DIR = "eval"

# consistency: these messages are run CONSISTENCY_RUNS times each
CONSISTENCY_RUNS = 3
CONSISTENCY_IDS = ["M001", "M004", "M011", "M015", "M019", "M028", "M035", "M044", "M049", "M057"]

# robustness: rewordings of dataset messages, should get the original's routing and action
ROBUSTNESS_CASES = [
    ("M001", "i got charged 2 times for one purchase!! fix it now or im escalating"),
    ("M011", "Someone bought something for 350 JOD with my card on a site I don't know. It wasn't me."),
    ("M013", "stolen wallet, debit card inside, block it immediately"),
    ("M025", "App won't let me sign in - says wrong password every time"),
    ("M035", "how much interest do you charge on personal loans"),
    ("M040", "Are you open on Saturdays and until when?"),
    ("M045", "40 minutes on hold. Your support is awful."),
    ("M048", "doesnt work"),
]


# ---- helpers

def percent(part, total):
    # e.g. "45/60 (75.0%)"
    if total == 0:
        return "0/0 (n/a)"
    value = round(100 * part / total, 1)
    return str(part) + "/" + str(total) + " (" + str(value) + "%)"


def compare_intents(expected, predicted):
    true_pos = 0
    false_pos = 0
    false_neg = 0
    for intent in predicted:
        if intent in expected:
            true_pos = true_pos + 1
        else:
            false_pos = false_pos + 1
    for intent in expected:
        if intent not in predicted:
            false_neg = false_neg + 1
    return true_pos, false_pos, false_neg


def is_complete(result):
    required = ["intents", "issue_type", "priority", "routing", "suggested_action", "response"]
    for field in required:
        if field not in result:
            return False
        if result[field] is None or result[field] == "" or result[field] == []:
            return False
    return True


def find_numbers(text):
    # "within 24 hours, 5.5%" -> ["24", "5.5"]
    return re.findall(r"\d+(?:\.\d+)?", text)


def ungrounded_numbers(response, message, chunks):
    """numbers in the reply that aren't in the retrieved policy text or the message itself."""
    allowed_text = message
    for chunk in chunks:
        allowed_text = allowed_text + " " + chunk["text"]
    allowed_numbers = find_numbers(allowed_text)

    missing = []
    for number in find_numbers(response):
        if number not in allowed_numbers:
            missing.append(number)
    return missing


def cites_a_source(response, sources):
    for source in sources:
        if source in response:
            return True
    return False


# ---- output quality

def evaluate_dataset(messages, config):
    rows = []
    counter = 0
    for message in messages:
        counter = counter + 1
        print("[" + str(counter) + "/" + str(len(messages)) + "]", message["id"], message["text"][:60])

        start = time.perf_counter()
        try:
            result = process(message["text"], config)
            error = None
        except Exception as caught:
            result = {}
            error = repr(caught)
        latency = time.perf_counter() - start

        predicted_intents = result.get("intents", [])
        true_pos, false_pos, false_neg = compare_intents(message["intents"], predicted_intents)

        row = {
            "id": message["id"],
            "text": message["text"],
            "error": error,
            "latency_seconds": round(latency, 2),
            "expected_intents": message["intents"],
            "predicted_intents": predicted_intents,
            "intents_exact": sorted(message["intents"]) == sorted(predicted_intents),
            "intent_tp": true_pos,
            "intent_fp": false_pos,
            "intent_fn": false_neg,
            "expected_priority": message["priority"],
            "predicted_priority": result.get("priority"),
            "expected_routing": message["routing"],
            "predicted_routing": result.get("routing"),
            "expected_action": message["suggested_action"],
            "predicted_action": result.get("suggested_action"),
            "complete": is_complete(result),
            "response": result.get("response", ""),
            "sources": result.get("sources", []),
            "relevant_docs": message["relevant_docs"],
            "requires_retrieval": message["requires_retrieval"],
        }

        # groundedness only makes sense when policy text was actually used
        if len(row["sources"]) > 0:
            chunks = retrieve(message["text"])  # deterministic, same chunks as the pipeline got
            row["cites_source"] = cites_a_source(row["response"], row["sources"])
            row["ungrounded_numbers"] = ungrounded_numbers(row["response"], message["text"], chunks)
        else:
            row["cites_source"] = None
            row["ungrounded_numbers"] = None

        rows.append(row)
    return rows


def summarize_quality(rows):
    total = len(rows)
    counts = {"exact": 0, "priority": 0, "routing": 0, "action": 0, "complete": 0, "errors": 0}
    tp = 0
    fp = 0
    fn = 0
    latencies = []
    grounded_total = 0
    cites = 0
    no_invented_numbers = 0

    for row in rows:
        if row["error"] is not None:
            counts["errors"] = counts["errors"] + 1
        if row["intents_exact"]:
            counts["exact"] = counts["exact"] + 1
        if row["predicted_priority"] == row["expected_priority"]:
            counts["priority"] = counts["priority"] + 1
        if row["predicted_routing"] == row["expected_routing"]:
            counts["routing"] = counts["routing"] + 1
        if row["predicted_action"] == row["expected_action"]:
            counts["action"] = counts["action"] + 1
        if row["complete"]:
            counts["complete"] = counts["complete"] + 1
        tp = tp + row["intent_tp"]
        fp = fp + row["intent_fp"]
        fn = fn + row["intent_fn"]
        latencies.append(row["latency_seconds"])

        if row["cites_source"] is not None:
            grounded_total = grounded_total + 1
            if row["cites_source"]:
                cites = cites + 1
            if len(row["ungrounded_numbers"]) == 0:
                no_invented_numbers = no_invented_numbers + 1

    precision = 0
    if tp + fp > 0:
        precision = tp / (tp + fp)
    recall = 0
    if tp + fn > 0:
        recall = tp / (tp + fn)
    f1 = 0
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)

    summary = {
        "messages": total,
        "errors": counts["errors"],
        "intent_exact_match": percent(counts["exact"], total),
        "intent_precision": round(precision, 3),
        "intent_recall": round(recall, 3),
        "intent_f1": round(f1, 3),
        "priority_accuracy": percent(counts["priority"], total),
        "routing_accuracy": percent(counts["routing"], total),
        "action_accuracy": percent(counts["action"], total),
        "complete_outputs": percent(counts["complete"], total),
        "replies_citing_a_source": percent(cites, grounded_total),
        "replies_with_no_invented_numbers": percent(no_invented_numbers, grounded_total),
        "avg_latency_seconds": round(sum(latencies) / total, 2),
        "max_latency_seconds": max(latencies),
    }
    return summary


# ---- retrieval quality

def evaluate_retrieval(messages):
    total = 0
    hit_at_1 = 0
    hit_at_3 = 0
    strict_total = 0
    strict_hit_at_3 = 0

    for message in messages:
        if len(message["relevant_docs"]) == 0:
            continue
        total = total + 1

        retrieved_sources = []
        for chunk in retrieve(message["text"], k=3):
            retrieved_sources.append(chunk["source"])

        if retrieved_sources[0] in message["relevant_docs"]:
            hit_at_1 = hit_at_1 + 1

        found = False
        for source in retrieved_sources:
            if source in message["relevant_docs"]:
                found = True
        if found:
            hit_at_3 = hit_at_3 + 1

        if message["requires_retrieval"]:
            strict_total = strict_total + 1
            if found:
                strict_hit_at_3 = strict_hit_at_3 + 1

    return {
        "messages_with_relevant_doc": total,
        "hit_at_1": percent(hit_at_1, total),
        "hit_at_3": percent(hit_at_3, total),
        "hit_at_3_requires_retrieval_only": percent(strict_hit_at_3, strict_total),
    }


# ---- consistency and robustness

def key_fields(result):
    return {
        "intents": sorted(result["intents"]),
        "priority": result["priority"],
        "routing": result["routing"],
        "suggested_action": result["suggested_action"],
    }


def evaluate_consistency(messages_by_id, config):
    stable = 0
    unstable_ids = []
    for message_id in CONSISTENCY_IDS:
        print("  consistency:", message_id)
        text = messages_by_id[message_id]["text"]
        first = key_fields(process(text, config))
        same = True
        for run in range(CONSISTENCY_RUNS - 1):
            if key_fields(process(text, config)) != first:
                same = False
        if same:
            stable = stable + 1
        else:
            unstable_ids.append(message_id)
    return {
        "runs_per_message": CONSISTENCY_RUNS,
        "stable_messages": percent(stable, len(CONSISTENCY_IDS)),
        "unstable_ids": unstable_ids,
    }


def evaluate_robustness(messages_by_id, config):
    passed = 0
    failures = []
    for original_id, reworded in ROBUSTNESS_CASES:
        print("  robustness:", original_id, "->", reworded[:50])
        expected = messages_by_id[original_id]
        result = process(reworded, config)
        same_routing = result["routing"] == expected["routing"]
        same_action = result["suggested_action"] == expected["suggested_action"]
        if same_routing and same_action:
            passed = passed + 1
        else:
            failures.append({
                "original_id": original_id,
                "reworded": reworded,
                "expected": [expected["routing"], expected["suggested_action"]],
                "got": [result["routing"], result["suggested_action"]],
            })
    return {
        "reworded_cases_passed": percent(passed, len(ROBUSTNESS_CASES)),
        "failures": failures,
    }


# ---- main

if __name__ == "__main__":
    config = load_config()
    messages = load_messages()
    messages_by_id = {}
    for message in messages:
        messages_by_id[message["id"]] = message

    print("== 1. Output quality (all", len(messages), "messages) ==")
    rows = evaluate_dataset(messages, config)
    quality = summarize_quality(rows)

    print("== 2. Retrieval quality ==")
    retrieval = evaluate_retrieval(messages)

    print("== 3. Consistency and robustness ==")
    consistency = evaluate_consistency(messages_by_id, config)
    robustness = evaluate_robustness(messages_by_id, config)

    summary = {
        "output_quality": quality,
        "retrieval": retrieval,
        "consistency": consistency,
        "robustness": robustness,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "results.jsonl"), "w") as file:
        for row in rows:
            file.write(json.dumps(row) + "\n")
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as file:
        json.dump(summary, file, indent=2)

    print()
    print(json.dumps(summary, indent=2))
    print()
    print("Messages with a wrong routing or action:")
    for row in rows:
        if row["predicted_routing"] != row["expected_routing"] or row["predicted_action"] != row["expected_action"]:
            print("  ", row["id"], "| expected", row["expected_routing"], "/", row["expected_action"],
                  "| got", row["predicted_routing"], "/", row["predicted_action"], "|", row["text"][:50])
    print()
    print("Saved eval/results.jsonl and eval/summary.json")
