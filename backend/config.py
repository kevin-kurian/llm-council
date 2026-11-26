"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - "<provider>:<model>". Bare identifiers use OpenRouter.
COUNCIL_MODELS = [
    "openrouter:deepseek/deepseek-v4.1-flash-1017",
    "codex:gpt-6.2-sol",
    "grok:grok-4.7",
    "agy:gemini-4-hydrogen-high",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "codex:gpt-6.2-astra"

# Reasoning effort sent to every provider that supports it (low|medium|high|xhigh|max)
REASONING_EFFORT = "high"

# Cheap model for conversation titles (still uses REASONING_EFFORT)
TITLE_MODEL = "agy:gemini-3.8-flash-low"

# Per-call timeout; CLI agents are slower than raw API calls
MODEL_TIMEOUT = 240.0

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
