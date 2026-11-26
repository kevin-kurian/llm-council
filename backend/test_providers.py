"""Self-check for provider dispatch. Run: python -m backend.test_providers [--live]

--live also calls each configured CLI (burns subscription quota).
"""

import asyncio
import sys

from .config import COUNCIL_MODELS
from .providers import _flatten, parse_model, query_model

assert parse_model("openrouter:google/gemini-3-pro-preview") == ("openrouter", "google/gemini-3-pro-preview")
assert parse_model("codex:gpt-6.1-sol") == ("codex", "gpt-6.1-sol")
assert parse_model("agy:gemini-4-hydrogen-high") == ("agy", "gemini-4-hydrogen-high")
assert parse_model("google/gemini-2.5-flash") == ("openrouter", "google/gemini-2.5-flash")
assert parse_model("weird:thing") == ("openrouter", "weird:thing")
assert _flatten([{"role": "user", "content": "hi"}]) == "hi"
assert _flatten([{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]) == "a\n\nAssistant:\nb"
print("parse checks passed")


async def live():
    failed = []
    for model in COUNCIL_MODELS:
        result = await query_model(model, [{"role": "user", "content": "Reply with exactly: OK"}], timeout=240)
        if result and result.get("content"):
            print(f"{model}: {result['content'].strip()[:40]!r}")
        else:
            failed.append(model)
    assert not failed, f"failed: {failed}"


if "--live" in sys.argv:
    asyncio.run(live())
