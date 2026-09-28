"""
routing and next action, decided by rules instead of the model.

the rules live in config/taxonomy.yaml.
self-check: python decision.py
"""

import yaml


def load_config(path="config/taxonomy.yaml"):
    with open(path) as file:
        config = yaml.safe_load(file)

    # the two intent lists in the yaml have to stay in sync
    for name in config["intents"]:
        assert name in config["intent_descriptions"], "No description for intent: " + name
    for name in config["intent_descriptions"]:
        assert name in config["intents"], "Description for unknown intent: " + name
    return config


def clean_intents(intents, config):
    """drop Unclear when the model also found a real intent.

    without this, a phishing report tagged [Fraud Report, Unclear] got
    "Request more info" instead of an escalation (eval case M012).
    """
    unclear = config["unclear_intent"]
    cleaned = []
    for intent in intents:
        if intent != unclear:
            cleaned.append(intent)
    if len(cleaned) == 0 and unclear in intents:
        cleaned.append(unclear)
    return cleaned


def pick_team(intents, config):
    teams_found = []
    for intent in intents:
        if intent in config["intents"]:
            team = config["intents"][intent]
            if team is not None:
                teams_found.append(team)

    # several teams can match, team_order decides (highest risk first)
    for team in config["team_order"]:
        if team in teams_found:
            return team

    return config["default_team"]


def pick_action(intents, priority, team, config):
    # order matters: the first rule that matches wins
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
    team = pick_team(intents, config)
    action = pick_action(intents, priority, team, config)
    decision = {
        "routing": team,
        "suggested_action": action,
    }
    return decision


if __name__ == "__main__":
    config = load_config()

    # angry duplicate charge
    result = decide(["Billing Issue", "Complaint"], "High", config)
    assert result["routing"] == "Billing Department", result
    assert result["suggested_action"] == "Escalate", result

    # fraud wins over billing and escalates even at Low priority
    result = decide(["Billing Issue", "Fraud Report"], "Low", config)
    assert result["routing"] == "Fraud Team", result
    assert result["suggested_action"] == "Escalate", result

    # vague message
    result = decide(["Unclear"], "Low", config)
    assert result["routing"] == "Support Team", result
    assert result["suggested_action"] == "Request more info", result

    # Unclear next to a real intent gets dropped
    assert clean_intents(["Fraud Report", "Unclear"], config) == ["Fraud Report"]
    assert clean_intents(["Unclear"], config) == ["Unclear"]
    result = decide(clean_intents(["Fraud Report", "Unclear"], config), "High", config)
    assert result["routing"] == "Fraud Team", result
    assert result["suggested_action"] == "Escalate", result

    # simple question
    result = decide(["Loan Inquiry"], "Low", config)
    assert result["routing"] == "Account Services", result
    assert result["suggested_action"] == "Respond", result

    print("Decision self-check passed.")
