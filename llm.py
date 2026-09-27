"""
llm.py - talks to the local Qwen model running in Ollama.

Before running:
    1. Ollama is installed and running  (ollama serve)
    2. The model is downloaded          (ollama pull qwen3.5:4b)
    3. pip install ollama pydantic pyyaml

Run the self-check:
    python llm.py
"""

from typing import List, Literal

import ollama
from pydantic import BaseModel


MODEL_NAME = "qwen3.5:4b"


# This class describes the exact JSON shape we want back from the model.
# Pydantic turns it into a JSON schema, and Ollama forces the model to follow it.
class Extraction(BaseModel):
    intents: List[str]
    issue_type: str
    priority: Literal["Low", "Medium", "High", "Critical"]
    entities: List[str]


def build_system_prompt(intent_descriptions):
    """Build the instructions for the model, including each allowed intent and its definition."""
    # One line per intent, e.g. "- Billing Issue: Wrong, duplicate or unexpected charges..."
    intent_lines = ""
    for name in intent_descriptions:
        intent_lines = intent_lines + "- " + name + ": " + intent_descriptions[name] + "\n"

    prompt = (
        "You are an assistant for a bank's customer service team. "
        "Read the customer message and extract: the intents, the issue type, "
        "the priority (Low, Medium, High or Critical), and the key entities "
        "(account types, transaction references, amounts, dates, merchants, "
        "or short phrases like 'duplicate transaction').\n\n"
        "Choose intents ONLY from this list, using the definitions:\n"
        + intent_lines +
        "\nA message can have more than one intent. Include every intent that clearly applies, "
        "and do not add intents that are only loosely related. "
        "If the message does not say what the problem is, use Unclear instead of guessing.\n\n"
        "Priority guide:\n"
        "- Critical: money is being lost right now (fraud, stolen card, unknown withdrawals), "
        "or the customer mentions regulators or legal action.\n"
        "- High: the customer is angry or the problem is urgent (deadline today or tomorrow, "
        "repeated complaint, no access to their money).\n"
        "- Medium: a real problem described calmly, with no urgency.\n"
        "- Low: a simple question or information request.\n"
        "For vague messages, judge the priority from the tone only.\n\n"
        "Answer only with JSON."
    )
    return prompt


def extract(message, intent_descriptions):
    """Send one customer message to the model and return an Extraction object."""
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": build_system_prompt(intent_descriptions)},
            {"role": "user", "content": message},
        ],
        format=Extraction.model_json_schema(),  # force valid JSON in our shape
        think=False,                            # skip Qwen's long "thinking" step
        options={
            "temperature": 0,   # same input -> same output
            "num_ctx": 4096,    # small context window to save RAM on 8 GB
        },
    )
    raw_json = response.message.content
    result = Extraction.model_validate_json(raw_json)
    return result


def generate_response(message, chunks, routing, suggested_action):
    """Write a short reply to the customer, grounded ONLY in the retrieved policy chunks."""
    # Put each retrieved chunk on its own line, labelled with the file it came from.
    policy_text = ""
    for chunk in chunks:
        policy_text = policy_text + "[" + chunk["source"] + "] " + chunk["text"] + "\n"
    if policy_text == "":
        policy_text = "(no policy text available)\n"

    system_prompt = (
        "You are a customer service assistant at Nova Bank. "
        "Write a short, polite reply (2 to 4 sentences) to the customer. "
        "Use ONLY the facts in the POLICY section. Never invent numbers, fees or time limits. "
        "When you use a fact, mention the policy file it came from in brackets, e.g. [fees_and_charges.md]. "
        "If the policy does not answer the question, say the request is being forwarded to the right team. "
        "If the next step is 'Request more info', ask the customer one clear question about what they need."
    )
    user_prompt = (
        "CUSTOMER MESSAGE:\n" + message + "\n\n"
        "NEXT STEP: " + suggested_action + " (handled by " + routing + ")\n\n"
        "POLICY:\n" + policy_text
    )

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        think=False,
        options={
            "temperature": 0,
            "num_ctx": 4096,
        },
    )
    return response.message.content.strip()


if __name__ == "__main__":
    test_message = (
        "I was charged twice for the same transaction and I need this "
        "resolved immediately. If not, I will escalate."
    )
    test_intents = {
        "Billing Issue": "Wrong, duplicate or unexpected charges on the customer's own purchases.",
        "Unauthorized Transaction": "A transaction the customer did NOT make. A duplicate of their own purchase is NOT this.",
        "Complaint": "Customer is angry or threatens to escalate.",
        "Unclear": "Too vague to understand.",
    }
    result = extract(test_message, test_intents)
    print(result.model_dump_json(indent=2))

    # Minimal check: the model must detect a High or Critical priority here.
    assert result.priority in ["High", "Critical"], "Priority should be High or Critical"
    assert len(result.intents) > 0, "At least one intent should be detected"
    print("Self-check passed.")
