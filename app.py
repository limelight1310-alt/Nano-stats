"""
nanda-textstats
================

Problem
-------
AI agents increasingly generate, summarize, and publish text on behalf of
users -- replies, articles, documentation, social posts -- but have no fast,
reliable way to check basic properties of that text before sending it. Is it
too long? Too short? Too complex for the intended audience? Right now, an
agent either has to guess, or burn an expensive LLM call just to estimate
something as simple as reading time or readability level.

What this service does
-----------------------
A minimal, self-contained API that takes any block of text and instantly
returns:
  - word_count
  - sentence_count
  - reading_time_seconds
  - flesch_kincaid_grade

Everything is computed locally with simple, well-established formulas.
No external calls, no API keys, no network dependency, sub-second response
time. Deterministic: same text in, same numbers out, every time.

Endpoints
---------
GET  /                -> health check / service info
POST /analyze         -> {"text": "..."} -> stats JSON

Run locally:
    pip install -r requirements.txt
    python app.py
    # serves on http://0.0.0.0:8080

Deploy anywhere that runs a Python web app (Render, Railway, Fly.io,
PythonAnywhere, a VPS, etc.) -- there are zero external dependencies beyond
the `flask` package itself, so it will boot on essentially any free tier.
"""

import re
from flask import Flask, request, jsonify

app = Flask(__name__)

AVERAGE_READING_WPM = 200  # standard adult silent-reading speed used for reading-time estimates


def count_words(text: str) -> int:
    words = re.findall(r"[A-Za-z0-9'-]+", text)
    return len(words)


def count_sentences(text: str) -> int:
    # Split on ., !, ? followed by whitespace or end of string.
    # Filter out empty fragments caused by trailing/leading punctuation.
    sentences = re.split(r"[.!?]+(?:\s+|$)", text.strip())
    sentences = [s for s in sentences if s.strip()]
    return max(len(sentences), 1) if text.strip() else 0


def count_syllables_in_word(word: str) -> int:
    word = word.lower()
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 0
    vowel_groups = re.findall(r"[aeiouy]+", word)
    syllables = len(vowel_groups)
    # Silent trailing 'e' usually doesn't add a syllable (e.g. "like")
    if word.endswith("e") and syllables > 1:
        syllables -= 1
    return max(syllables, 1)


def count_syllables(text: str) -> int:
    words = re.findall(r"[A-Za-z]+", text)
    return sum(count_syllables_in_word(w) for w in words) or 0


def flesch_kincaid_grade(word_count: int, sentence_count: int, syllable_count: int) -> float:
    if word_count == 0 or sentence_count == 0:
        return 0.0
    grade = (
        0.39 * (word_count / sentence_count)
        + 11.8 * (syllable_count / word_count)
        - 15.59
    )
    return round(grade, 2)


def analyze_text(text: str) -> dict:
    words = count_words(text)
    sentences = count_sentences(text)
    syllables = count_syllables(text)
    reading_time_seconds = round((words / AVERAGE_READING_WPM) * 60, 1) if words else 0.0
    grade = flesch_kincaid_grade(words, sentences, syllables)

    return {
        "word_count": words,
        "sentence_count": sentences,
        "reading_time_seconds": reading_time_seconds,
        "flesch_kincaid_grade": grade,
    }


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "service": "nanda-textstats",
        "status": "ok",
        "endpoints": {
            "POST /analyze": "Send {\"text\": \"...\"} to get word count, sentence count, reading time, and readability grade."
        }
    })


@app.route("/analyze", methods=["POST"])
def analyze():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")

    if not isinstance(text, str) or not text.strip():
        return jsonify({
            "error": "Request body must be JSON with a non-empty string field 'text'."
        }), 400

    return jsonify(analyze_text(text))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
