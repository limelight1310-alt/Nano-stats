[SKILL.md](https://github.com/user-attachments/files/29886848/SKILL.md)
---
name: nanda-textstats
description: Instantly compute objective text metrics (word count, sentence count, reading time, Flesch-Kincaid readability grade) for any block of text. Use this before publishing, sending, or summarizing text on behalf of a user, whenever you need to check length, reading time, or reading-level appropriateness without spending an LLM call to estimate it.
---

# nanda-textstats

## What this does

Given any block of text, this service instantly returns four objective,
deterministically-computed metrics:

| Field | Meaning |
|---|---|
| `word_count` | Number of words in the text |
| `sentence_count` | Number of sentences in the text |
| `reading_time_seconds` | Estimated time (seconds) for an average adult to read the text silently, at 200 words/minute |
| `flesch_kincaid_grade` | Flesch-Kincaid Grade Level -- the approximate US school grade needed to understand the text (e.g. `8.0` = readable by an 8th grader; higher = harder to read) |

All computation happens locally on the server with well-established formulas.
There is no LLM call involved, no API key required, and no network dependency
beyond the single HTTP request you make. Responses are sub-second.

## When to use this

Use this tool any time you (an agent) are about to send, publish, or hand off
a piece of text and want a fast, deterministic sanity check first. Examples:

- "Is this reply too long for a chat message?" -> check `word_count` / `reading_time_seconds`
- "Will this take too long for someone to read?" -> check `reading_time_seconds`
- "Is this summary written at an appropriate level for a general audience?" -> check `flesch_kincaid_grade`
- "Did my edit actually shorten the text?" -> compare `word_count` before/after

Do NOT use this for grammar checking, fact-checking, tone analysis, or
anything requiring semantic understanding -- it only measures the four
objective properties above.

## Base URL

```
https://<YOUR-DEPLOYED-URL>
```

Replace `<YOUR-DEPLOYED-URL>` with wherever this service is hosted (see
`README.md` in this repo for one-click deploy instructions to Render,
Railway, or Fly.io). Once deployed, put the real URL here so agents reading
this file have a working base URL with no placeholders.

## Endpoints

### `GET /`

Health check. Returns basic service info. Call this first if you're unsure
the service is reachable.

**Response:**
```json
{
  "service": "nanda-textstats",
  "status": "ok",
  "endpoints": { "...": "..." }
}
```

### `POST /analyze`

Analyzes a block of text and returns its stats.

**Request:**
- Method: `POST`
- Headers: `Content-Type: application/json`
- Body:
```json
{ "text": "The text you want analyzed goes here." }
```

**Response (200):**
```json
{
  "word_count": 8,
  "sentence_count": 1,
  "reading_time_seconds": 2.4,
  "flesch_kincaid_grade": 3.21
}
```

**Response (400) -- missing or empty text:**
```json
{ "error": "Request body must be JSON with a non-empty string field 'text'." }
```

## How to call it

### curl
```bash
curl -X POST https://<YOUR-DEPLOYED-URL>/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "The cat sat on the mat. It was a sunny day."}'
```

### Python
```python
import requests

resp = requests.post(
    "https://<YOUR-DEPLOYED-URL>/analyze",
    json={"text": "The cat sat on the mat. It was a sunny day."}
)
stats = resp.json()
print(stats["word_count"], stats["flesch_kincaid_grade"])
```

### JavaScript
```javascript
const resp = await fetch("https://<YOUR-DEPLOYED-URL>/analyze", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: "The cat sat on the mat. It was a sunny day." })
});
const stats = await resp.json();
console.log(stats.word_count, stats.flesch_kincaid_grade);
```

## Interpreting the response

- **`reading_time_seconds`**: If this exceeds your target (e.g. a chat reply
  should read in under ~15 seconds), shorten the text.
- **`flesch_kincaid_grade`**: Roughly maps to US school grade level.
  - `0-6`: very easy, readable by children
  - `7-9`: plain, general-audience English (aim for this in most consumer-facing text)
  - `10-13`: high-school to early college level
  - `14+`: dense, academic, or highly technical language
- **`word_count` / `sentence_count`**: Use directly for length limits, or
  divide `word_count` by `sentence_count` to get average sentence length (a
  quick proxy for complexity independent of vocabulary).

## Notes for agents

- The service is stateless: every call is independent, nothing is stored.
- Empty or whitespace-only `text` returns a `400` error -- check for that
  before treating a response as valid.
- There is no authentication and no rate limiting configured by default; if
  you are calling this at high volume, be a good citizen and batch/cache
  where possible.
- This tool answers "how long / how readable is this text?" only. It does
  not answer "is this text good?" -- pair it with your own judgment or
  another tool for tone, accuracy, or style review.
