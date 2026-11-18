"""
Meeting Summarizer — Web Application (API)
==============================================
IMPORTANT: The AI pipeline is untouched. This file only calls
meeting_summarizer() and format_report() from meeting_summarizer.py exactly
as before — same transcription, same prompt, same output. Everything below
(history, PDF export, analytics, insights, search) is a layer built AROUND
that pipeline, never inside it.

This file now serves as a pure JSON API plus the built React frontend
(frontend/dist) — the old server-rendered Jinja templates were replaced by
the React app per the UI/UX redesign. No API route, request shape, or
response shape changed in that process.
"""

import os
import time
import hashlib
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory, send_file

# UNCHANGED pipeline functions — imported individually (rather than only the
# meeting_summarizer() wrapper) so app.py can run the two independent LLM
# calls concurrently. Each function's code, prompt, and behavior is exactly
# what it was before; only the ORCHESTRATION (who calls what, in what order)
# changed. meeting_summarizer() itself is untouched and the CLI still uses it.
from meeting_summarizer import audio_to_text, clean_text, analyze_meeting_with_llm, format_report
import db
import analytics
import pdf_export
import insights  # separate, independent AI insights — does not touch the pipeline above
import languages
import assistant  # separate, independent AI Meeting Assistant chat — does not touch the pipeline above

FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")

app = Flask(__name__, static_folder=None)  # static handling done manually below
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB max upload

ALLOWED_AUDIO_EXT = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac"}

db.init_db()


# ----------------------------------------------------------------------
# Frontend (built React app) — serves the built assets, and falls back to
# index.html for any other route so React Router can handle client-side
# navigation (e.g. /history). static_folder=None above avoids a route
# conflict between Flask's default static handler and this catch-all.
# ----------------------------------------------------------------------
@app.route("/assets/<path:filename>")
def serve_asset(filename):
    return send_from_directory(os.path.join(FRONTEND_DIST, "assets"), filename)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    full_path = os.path.join(FRONTEND_DIST, path)
    if path and os.path.isfile(full_path):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


# ----------------------------------------------------------------------
# Analyze (calls the untouched pipeline, then saves + measures)
# ----------------------------------------------------------------------
def _probe_audio_duration(path):
    """
    Reads duration from the file's metadata (via ffprobe, through pydub's
    mediainfo helper) instead of decoding the entire audio into memory just
    to measure its length. This removes a full duplicate decode pass that
    used to happen here — audio_to_text() below still does its own decode
    (unchanged, required for transcription), but we no longer do a SECOND
    full decode purely to read the duration.
    """
    try:
        from pydub.utils import mediainfo
        info = mediainfo(path)
        return float(info["duration"])
    except Exception:
        # Fall back to a full decode only if metadata reading fails.
        try:
            from pydub import AudioSegment
            return len(AudioSegment.from_file(path)) / 1000.0
        except Exception:
            return None


