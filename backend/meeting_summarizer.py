"""
Meeting Summarizer
====================
Pipeline:
  1. Audio -> Text          (SpeechRecognition + pydub, for pre-recorded audio files)
  2. Basic Text Cleanup     (whitespace normalization only — no semantic decisions
                              are made at this stage anymore, see REFACTOR NOTES)
  3. Meeting Analysis       (semantic understanding via the Gemini API — replaces
                              the old TF-IDF / keyword / regex extraction)
  4. Report Formatting      (fixed, professional report layout)

REFACTOR NOTES (why the analysis logic changed)
------------------------------------------------
The previous version decided what counted as a "summary sentence", "action item",
"decision", or "deadline" using surface-level signals: TF-IDF word frequency,
a hard-coded keyword list, and a regex for dates. Those techniques can't tell
"Let's get started" apart from "Let's finalize the budget by Friday" — both
contain a trigger word ("let's" / "by <day>"), but only one is real content.
That is a *meaning* problem, not a *pattern-matching* problem, so it needed a
component that actually understands meaning: an LLM. Gemini's free tier is
used here, with a pinned GA model + automatic fallback (see gemini_retry.py)
so the whole pipeline runs at no cost and stays resilient to transient
model-overload 503 errors.

Everything else — audio loading, silence-based chunking, transcription via
Google's speech API, the CLI, and the report structure — is unchanged.

Usage:
    python meeting_summarizer.py --audio meeting.mp3
    python meeting_summarizer.py --text meeting_transcript.txt
    python meeting_summarizer.py --text meeting_transcript.txt --model gemini-3.6-flash

Requires a free Gemini API key in the GEMINI_API_KEY environment variable.
Get one at https://aistudio.google.com/apikey
"""

import os
import re
import sys
import json
import argparse

from google import genai
from google.genai import types

import gemini_retry


# ----------------------------------------------------------------------
# STEP 1: Audio -> Text
# ----------------------------------------------------------------------
def audio_to_text(audio_path, language="en-IN"):
    """
    Converts a pre-recorded audio file (mp3/wav/m4a/ogg...) to text.
    Splits on silence so long meeting recordings are handled in chunks
    (Google's free speech API works best on short clips).
    Requires ffmpeg installed on the system (used internally by pydub).
    """
    import speech_recognition as sr
    from pydub import AudioSegment
    from pydub.silence import split_on_silence

    print(f"Loading audio file: {audio_path}")
    sound = AudioSegment.from_file(audio_path)
    sound = sound.set_channels(1).set_frame_rate(16000)

    chunks = split_on_silence(
        sound,
        min_silence_len=500,
        silence_thresh=sound.dBFS - 14,
        keep_silence=400,
    )
    if not chunks:
        chunks = [sound]

    recognizer = sr.Recognizer()
    # Without this, a slow/unresponsive API response could hang this call
    # (and the whole request) indefinitely with no error ever surfacing —
    # that's what was causing the "stuck, no output" symptom. Now it fails
    # with a catchable RequestError instead.
    recognizer.operation_timeout = 25  # seconds per chunk
    os.makedirs("temp_audio_chunks", exist_ok=True)
    full_text = []

    print(f"Split into {len(chunks)} chunk(s). Transcribing...")
    for i, chunk in enumerate(chunks):
        chunk_path = os.path.join("temp_audio_chunks", f"chunk_{i}.wav")
        chunk.export(chunk_path, format="wav")

        with sr.AudioFile(chunk_path) as source:
            audio_data = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio_data, language=language)
            full_text.append(text)
        except sr.UnknownValueError:
            continue  # silence / unclear audio in this chunk, skip
        except sr.RequestError as e:
            raise RuntimeError(f"Speech recognition API error: {e}")
        finally:
            os.remove(chunk_path)

    try:
        os.rmdir("temp_audio_chunks")
    except OSError:
        pass

    return " ".join(full_text)


