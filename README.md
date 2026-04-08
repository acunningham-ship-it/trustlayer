# TrustLayer

**You bring the AI. We bring the trust.**

The universal trust layer for every AI tool you use. Verify outputs, track costs, compare models, and keep your data local — all from one open-source app that runs on your machine.

[![License: MIT](https://img.shields.io/badge/License-MIT-stone.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-stone.svg)](https://python.org)
[![Website](https://img.shields.io/badge/website-live-green.svg)](https://acunningham-ship-it.github.io/trustlayer)

> **[Website](https://acunningham-ship-it.github.io/trustlayer)** · **[Quick Start](#quick-start)** · **[CLI Reference](#cli-usage)** · **[REST API](#rest-api)**

---

## Why TrustLayer?

People don't trust AI. Not because it's incapable — but because:

- You can't verify if an output is accurate or hallucinated
- Your data goes to multiple cloud providers you don't control
- 100 new AI tools launch daily — impossible to evaluate all of them
- No single place to track what you're spending across all providers

**TrustLayer wraps around all of them.** You bring whatever AI you already trust. We add the trust layer on top.

---

## Features

| Feature | What it does |
|---|---|
| **Universal Connector** | Plug in any AI: Ollama (auto-detected), Claude, GPT-4, Gemini. One interface for all. |
| **Verification Engine** | Every output gets a trust score 0–100. Hallucination and overconfidence flags. |
| **Personal Learning** | Learns how you work across sessions. Stored 100% locally. |
| **Cost Tracker** | Real-time spending dashboard across all providers. Budget alerts. |
| **Model Comparison** | Test your actual tasks across models side-by-side. Personal benchmarks. |
| **Offline Knowledge Base** | Index your docs, PDFs, code repos. Works fully offline with Ollama. |
| **No-Code Workflows** | Visual workflow builder. Summarize emails, auto-verify, doc Q&A. |
| **Adaptive Personality** | Honest for facts. Creative for brainstorming. Adapts automatically. |

---

## Quick Start

```bash
# Install
pip install trustlayer

# Start the server + web UI
trustlayer server
# → Auto-detects Ollama if running
# → Opens http://localhost:8000
```

That's it. Add API keys if you want cloud providers:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=...
```

---

## CLI Usage

```bash
# Verify any AI output
trustlayer verify "The earth is 4.5 billion years old."
# → Trust Score: 94/100 (HIGH) — No concerns

# Ask any connected AI
trustlayer ask "Summarize this codebase" --provider ollama --model llama3.2

# Compare multiple providers side-by-side on the same prompt
trustlayer compare "Write unit tests for this function"

# Check your spending across all providers
trustlayer costs

# Detect what AI tools are available on your machine
trustlayer detect

# Upload documents to your local knowledge base
trustlayer knowledge upload ./my-docs/

# Learn and track your session
trustlayer learn
```

---

## REST API

```bash
# Verify content
curl -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d '{"content": "AI output here"}'

# Response
{
  "trust_score": 87,
  "trust_label": "high",
  "summary": "This response is 87% trusted. 0 concern(s) flagged.",
  "issues": []
}

# Compare providers
curl -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum entanglement", "providers": ["ollama", "anthropic"]}'

# Check costs
curl http://localhost:8000/api/costs

# List connected providers
curl http://localhost:8000/api/connectors
```

Full interactive docs at `http://localhost:8000/docs` (Swagger UI) when the server is running.

---

## Architecture

```
trustlayer/
├── backend/              # FastAPI backend (async SQLite)
│   ├── main.py           # Application entry point + lifespan
│   ├── config.py         # Configuration (env vars)
│   ├── database.py       # SQLite with SQLAlchemy async
│   ├── providers/        # AI provider adapters (Ollama, OpenAI-compat)
│   └── routers/          # 8 feature routers
│       ├── verify.py     # Verification engine + trust scoring
│       ├── compare.py    # Multi-provider comparison
│       ├── connectors.py # Provider detection & management
│       ├── costs.py      # Cost tracking + budget alerts
│       ├── knowledge.py  # Local knowledge base (RAG)
│       ├── learn.py      # Personal learning & session memory
│       ├── workflows.py  # No-code workflow builder
│       └── settings.py   # Runtime configuration
├── frontend/             # React + TypeScript + Tailwind CSS
│   └── src/pages/        # Dashboard, Verify, Compare, Costs, Knowledge,
│                         # Connectors, Workflows, Settings
├── cli/                  # Python CLI (Typer) with rich output
└── docs/                 # GitHub Pages website
```

All data stored in `~/.trustlayer/` — nothing leaves your machine unless you configure cloud providers.

---

## Privacy & Local-First Design

- **No telemetry.** No usage data sent anywhere.
- **No accounts.** TrustLayer itself requires no sign-up.
- **No cloud sync.** SQLite database lives at `~/.trustlayer/trustlayer.db`.
- **Fully offline.** Works completely without internet when using Ollama.
- **Your keys, your calls.** API calls go directly from your machine to providers.

---

## Development

```bash
git clone https://github.com/acunningham-ship-it/trustlayer
cd trustlayer

# Backend (FastAPI)
pip install -r requirements.txt
uvicorn backend.main:app --reload
# → http://localhost:8000

# Frontend (React + Vite)
cd frontend && npm install && npm run dev
# → http://localhost:5173

# CLI
pip install -e .
trustlayer --help

# Tests
pytest tests/
```

---

## Contributing

Issues and PRs are welcome. TrustLayer is MIT licensed — use it, fork it, build on it.

---

## License

MIT — free to use, modify, and distribute.

**
