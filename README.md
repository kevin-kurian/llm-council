# LLM Council

![llmcouncil](header.jpg)

The idea of this repo is that instead of asking a question to your favorite LLM provider (e.g. OpenAI GPT 5.1, Google Gemini 3.0 Pro, Anthropic Claude Sonnet 4.5, xAI Grok 4, eg.c), you can group them into your "LLM Council". This repo is a simple, local web app that essentially looks like ChatGPT except it sends your query to multiple LLMs, it then asks them to review and rank each other's work, and finally a Chairman LLM produces the final response.

Models can come from the OpenRouter API or from local subscription CLIs (Codex, Grok, Antigravity), mixed freely in one council.

In a bit more detail, here is what happens when you submit a query:

1. **Stage 1: First opinions**. The user query is given to all LLMs individually, and the responses are collected. The individual responses are shown in a "tab view", so that the user can inspect them all one by one.
2. **Stage 2: Review**. Each individual LLM is given the responses of the other LLMs. Under the hood, the LLM identities are anonymized so that the LLM can't play favorites when judging their outputs. The LLM is asked to rank them in accuracy and insight.
3. **Stage 3: Final response**. The designated Chairman of the LLM Council takes all of the model's responses and compiles them into a single final answer that is presented to the user.

## Vibe Code Alert

This project was 99% vibe coded as a fun Saturday hack because I wanted to explore and evaluate a number of LLMs side by side in the process of [reading books together with LLMs](https://x.com/karpathy/status/1990577951671509438). It's nice and useful to see multiple responses side by side, and also the cross-opinions of all LLMs on each other's outputs. I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for Python and npm for the frontend.

```bash
uv sync

cd frontend
npm install
cd ..
```

The `npm install` output may mention audit findings and skipped install scripts for `esbuild`/`fsevents`. Both are harmless: the audit items are dev-only tooling, and the esbuild binary still loads.

### 2. Configure Models and Providers

Models are `"<provider>:<model>"`. OpenRouter models need an API key in `.env`:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your key at [openrouter.ai](https://openrouter.ai/).

Subscription CLIs need no key — just be logged in locally (`codex login`, `grok`, `agy`):

| Prefix | Example | CLI used |
|---|---|---|
| `openrouter:` | `openrouter:deepseek/deepseek-v4.1-flash-1017` | HTTP API |
| `codex:` | `codex:gpt-6.2-sol` | `codex exec` (ChatGPT subscription) |
| `grok:` | `grok:grok-4.7` | `grok -p` (grok.com subscription) |
| `agy:` | `agy:gemini-4-hydrogen-high` | `agy -p` (Antigravity subscription) |

Bare identifiers such as `google/gemini-2.5-flash` still default to OpenRouter.
Subscription calls burn plan quota: each call carries the CLI's ~10-20k token system prompt.

### 3. Configure Models (Optional)

Edit `backend/config.py` to customize the council:

```python
COUNCIL_MODELS = [
    "openrouter:deepseek/deepseek-v4.1-flash-1017",
    "codex:gpt-6.2-sol",
    "grok:grok-4.7",
    "agy:gemini-4-hydrogen-high",
]

CHAIRMAN_MODEL = "codex:gpt-6.2-astra"
REASONING_EFFORT = "high"   # low|medium|high|xhigh|max, per provider
```

`REASONING_EFFORT` is translated per provider: `reasoning.effort` on OpenRouter, `model_reasoning_effort` on Codex, `--reasoning-effort` on Grok, `--effort` on Antigravity. An agy slug that already ends in an effort level (`-low`, `-high`, ...) wins over the config value.

### 4. Verify Providers

```bash
uv run python -m backend.test_providers --live
```

Runs parse checks, then one live call per council model:

```
parse checks passed
openrouter:deepseek/deepseek-v4.1-flash-1017: 'OK'
codex:gpt-6.2-sol: 'OK'
grok:grok-4.7: 'OK'
agy:gemini-4-hydrogen-high: 'OK'
```

Omit `--live` for offline checks only. A failing model is reported but does not stop the others; fix `backend/config.py` before starting the app.

### 5. Optional: Pre-commit Hook

```bash
pre-commit install
```

Runs [gitleaks](https://github.com/gitleaks/gitleaks) on staged changes and blocks commits that contain secrets.

## Running the Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

One question costs 9 model calls (4 stage 1, 4 stage 2, 1 chairman) plus a title call. Stages run in parallel, so expect roughly 1-3 minutes per answer with subscription CLIs. A model that errors or times out is dropped and the council continues with the rest; errors print in the backend terminal.

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx for OpenRouter, subprocess adapters for subscription CLIs
- **Frontend:** React + Vite, react-markdown for rendering
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript
