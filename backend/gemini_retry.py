"""
Shared Gemini call resilience helper.
=========================================
Used by every module that calls the Gemini API (meeting_summarizer.py,
insights.py, assistant.py) to survive transient 503 "model overloaded"
errors. This is pure infrastructure (retry/backoff/fallback) — it contains
no prompts, no business logic, and doesn't know what any caller is asking
Gemini to do. Sharing it does NOT couple those otherwise-independent
modules together.

ROOT CAUSE of the 503s: "gemini-flash-latest" (used everywhere before this
fix) is documented by Google as an ALIAS FOR AN EXPERIMENTAL MODEL —
"typically not suitable for production use and comes with more restrictive
rate limits." That's what was producing "high demand" 503 errors. The
models below are pinned, generally-available (GA) production models
instead — verified against Google's current model list, not guessed.
"""

import time
from google.genai import errors as genai_errors

PRIMARY_MODEL = "gemini-3.6-flash"        # current GA workhorse Flash model
FALLBACK_MODEL = "gemini-3.5-flash-lite"  # GA, high-throughput — same task type, used only if primary is unavailable

MAX_RETRIES = 3
RETRY_BACKOFF_SECS = [1, 2, 4]  # attempt 1 -> wait 1s, attempt 2 -> wait 2s, attempt 3 -> wait 4s


def call_with_retry_and_fallback(call_fn, label="gemini_call"):
    """
    call_fn(model_name) must perform the actual client.models.generate_content(...)
    call using the given model name and return its result (or raise).

    Strategy: try PRIMARY_MODEL up to MAX_RETRIES times with exponential
    backoff, but ONLY retry on a 503 (transient overload) — other errors
    (bad request, auth, etc.) are not retried since retrying won't fix them.
    If the primary is still unavailable after retries, try FALLBACK_MODEL
    once. Raises the last exception if everything fails, so the caller
    decides its own user-facing message (never exposed raw here).

    Logs each stage (model + outcome only — never API keys or meeting
    content) so failover is visible in the server console.
    """
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = call_fn(PRIMARY_MODEL)
            if attempt > 1:
                print(f"[{label}] primary model ({PRIMARY_MODEL}) succeeded on retry attempt {attempt}")
            return result
        except genai_errors.ServerError as e:
            last_exc = e
            code = getattr(e, "code", None)
            is_503 = code == 503
            status_desc = "503 UNAVAILABLE" if is_503 else f"ServerError code={code}"
            print(f"[{label}] primary={PRIMARY_MODEL} attempt {attempt}/{MAX_RETRIES} -> {status_desc}")
            if not is_503 or attempt == MAX_RETRIES:
                break
            time.sleep(RETRY_BACKOFF_SECS[attempt - 1])
        except Exception as e:
            print(f"[{label}] primary={PRIMARY_MODEL} non-retryable error: {e}")
            raise

    print(f"[{label}] primary unavailable after {MAX_RETRIES} attempts -> trying fallback={FALLBACK_MODEL}")
    try:
        result = call_fn(FALLBACK_MODEL)
        print(f"[{label}] fallback={FALLBACK_MODEL} result=SUCCESS")
        return result
    except Exception as e:
        print(f"[{label}] fallback={FALLBACK_MODEL} result=FAILED ({e})")
        raise last_exc if last_exc else e