@app.route("/api/languages", methods=["GET"])
def api_languages():
    return jsonify({"languages": languages.list_languages()})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    if not os.environ.get("GEMINI_API_KEY"):
        return jsonify({"error": "GEMINI_API_KEY is not set on the server. Set it and restart app.py."}), 500

    mode = request.form.get("mode")
    custom_title = (request.form.get("title") or "").strip()
    language_code = (request.form.get("language") or languages.DEFAULT_LANGUAGE_CODE).strip()
    lang = languages.get_language(language_code)
    duration_secs = None
    timings = {}
    t_request_start = time.perf_counter()

    try:
        # ------------------------------------------------------------
        # STEP 1: Get the transcript (+ compute a content hash for caching)
        # Language is part of the hash: the same text/audio requested in
        # two different languages must NOT collide in the cache — that
        # would return a result in the wrong language (see requirement 9,
        # "do not cache incorrectly").
        # ------------------------------------------------------------
        if mode == "text":
            text = request.form.get("text", "")
            if not text.strip():
                return jsonify({"error": "Please paste a transcript first."}), 400
            content_hash = hashlib.sha256(f"{language_code}::{text.strip()}".encode("utf-8")).hexdigest()

        elif mode == "audio":
            file = request.files.get("audio")
            if not file or file.filename == "":
                return jsonify({"error": "Please choose an audio file first."}), 400

            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ALLOWED_AUDIO_EXT:
                return jsonify({
                    "error": f"Unsupported file type '{ext}'. Use mp3, mp4, wav, m4a, ogg, or flac."
                }), 400

            file_bytes = file.read()
            content_hash = hashlib.sha256(language_code.encode("utf-8") + file_bytes).hexdigest()

        else:
            return jsonify({"error": "Invalid request — no mode specified."}), 400

        # ------------------------------------------------------------
        # CACHE CHECK: identical content already processed? Skip straight
        # to returning it — no transcription, no LLM calls, no DB write.
        # ------------------------------------------------------------
        t0 = time.perf_counter()
        cached = db.find_by_hash(content_hash)
        timings["cache_lookup_secs"] = round(time.perf_counter() - t0, 3)

        if cached:
            timings["total_secs"] = round(time.perf_counter() - t_request_start, 3)
            timings["cache_hit"] = True
            print(f"[timing] cache HIT for hash {content_hash[:10]}… — {timings}")
            stats = analytics.compute_analytics(
                transcript=cached["transcript"], action_items=cached["action_items"],
                decisions=cached["decisions"], deadlines=cached["deadlines"],
                duration_secs=cached["duration_secs"],
            )
            breakdown = analytics.compute_breakdown(
                stats["sentence_count"], stats["action_item_count"],
                stats["decision_count"], stats["deadline_count"],
            )
            return jsonify({
                "id": cached["id"], "title": cached["title"], "created_at": cached["created_at"],
                "input_type": cached["input_type"], "summary": cached["summary"],
                "action_items": cached["action_items"], "decisions": cached["decisions"],
                "deadlines": cached["deadlines"], "report_text": format_report(cached),
                "analytics": {
                    **stats,
                    "duration_display": analytics.format_duration(cached["duration_secs"]),
                    "processing_secs": 0.0,
                    "reading_time": insights.estimate_reading_time(stats["word_count"]),
                    "breakdown": breakdown,
                },
                "ai_insights": {
                    "meeting_type": cached.get("meeting_type") or "Not Available",
                    "primary_topic": cached.get("primary_topic") or "Not Available",
                    "sentiment": cached.get("sentiment") or "Not Available",
                },
                "language": cached.get("language") or "English",
                "language_warning": None,
                "timings": timings,
            })

        # ------------------------------------------------------------
        # STEP 2: Transcribe (audio only) — unchanged function/behavior
        # ------------------------------------------------------------
        if mode == "audio":
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            t0 = time.perf_counter()
            duration_secs = _probe_audio_duration(tmp_path)
            timings["duration_probe_secs"] = round(time.perf_counter() - t0, 3)

            try:
                t0 = time.perf_counter()
                raw_text = audio_to_text(tmp_path, language=lang["speech_code"])  # UNCHANGED function, now given the selected language
                timings["transcription_secs"] = round(time.perf_counter() - t0, 3)
            finally:
                os.remove(tmp_path)
        else:
            raw_text = text

        if not raw_text or not raw_text.strip():
            return jsonify({"error": "No text could be extracted from the input."}), 400

        transcript = clean_text(raw_text)  # UNCHANGED — same single cheap regex pass as before, Unicode-safe

        # Lightweight, best-effort sanity check — never a hard block, never silently wrong.
        language_warning = languages.detect_script_mismatch(transcript, language_code)

        # ------------------------------------------------------------
        # STEP 3: Main analysis + AI Insights — run CONCURRENTLY.
        # These are two independent network calls that both only need
        # `transcript` as input and don't depend on each other's output,
        # so there is no reason to wait for one before starting the other.
        # Each call is byte-for-byte the same function call as before.
        # ------------------------------------------------------------
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=2) as pool:
            main_future = pool.submit(analyze_meeting_with_llm, transcript, None, lang["name"])  # UNCHANGED function; model=None now uses the resilient GA primary+fallback strategy
            insights_future = pool.submit(insights.analyze_meeting_insights, transcript)  # UNCHANGED
            analysis = main_future.result()
            ai_insights = insights_future.result()
        timings["ai_analysis_plus_insights_parallel_secs"] = round(time.perf_counter() - t0, 3)

        result = {
            "transcript": transcript,
            "summary": analysis["summary"],
            "action_items": analysis["action_items"],
            "decisions": analysis["decisions"],
            "deadlines": analysis["deadlines"],
        }

    except Exception as e:
        return jsonify({"error": f"Something went wrong while processing: {e}"}), 500

    # ------------------------------------------------------------
    # STEP 4: Analytics (local, fast) + DB write
    # ------------------------------------------------------------
    t0 = time.perf_counter()
    stats = analytics.compute_analytics(
        transcript=result["transcript"],
        action_items=result["action_items"],
        decisions=result["decisions"],
        deadlines=result["deadlines"],
        duration_secs=duration_secs,
    )
    reading_time = insights.estimate_reading_time(stats["word_count"])
    breakdown = analytics.compute_breakdown(
        stats["sentence_count"], stats["action_item_count"],
        stats["decision_count"], stats["deadline_count"],
    )
    timings["analytics_secs"] = round(time.perf_counter() - t0, 3)

    created_at_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
    title = custom_title or analytics.generate_title(result["summary"], created_at_str)

    t0 = time.perf_counter()
    meeting_id = db.insert_meeting(
        title=title,
        created_at=created_at_str,
        input_type=mode,
        summary=result["summary"],
        action_items=result["action_items"],
        decisions=result["decisions"],
        deadlines=result["deadlines"],
        transcript=result["transcript"],
        duration_secs=duration_secs,
        word_count=stats["word_count"],
        sentence_count=stats["sentence_count"],
        top_keywords=stats["top_keywords"],
        processing_secs=round(time.perf_counter() - t_request_start, 2),
        meeting_type=ai_insights["meeting_type"],
        primary_topic=ai_insights["primary_topic"],
        sentiment=ai_insights["sentiment"],
        content_hash=content_hash,
        language=lang["name"],
    )
    timings["db_write_secs"] = round(time.perf_counter() - t0, 3)
    timings["total_secs"] = round(time.perf_counter() - t_request_start, 3)
    timings["cache_hit"] = False

    print(f"[timing] {mode} meeting id={meeting_id}: {timings}")

    processing_secs = timings["total_secs"]

    return jsonify({
        "id": meeting_id,
        "title": title,
        "created_at": created_at_str,
        "input_type": mode,
        "summary": result["summary"],
        "action_items": result["action_items"],
        "decisions": result["decisions"],
        "deadlines": result["deadlines"],
        "report_text": format_report(result),  # identical to CLI output
        "analytics": {
            **stats,
            "duration_display": analytics.format_duration(duration_secs),
            "processing_secs": processing_secs,
            "reading_time": reading_time,
            "breakdown": breakdown,
        },
        "ai_insights": {
            "meeting_type": ai_insights["meeting_type"] or "Not Available",
            "primary_topic": ai_insights["primary_topic"] or "Not Available",
            "sentiment": ai_insights["sentiment"] or "Not Available",
        },
        "language": lang["name"],
        "language_warning": language_warning,
        "timings": timings,
    })


