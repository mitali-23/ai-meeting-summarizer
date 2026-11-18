"""
AI Insights (meeting type / primary topic / sentiment).
===========================================================
This is a SEPARATE, independent analysis from the main summarization
pipeline in meeting_summarizer.py — different function, different prompt,
different call. It does not touch, wrap, or alter analyze_meeting_with_llm()
in any way. If this call fails for any reason, the app simply shows
"Not Available" for these fields — it never fabricates a value.
"""

import os
import re
import json

from google import genai
from google.genai import types

import gemini_retry

INSIGHTS_SYSTEM_PROMPT = """You analyze a meeting transcript and classify it along three \
dimensions. Only answer if you are reasonably confident from the transcript itself — \
if you cannot tell, use null. Never guess or invent details not supported by the text.

Respond with ONLY valid JSON (no markdown fences) in exactly this shape:
{
  "meeting_type": "e.g. Standup / Planning / Review / Client Call / Brainstorm / General Discussion, or null",
  "primary_topic": "a short phrase (3-6 words) naming the main subject, or null",
  "sentiment": "Positive / Neutral / Mixed / Negative, or null"
}"""


def analyze_meeting_insights(transcript, model=None):
    """
    Returns a dict with meeting_type / primary_topic / sentiment, each either
    a string or None. Never raises to the caller — on any failure (including
    the primary model AND its fallback both being unavailable) it returns
    all-None so the UI can show "Not Available" instead of breaking the page.
    """
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            system_instruction=INSIGHTS_SYSTEM_PROMPT,
            response_mime_type="application/json",
            max_output_tokens=300,
        )

        def _call(model_name):
            return client.models.generate_content(
                model=model_name,
                contents=f"Transcript:\n\n{transcript}",
                config=config,
            )

        if model:
            response = gemini_retry.call_with_retry_and_fallback(lambda m: _call(model), label="analyze_meeting_insights")
        else:
            response = gemini_retry.call_with_retry_and_fallback(_call, label="analyze_meeting_insights")

        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(json)?", "", raw).rstrip("`").strip()

        data = json.loads(raw)
        return {
            "meeting_type": data.get("meeting_type") or None,
            "primary_topic": data.get("primary_topic") or None,
            "sentiment": data.get("sentiment") or None,
        }
    except Exception:
        return {"meeting_type": None, "primary_topic": None, "sentiment": None}


def estimate_reading_time(word_count):
    """Deterministic, not AI-derived: standard ~200 wpm reading speed."""
    if not word_count:
        return "Not Available"
    minutes = max(1, round(word_count / 200))
    return f"{minutes} min read"
