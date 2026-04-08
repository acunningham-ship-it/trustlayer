"""TrustLayer configuration."""

import os
from pathlib import Path

# Data directory - everything stored locally
DATA_DIR = Path(os.getenv("TRUSTLAYER_DATA_DIR", Path.home() / ".trustlayer"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/trustlayer.db"

# Provider keys (from env or user config)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Knowledge base
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

# User profile
PROFILE_FILE = DATA_DIR / "profile.json"

# Cost tracking budget alerts (USD)
DEFAULT_MONTHLY_BUDGET = float(os.getenv("TRUSTLAYER_BUDGET", "50.0"))
