# Reddit r/LocalLLaMA Post

**Target subreddits (in order):**
1. r/LocalLLaMA — primary, Ollama users
2. r/MachineLearning — verification/research angle
3. r/artificial — broad AI community
4. r/programming — developer audience
5. r/ChatGPT — hallucination-frustrated users

---

## r/LocalLLaMA

### Title
```
I built a trust layer for Ollama (and any AI) — scores hallucinations, tracks costs, lets you compare models on your actual tasks
```

### Body
```
Hey r/LocalLLaMA,

After running Ollama locally for a while, I kept running into the same frustrations:
- How do I know when it's hallucinating vs. when I can trust the output?
- I'm switching between local models and APIs — no visibility into total costs
- Which model is actually best for *my* specific use cases?

I built TrustLayer to solve this. It wraps around Ollama (and any other AI) and gives you:

**Trust scoring**: Every response gets a 0-100 trust score. Flagged claims show up
highlighted. "This response is 87% verified. 2 claims could not be confirmed."

**Hallucination detection**: Flags responses where claims seem fabricated or
can't be sourced.

**Cost tracker**: Real-time spend across all your AI providers (yes, including $0
for local Ollama vs. API costs — useful when deciding what to route where).

**Model comparison**: Test your actual prompts against multiple models. "For code
review, your local Mistral is 23% better on your tasks than GPT-4."

**Local knowledge base**: Drag in your docs, code repos, PDFs. Indexed locally.
Works 100% offline with Ollama.

Install with one command:

    pip install trustlayer-ai && trustlayer server

Auto-detects Ollama if you have it running. Everything stores locally — your
prompts and context never leave your machine.

Open source: https://github.com/acunningham-ship-it/trustlayer

Would love feedback from the local AI community since this was built with you in mind.
```

---

## r/MachineLearning

### Title
```
[Project] TrustLayer: Open source verification layer for LLM outputs — hallucination detection, trust scoring, source attribution
```

### Body
```
Built an open source tool for verifying LLM outputs that this community might find interesting.

Key capabilities:
- Trust scoring (0-100) per response with claim-level confidence
- Hallucination detection using cross-reference checks
- Source attribution on factual claims
- Plagiarism detection for generated content
- Works with any LLM (local via Ollama, or API: Anthropic, OpenAI, Google, etc.)

It's not trying to be a perfect fact-checker — that's an unsolved problem. Instead it
uses a pipeline of heuristics (claim extraction → cross-reference → confidence scoring)
to flag responses worth scrutinizing.

Install: pip install trustlayer-ai
GitHub: https://github.com/acunningham-ship-it/trustlayer

Interested in feedback on the verification approach — especially from anyone who's
worked on hallucination detection.
```