# ----------------------------------------------------------------------
# STEP 2: Basic text cleanup (formatting only — no content decisions here)
# ----------------------------------------------------------------------
def clean_text(text):
    """
    Collapse repeated whitespace/newlines and trim the transcript.
    This is intentionally the ONLY preprocessing step left before the
    transcript reaches the LLM — no stopword removal, no sentence
    filtering, no keyword rules. Stripping stopwords or splitting into
    isolated sentences would actually hurt an LLM's understanding, since
    it relies on full sentence/paragraph context (e.g. "who" said "what
    about which task") to tell a real action item apart from small talk.
    """
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ----------------------------------------------------------------------
# STEP 3: Meeting Analysis — semantic understanding via the Claude API
# ----------------------------------------------------------------------
ANALYSIS_SYSTEM_PROMPT = """You are an expert executive assistant who writes professional \
meeting minutes. You will be given a raw, possibly messy meeting transcript (it may \
contain speech-to-text errors, filler words, and repeated lines).

Read the ENTIRE transcript before producing any output. Understand the context and \
meaning of the conversation — do not rely on keywords or copy sentences verbatim.

Completely IGNORE, and never turn into an action item / decision / deadline / summary line:
- Greetings, introductions, attendance/roll call, small talk
- Agenda transitions ("let's get started", "let's move on", "next topic", "thank you")
- Speaker names, unless that person is being assigned a task
- Repeated/duplicate statements (say it once)
- Filler words and disfluencies
- References to a PREVIOUS meeting, unless they create a NEW action or decision now

SUMMARY: Exactly TWO concise lines — line 1 says what the meeting was about, line 2 \
says the overall outcome. Written in your own words, never copied from the transcript.

ACTION ITEMS: Only genuine follow-up work (task assignments, follow-ups, implementation \
tasks, reports to prepare, surveys, deliverables, research). Exclude greetings, opinions, \
mere discussion, agenda transitions. Rewrite each as a short professional task. If an \
owner is named, format as "Owner — Task." (e.g. "Rahul — Complete the login page by \
tomorrow."). If no owner, just state the task.

DECISIONS: Only things the group actually agreed upon / approved / finalized / accepted / \
rejected / postponed. Exclude opinions or suggestions that were never accepted. Rewrite \
professionally.

DEADLINES: Only FUTURE deadlines (tomorrow, next Monday, by Friday, future meeting/delivery \
dates). Exclude past/historical dates and references to previous reports or meetings.

Quality rules: remove duplicate information, merge similar action items, merge similar \
decisions, keep every point concise, never copy long transcript passages, infer meaning \
instead of extracting exact sentences. If a section has no genuine content, return an \
empty list for it.

Respond with ONLY a valid JSON object (no markdown fences, no commentary) in exactly this \
shape:
{
  "summary": ["line 1", "line 2"],
  "action_items": ["...", "..."],
  "decisions": ["...", "..."],
  "deadlines": ["...", "..."]
}"""


def analyze_meeting_with_llm(transcript, model=None, output_language="English"):
    """
    Sends the full transcript to Gemini and gets back structured JSON: a
    2-line summary, action items, decisions, and deadlines — all derived
    from semantic understanding of the whole conversation rather than
    isolated sentence/keyword matching.

    output_language: the language the SUMMARY/ACTION ITEMS/DECISIONS/
    DEADLINES text should be written in (e.g. "Hindi", "Gujarati").
    Defaults to "English", which produces the exact same prompt (and
    therefore the same behavior) as before this parameter existed.

    model: optional explicit model override (e.g. from the CLI --model
    flag). If not given, uses gemini_retry's pinned GA primary model with
    automatic retry + fallback on transient 503 "high demand" errors —
    this replaces the old hardcoded "gemini-flash-latest" default, which
    Google documents as an experimental alias prone to those errors.

    Requires the GEMINI_API_KEY environment variable to be set.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    system_prompt = ANALYSIS_SYSTEM_PROMPT
    if output_language and output_language.strip().lower() != "english":
        system_prompt += f"""

