"""
llm.py - talks to the language model. Two backends, chosen with the LLM_PROVIDER setting:

    LLM_PROVIDER=ollama (default)  local Qwen3.5-4B in Ollama - no data leaves the machine
    LLM_PROVIDER=groq              hosted model on Groq's API - used for the public demo

Before running (ollama):  ollama pull qwen3.5:4b
Before running (groq):    export LLM_PROVIDER=groq  and  export GROQ_API_KEY=...

Run the self-check:
    python llm.py
"""

import os
from typing import List, Literal

from pydantic import BaseModel, ConfigDict


# Read the settings from environment variables (outside the code), with safe defaults.
PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

if PROVIDER == "groq":
    from groq import Groq
    MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    groq_client = Groq()  # reads GROQ_API_KEY from the environment; fails clearly if it is missing
elif PROVIDER == "ollama":
    import ollama
    MODEL_NAME = "qwen3.5:4b"
else:
    raise ValueError("LLM_PROVIDER must be 'ollama' or 'groq', not: " + PROVIDER)


# This class describes the exact JSON shape we want back from the model.
# Pydantic turns it into a JSON schema, and the model is forced to follow it.
class Extraction(BaseModel):
    # extra="forbid" adds "additionalProperties": false to the schema (required by Groq's strict mode).
    model_config = ConfigDict(extra="forbid")

    intents: List[str]
    issue_type: str
    priority: Literal["Low", "Medium", "High", "Critical"]
    entities: List[str]


def chat(system_prompt, user_prompt, schema=None):
    """Send one system + user message to the active backend and return the reply text.

    If a JSON schema is given, the model is forced to answer with JSON in exactly that shape.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    if PROVIDER == "groq":
        request = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0,             # same input -> same output
            "reasoning_effort": "low",    # gpt-oss thinks before answering; keep it short
            "include_reasoning": False,   # do not send the thinking text back
        }
        if schema is not None:
            request["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "extraction", "strict": True, "schema": schema},
            }
        response = groq_client.chat.completions.create(**request)
        return response.choices[0].message.content

    # Local Ollama backend
    response = ollama.chat(
        model=MODEL_NAME,
        messages=messages,
        format=schema,      # None = free text; a schema = JSON in exactly that shape
        think=False,        # skip Qwen's long "thinking" step
        options={
            "temperature": 0,   # same input -> same output
            "num_ctx": 4096,    # small context window to save RAM on 8 GB
        },
    )
    return response.message.content


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
    raw_json = chat(
        build_system_prompt(intent_descriptions),
        message,
        schema=Extraction.model_json_schema(),  # force valid JSON in our shape
    )
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

    reply = chat(system_prompt, user_prompt)
    return reply.strip()


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
    print("Provider:", PROVIDER, "| Model:", MODEL_NAME)
    result = extract(test_message, test_intents)
    print(result.model_dump_json(indent=2))

    # Minimal check: the model must detect a High or Critical priority here.
    assert result.priority in ["High", "Critical"], "Priority should be High or Critical"
    assert len(result.intents) > 0, "At least one intent should be detected"
    print("Self-check passed.")
