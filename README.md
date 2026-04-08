# TrustLayer

**You bring the AI. We bring the trust.**

The universal trust layer for every AI tool you use. Verify outputs, track costs, compare models, and keep your data local — all from one open-source app.

[![License: MIT](https://img.shields.io/badge/License-MIT-stone.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

> **[Website](https://acunningham-ship-it.github.io/trustlayer)** · **[GitHub](https://github.com/acunningham-ship-it/trustlayer)**

---

## Why TrustLayer?

People don't trust AI. Not because it's incapable — but because:

- You can't verify if an output is accurate or hallucinated
- Your data goes to multiple cloud providers you don't control
- 100 new AI tools launch daily — impossible to evaluate all of them
- No single place to track what you're spending across all providers

TrustLayer wraps around **all of them**. You bring whatever AI you already trust. We add the trust layer.

---

## Features

| Feature | What it does |
|---|---|
| **Universal Connector** | Plug in any AI: Ollama, Claude, GPT-4, Gemini, Aider. One interface. |
| **Verification Engine** | Every output gets a trust score 0–100. Hallucination and overconfidence flags. |
| **Personal Learning** | Learns how you work across sessions. Stored 100% locally. |
| **Cost Tracker** | Real-time spending across all providers. Budget alerts. Optimization tips. |
| **Model Comparison** | Test your actual tasks across models. Personal benchmarks. |
| **Offline Knowledge Base** | Index your docs, PDFs, code repos. Works offline with Ollama. |
| **No-Code Workflows** | Visual workflow builder. Summarize emails, auto-verify, Q&A your docs. |
| **Adaptive Personality** | Honest for facts. Creative for brainstorming. Adapts automatically. |

---

## Quick Start

```bash
# Install
pip install trustlayer

# Start the server + web UI
trustlayer server
# → http://localhost:8000
```

That's it. TrustLayer auto-detects Ollama if it's running. Add API keys via environment variables:

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
# → Trust Score: 92/100 (HIGH) — No concerns

# Ask any connected AI
trustlayer ask "Summarize this codebase" --provider ollama --model llama3.2

# Compare across providers
trustlayer compare "Write unit tests for this function"

# Check your AI spending
trustlayer costs

# Detect available AI tools
trustlayer detect
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
```

Full API docs at `http://localhost:8000/docs` when server is running.

---

## Architecture

```
trustlayer/
├── backend/              # FastAPI backend
│   ├── main.py           # Application entry point
│   ├── config.py         # Configuration
│   ├── database.py       # SQLite (SQLAlchemy async)
│   ├── providers/        # AI provider adapters
│   └── routers/          # API routes (8 feature routers)
├── frontend/             # React + TypeScript + Tailwind
├── cli/                  # Typer CLI
└── docs/                 # GitHub Pages website
```

All data stored in `~/.trustlayer/` — nothing leaves your machine.

---

## Privacy

Local-first by design. No telemetry. No cloud sync. No accounts. SQLite database in `~/.trustlayer/`. Works fully offline with Ollama.

---

## Development

```bash
git clone https://github.com/acunningham-ship-it/trustlayer
cd trustlayer

# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# CLI
cd cli && pip install -e . && trustlayer --help
```

---

## License

MIT — free to use, modify, and distribute.

*Built for the AI Builder Challenge 2026.*
