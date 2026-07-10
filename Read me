# nanda-textstats

## Problem Statement

**The problem:** AI agents increasingly generate, summarize, and publish text
on behalf of users — replies, articles, documentation, social posts — but
have no fast, reliable way to check basic properties of that text before
sending it. Is it too long? Too short? Too complex for the intended
audience? Right now, an agent either has to guess, or burn an expensive LLM
call just to estimate something as simple as reading time or readability
level.

**Why it matters:** In a multi-agent system, small inefficiencies compound.
If every agent re-implements its own (likely inconsistent) word-counting or
readability logic — or worse, asks a large language model to "estimate how
readable this is" — that's wasted compute, inconsistent results across
agents, and no shared standard other agents can rely on.

**The gap:** There's no lightweight, standardized, agent-callable service
that instantly returns objective text metrics — no API key, no LLM call, no
network dependency beyond a single request.

**What we built:** A minimal, self-contained API — `nanda-textstats` — that
takes any block of text and instantly returns:
- Word count
- Sentence count
- Estimated reading time (seconds)
- Flesch-Kincaid readability grade level

All computed locally with simple, well-established formulas — no external
calls, no API keys, sub-second response time.

**Who it's for:** Any AI agent that drafts, edits, or reviews text and needs
a fast, deterministic sanity check before publishing — e.g., "is this reply
appropriate for a general audience?" or "will this summary take too long to
read?"

**Success criteria:** An agent that has only read `SKILL.md` — with no other
context or human help — can correctly call the service and interpret its
response on the first try.

---

## What's in this repo

| File | Purpose |
|---|---|
| `app.py` | The Flask service — two endpoints, zero external dependencies |
| `requirements.txt` | `flask` + `gunicorn`, nothing else |
| `render.yaml` | One-click deploy config for [Render](https://render.com) |
| `SKILL.md` | The agent-facing instructions — **this is the file you hand to an agent** |

## Deploying it live (pick one, all have free tiers)

### Option A — Render (easiest, has a `render.yaml` already)
1. Push this folder to a GitHub repo.
2. Go to [render.com](https://render.com) → New → Blueprint → point at the repo.
3. Render reads `render.yaml` and deploys automatically.
4. Copy the resulting URL (looks like `https://nanda-textstats.onrender.com`).

### Option B — Railway
1. Push this folder to a GitHub repo.
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub.
3. Railway auto-detects Python/Flask; set the start command to:
   `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Copy the generated public URL.

### Option C — Fly.io
```bash
fly launch   # follow prompts, it detects the Flask app
fly deploy
```

### Option D — Run it anywhere with Python
```bash
pip install -r requirements.txt
gunicorn app:app --bind 0.0.0.0:8080
```
Then put that host behind any reverse proxy / tunnel (ngrok, Cloudflare
Tunnel, etc.) to get a public URL.

## After deploying

**Open `SKILL.md` and replace every `<YOUR-DEPLOYED-URL>` with your real
base URL.** That file is the actual deliverable — it's what an agent reads
to learn the service exists and how to call it. The service is useless to
an agent until the SKILL.md points at a real, live address.

## Quick local test

```bash
python app.py
# in another terminal:
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The cat sat on the mat. It was a sunny day."}'
```