# ----------------------------------------------------------------------
# Meeting History API
# ----------------------------------------------------------------------
@app.route("/api/meetings", methods=["GET"])
def api_list_meetings():
    search = request.args.get("q", "").strip()
    meetings = db.list_meetings(search=search or None)
    return jsonify({"meetings": meetings})


@app.route("/api/meetings/<int:meeting_id>", methods=["GET"])
def api_get_meeting(meeting_id):
    meeting = db.get_meeting(meeting_id)
    if not meeting:
        return jsonify({"error": "Meeting not found."}), 404

    stats = analytics.compute_analytics(
        transcript=meeting["transcript"],
        action_items=meeting["action_items"],
        decisions=meeting["decisions"],
        deadlines=meeting["deadlines"],
        duration_secs=meeting["duration_secs"],
    )
    breakdown = analytics.compute_breakdown(
        stats["sentence_count"], stats["action_item_count"],
        stats["decision_count"], stats["deadline_count"],
    )
    meeting["analytics"] = {
        **stats,
        "duration_display": analytics.format_duration(meeting["duration_secs"]),
        "processing_secs": meeting.get("processing_secs"),
        "reading_time": insights.estimate_reading_time(stats["word_count"]),
        "breakdown": breakdown,
    }
    meeting["ai_insights"] = {
        "meeting_type": meeting.get("meeting_type") or "Not Available",
        "primary_topic": meeting.get("primary_topic") or "Not Available",
        "sentiment": meeting.get("sentiment") or "Not Available",
    }
    meeting["language"] = meeting.get("language") or "English"
    meeting["report_text"] = format_report(meeting)
    return jsonify(meeting)


@app.route("/api/meetings/<int:meeting_id>", methods=["DELETE"])
def api_delete_meeting(meeting_id):
    if not db.get_meeting(meeting_id):
        return jsonify({"error": "Meeting not found."}), 404
    db.delete_meeting(meeting_id)
    return jsonify({"ok": True})


@app.route("/api/meetings/<int:meeting_id>/pdf", methods=["GET"])
def api_meeting_pdf(meeting_id):
    meeting = db.get_meeting(meeting_id)
    if not meeting:
        return jsonify({"error": "Meeting not found."}), 404

    buf = pdf_export.generate_pdf(meeting)
    safe_name = "".join(c for c in meeting["title"] if c.isalnum() or c in " _-").strip() or "meeting"
    return send_file(
        buf, mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{safe_name}.pdf",
    )


# ----------------------------------------------------------------------
# AI Meeting Assistant
# ----------------------------------------------------------------------
@app.route("/api/meetings/<int:meeting_id>/suggested-questions", methods=["GET"])
def api_suggested_questions(meeting_id):
    meeting = db.get_meeting(meeting_id)
    if not meeting:
        return jsonify({"error": "Meeting not found."}), 404
    return jsonify({"questions": assistant.suggested_questions(meeting)})


@app.route("/api/meetings/<int:meeting_id>/chat", methods=["POST"])
def api_meeting_chat(meeting_id):
    if not os.environ.get("GEMINI_API_KEY"):
        return jsonify({"error": "GEMINI_API_KEY is not set on the server. Set it and restart app.py."}), 500

    # Scoped strictly to THIS meeting_id — db.get_meeting only ever returns
    # the one row matching this id, so there is no path for another
    # meeting's transcript/history to leak into this answer.
    meeting = db.get_meeting(meeting_id)
    if not meeting:
        return jsonify({"error": "Meeting not found."}), 404

    body = request.get_json(silent=True) or {}
    question = (body.get("message") or "").strip()
    history = body.get("history") or []

    if not question:
        return jsonify({"error": "Please type a question."}), 400
    if not isinstance(history, list):
        history = []

    reply = assistant.ask_assistant(meeting, question, history=history)
    return jsonify({"reply": reply, "language": meeting.get("language") or "English"})


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY is not set. The app will start, but /api/analyze will fail until you set it.")
    app.run(debug=True, port=5000)
