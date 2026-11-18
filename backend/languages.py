"""
Language registry — single source of truth for multilingual support.
=========================================================================
Add a new language by adding one entry here; nothing else needs to change
to make it selectable in the UI, used for speech recognition, and used as
the AI output language.

- `speech_code`: BCP-47 code passed to Google's speech-recognition API
  (used by meeting_summarizer.audio_to_text — that function already
  accepted a `language` parameter, it just wasn't being used until now).
- `name`: friendly display name, also used as the AI output-language
  instruction (e.g. "Write the output in Hindi.").
- `script_ranges`: Unicode code point ranges typical of this language's
  script, used only for the lightweight mismatch-detection warning
  (requirement 9) — NOT used for translation or processing.
"""

LANGUAGES = [
    {"code": "en", "name": "English",    "speech_code": "en-IN", "script_ranges": [(0x0041, 0x007A)]},
    {"code": "hi", "name": "Hindi",      "speech_code": "hi-IN", "script_ranges": [(0x0900, 0x097F)]},  # Devanagari
    {"code": "gu", "name": "Gujarati",   "speech_code": "gu-IN", "script_ranges": [(0x0A80, 0x0AFF)]},
    {"code": "bn", "name": "Bengali",    "speech_code": "bn-IN", "script_ranges": [(0x0980, 0x09FF)]},
    {"code": "mr", "name": "Marathi",    "speech_code": "mr-IN", "script_ranges": [(0x0900, 0x097F)]},  # Devanagari
    {"code": "ta", "name": "Tamil",      "speech_code": "ta-IN", "script_ranges": [(0x0B80, 0x0BFF)]},
    {"code": "te", "name": "Telugu",     "speech_code": "te-IN", "script_ranges": [(0x0C00, 0x0C7F)]},
    {"code": "kn", "name": "Kannada",    "speech_code": "kn-IN", "script_ranges": [(0x0C80, 0x0CFF)]},
    {"code": "ml", "name": "Malayalam",  "speech_code": "ml-IN", "script_ranges": [(0x0D00, 0x0D7F)]},
    {"code": "pa", "name": "Punjabi",    "speech_code": "pa-IN", "script_ranges": [(0x0A00, 0x0A7F)]},  # Gurmukhi
    {"code": "ur", "name": "Urdu",       "speech_code": "ur-PK", "script_ranges": [(0x0600, 0x06FF)]},  # Arabic script
    {"code": "es", "name": "Spanish",    "speech_code": "es-ES", "script_ranges": [(0x0041, 0x007A)]},
    {"code": "fr", "name": "French",     "speech_code": "fr-FR", "script_ranges": [(0x0041, 0x007A)]},
    {"code": "de", "name": "German",     "speech_code": "de-DE", "script_ranges": [(0x0041, 0x007A)]},
    {"code": "ar", "name": "Arabic",     "speech_code": "ar-SA", "script_ranges": [(0x0600, 0x06FF)]},
    {"code": "pt", "name": "Portuguese", "speech_code": "pt-PT", "script_ranges": [(0x0041, 0x007A)]},
    {"code": "zh", "name": "Chinese",    "speech_code": "zh-CN", "script_ranges": [(0x4E00, 0x9FFF)]},
    {"code": "ja", "name": "Japanese",   "speech_code": "ja-JP", "script_ranges": [(0x3040, 0x30FF), (0x4E00, 0x9FFF)]},
]

_BY_CODE = {lang["code"]: lang for lang in LANGUAGES}
DEFAULT_LANGUAGE_CODE = "en"


def get_language(code):
    """Returns the language entry for a code, defaulting to English if unknown."""
    return _BY_CODE.get(code, _BY_CODE[DEFAULT_LANGUAGE_CODE])


def list_languages():
    """Public list for the frontend dropdown: [{code, name}, ...]."""
    return [{"code": l["code"], "name": l["name"]} for l in LANGUAGES]


def detect_script_mismatch(text, selected_code):
    """
    Lightweight sanity check (NOT language detection/translation): if the
    selected language uses a distinctive non-Latin script (Devanagari,
    Gujarati, Arabic, etc.) but the transcript is overwhelmingly plain
    ASCII Latin text, that's a strong signal of a language/content
    mismatch worth warning about. Returns a warning string, or None if
    there's no clear mismatch. Deliberately conservative — mixed-language
    (code-switched) text is expected and should NOT trigger a warning.
    """
    lang = get_language(selected_code)
    if selected_code in ("en", "es", "fr", "de", "pt"):
        return None  # Latin-script languages — no reliable script signal to check

    sample = text[:2000]
    letters = [c for c in sample if c.isalpha()]
    if len(letters) < 20:
        return None  # not enough signal to judge confidently

    in_script = sum(
        1 for c in letters
        if any(lo <= ord(c) <= hi for lo, hi in lang["script_ranges"])
    )
    ratio = in_script / len(letters)

    if ratio < 0.15:  # almost no characters in the expected script at all
        return (
            f"Selected language: {lang['name']}. The detected content appears to be "
            f"in a different script (e.g. English/Latin). Please verify the selected language."
        )
    return None
