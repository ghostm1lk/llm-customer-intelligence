"""
decision.py - rule-based decision layer.

Takes the LLM's extraction (intents + priority) and decides:
    - routing: which team gets the message
    - suggested_action: Escalate / Respond / Request more info

Rules live in config/taxonomy.yaml, so they can be changed without touching code.

Run the self-check:
    python decision.py
"""

import yaml


def load_config(path="config/taxonomy.yaml"):
    """Read the taxonomy YAML file and return it as a Python dictionary."""
    with open(path) as file:
        config = yaml.safe_load(file)

    # Every intent must have a description, and every description must be a real intent.
    for name in config["intents"]:
        assert name in config["intent_descriptions"], "No description for intent: " + name
    for name in config["intent_descriptions"]:
        assert name in config["intents"], "Description for unknown intent: " + name
    return config


def clean_intents(intents, config):
    """Drop "Unclear" when the model also found a real intent.

    A message cannot be both understood and unclear. Without this guard, a phishing
    victim labeled [Fraud Report, Unclear] would get "Request more info" instead of
    an urgent escalation.
    """
    unclear = config["unclear_intent"]
    cleaned = []
    for intent in intents:
        if intent != unclear:
            cleaned.append(intent)
    if len(cleaned) == 0 and unclear in intents:
        cleaned.append(unclear)  # Unclear was the only intent: keep it
    return cleaned


def pick_team(intents, config):
    """Return the team that should handle a message with these intents."""
    # Collect every team that the detected intents point to.
    teams_found = []
    for intent in intents:
        if intent in config["intents"]:
            team = config["intents"][intent]
            if team is not None:
                teams_found.append(team)

    # Walk the team_order list; the first team we find wins.
    for team in config["team_order"]:
        if team in teams_found:
            return team

    return config["default_team"]


def pick_action(intents, priority, team, config):
    """Return the suggested action for the message."""
    if len(intents) == 0:
        return "Request more info"
    if config["unclear_intent"] in intents:
        return "Request more info"
    if team in config["escalate_teams"]:
        return "Escalate"
    if priority in config["escalate_priorities"]:
        return "Escalate"
    return "Respond"


def decide(intents, priority, config):
    """Run both rules and return the decision as a dictionary."""
    team = pick_team(intents, config)
    action = pick_action(intents, priority, team, config)
    decision = {
        "routing": team,
        "suggested_action": action,
    }
    return decision


if __name__ == "__main__":
    config = load_config()

    # Duplicate charge + angry customer -> Billing, escalate (High priority).
    result = decide(["Billing Issue", "Complaint"], "High", config)
    assert result["routing"] == "Billing Department", result
    assert result["suggested_action"] == "Escalate", result

    # Fraud always beats billing and always escalates, even at Low priority.
    result = decide(["Billing Issue", "Fraud Report"], "Low", config)
    assert result["routing"] == "Fraud Team", result
    assert result["suggested_action"] == "Escalate", result

    # Vague message -> ask the customer for more details.
    result = decide(["Unclear"], "Low", config)
    assert result["routing"] == "Support Team", result
    assert result["suggested_action"] == "Request more info", result

    # Unclear next to a real intent is dropped, so fraud still escalates (eval case M012).
    assert clean_intents(["Fraud Report", "Unclear"], config) == ["Fraud Report"]
    assert clean_intents(["Unclear"], config) == ["Unclear"]
    result = decide(clean_intents(["Fraud Report", "Unclear"], config), "High", config)
    assert result["routing"] == "Fraud Team", result
    assert result["suggested_action"] == "Escalate", result

    # Simple question -> just respond.
    result = decide(["Loan Inquiry"], "Low", config)
    assert result["routing"] == "Account Services", result
    assert result["suggested_action"] == "Respond", result

    print("Decision self-check passed.")
