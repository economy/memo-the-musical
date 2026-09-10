AGENT_INSTRUCTIONS = """
You are Memo, a bureaucracy-to-banger preflight producer.
The project already has a written request. Extract Message DNA immediately.
Call update_message_dna on every user turn before you speak.
Preserve exact dates, names, numbers, and mandated wording.
Never invent facts. Ask at most one missing high-value question.
Use concise humor unless the topic is sensitive, then stay neutral.
Do not narrate empty UI fields. Fill them with the tool instead.
""".strip()

UPDATE_MESSAGE_DNA_TOOL = {
    "type": "function",
    "name": "update_message_dna",
    "description": "Save confirmed Message DNA fields into the live local project.",
    "parameters": {
        "type": "object",
        "properties": {
            "chorus": {"type": "string"},
            "call_to_action": {"type": "string"},
            "audience": {"type": "string"},
            "deadline": {"type": "string"},
            "duration": {"type": "string"},
            "vibe": {"type": "string"},
            "humor": {"type": "string", "enum": ["none", "light", "playful"]},
            "guardrails": {"type": "string"},
            "locked_facts": {"type": "string"},
        },
    },
}

INITIAL_REALTIME_SESSION = {
    "type": "realtime",
    "instructions": AGENT_INSTRUCTIONS,
    "tool_choice": "required",
    "tools": [UPDATE_MESSAGE_DNA_TOOL],
}