LANGUAGE: The transcript may be in {output_language}, in English, or a mix of both \
(code-switching) — understand it regardless. Write the SUMMARY, ACTION ITEMS, \
DECISIONS, and DEADLINES text entirely in {output_language} (not English), while \
keeping the exact same JSON structure and field names shown above. Keep person names, \
company/product names, dates, times, numbers, and technical terms (e.g. "API", \
"project") accurate and do not mistranslate or alter them — it is fine for such terms \
to remain in their original form even inside {output_language} text."""

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        max_output_tokens=2000,
    )

    def _call(model_name):
        return client.models.generate_content(
            model=model_name,
            contents=f"Transcript:\n\n{transcript}",
            config=config,
        )

    if model:
        # Explicit override (e.g. CLI --model) — respect the caller's
        # choice, but still retry that same model on transient 503s.
        response = gemini_retry.call_with_retry_and_fallback(
            lambda m: _call(model), label="analyze_meeting_with_llm"
        )
    else:
        response = gemini_retry.call_with_retry_and_fallback(_call, label="analyze_meeting_with_llm")

    raw_output = (response.text or "").strip()

    # Defensive parsing: strip ```json fences if the model adds them anyway.
    if raw_output.startswith("```"):
        raw_output = re.sub(r"^```(json)?", "", raw_output).rstrip("`").strip()

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Could not parse the model's response as JSON: {e}\nRaw response:\n{raw_output}"
        )

    # Normalize shape / guard against a missing key.
    return {
        "summary": data.get("summary", []) or [],
        "action_items": data.get("action_items", []) or [],
        "decisions": data.get("decisions", []) or [],
        "deadlines": data.get("deadlines", []) or [],
    }


# ----------------------------------------------------------------------
# MAIN PIPELINE
# ----------------------------------------------------------------------
def meeting_summarizer(input_data, is_audio=False, model=None, language="en-IN", output_language="English"):
    if is_audio:
        raw_text = audio_to_text(input_data, language=language)
    else:
        raw_text = input_data

    if not raw_text or not raw_text.strip():
        return {"error": "No text could be extracted from the input."}

    raw_text = clean_text(raw_text)
    analysis = analyze_meeting_with_llm(raw_text, model=model, output_language=output_language)

    return {
        "transcript": raw_text,
        "summary": analysis["summary"],
        "action_items": analysis["action_items"],
        "decisions": analysis["decisions"],
        "deadlines": analysis["deadlines"],
    }


def format_report(result):
    """Builds the fixed, professional report layout as a single string."""
    lines = []
    lines.append("=" * 60)
    lines.append("MEETING SUMMARY REPORT")

    if "error" in result:
        lines.append(result["error"])
        return "\n".join(lines)

    lines.append("SUMMARY:")
    lines.extend(result["summary"] if result["summary"] else ["None"])
    lines.append("")

    lines.append("ACTION ITEMS:")
    if result["action_items"]:
        lines.extend(f"* {item}" for item in result["action_items"])
    else:
        lines.append("None")
    lines.append("")

    lines.append("DECISIONS:")
    if result["decisions"]:
        lines.extend(f"* {item}" for item in result["decisions"])
    else:
        lines.append("None")
    lines.append("")

    lines.append("DEADLINES:")
    if result["deadlines"]:
        lines.extend(f"* {item}" for item in result["deadlines"])
    else:
        lines.append("None")

    return "\n".join(lines)


def print_report(result):
    print("\n" + format_report(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Meeting Summarizer: audio/text -> summary, action items, deadlines, decisions"
    )
    parser.add_argument("--audio", type=str, help="Path to a pre-recorded audio file (mp3/wav/m4a/ogg)")
    parser.add_argument("--text", type=str, help="Path to a .txt transcript file")
    parser.add_argument("--model", type=str, default=None, help="Gemini model to use (default: resilient GA model with automatic fallback)")
    parser.add_argument("--language", type=str, default="en-IN", help="Speech recognition language code (default en-IN)")
    parser.add_argument("--output-language", type=str, default="English", help="Language for the generated Summary/Action Items/Decisions/Deadlines (default English)")
    args = parser.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: Set the GEMINI_API_KEY environment variable before running this script.")
        sys.exit(1)

    if args.audio:
        result = meeting_summarizer(args.audio, is_audio=True, model=args.model, language=args.language, output_language=args.output_language)
    elif args.text:
        with open(args.text, "r", encoding="utf-8") as f:
            text_data = f.read()
        result = meeting_summarizer(text_data, is_audio=False, model=args.model, output_language=args.output_language)
    else:
        print("Please provide either --audio <path> or --text <path>")
        sys.exit(1)

    print_report(result)
