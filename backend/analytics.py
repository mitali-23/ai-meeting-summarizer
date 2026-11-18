"""
Meeting Analytics.
=====================
Simple, independent text statistics (word/sentence counts, top keywords).
This has nothing to do with the AI summarization pipeline in
meeting_summarizer.py — it just measures the transcript directly, so it
can never change what the AI produces.
"""

import re
from collections import Counter

# A small generic stopword list, used ONLY to keep "top keywords" readable.
# (This is unrelated to — and does not touch — the AI analysis pipeline.)
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "to", "of", "in",
    "on", "at", "for", "with", "about", "as", "by", "is", "are", "was", "were",
    "be", "been", "being", "this", "that", "these", "those", "it", "its", "we",
    "our", "us", "you", "your", "they", "their", "he", "she", "his", "her",
    "i", "me", "my", "will", "would", "can", "could", "should", "shall",
    "do", "does", "did", "have", "has", "had", "not", "just", "also", "there",
    "here", "what", "which", "who", "whom", "when", "where", "why", "how",
    "all", "any", "some", "no", "yes", "okay", "ok", "um", "uh", "like",
    "get", "got", "going", "go", "let", "lets", "let's", "think", "know",
    "want", "need", "one", "two", "into", "up", "out", "so", "than",
}


def compute_analytics(transcript, action_items, decisions, deadlines, duration_secs=None):
    words = re.findall(r"[A-Za-z']+", transcript)
    word_count = len(words)

    sentences = [s for s in re.split(r"[.!?]+", transcript) if s.strip()]
    sentence_count = len(sentences)

    freq = Counter(
        w.lower() for w in words
        if len(w) > 3 and w.lower() not in _STOPWORDS
    )
    top_pairs = freq.most_common(8)
    top_keywords = [word for word, _ in top_pairs]
    keyword_freq = [{"word": word, "count": count} for word, count in top_pairs]

    def _count(items):
        # Extraction functions return ["None"] when empty — don't count that as 1.
        if not items or items == ["None"] or items == ["no clear action items found."]:
            return 0
        return len(items)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "top_keywords": top_keywords,
        "keyword_freq": keyword_freq,
        "action_item_count": _count(action_items),
        "decision_count": _count(decisions),
        "deadline_count": _count(deadlines),
        "duration_secs": duration_secs,
    }


def format_duration(seconds):
    if seconds is None:
        return "N/A"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def generate_title(summary_lines, created_at_str):
    """Auto-generate a short meeting title from the summary's first line."""
    if summary_lines:
        first = summary_lines[0].strip()
        words = first.split()
        short = " ".join(words[:8])
        if len(words) > 8:
            short += "…"
        if short:
            return short
    return f"Meeting — {created_at_str}"


def compute_breakdown(sentence_count, action_count, decision_count, deadline_count):
    """
    Rough composition of the meeting for the doughnut chart: how many
    sentences were action items / decisions / deadlines vs general
    discussion. Derived directly from real counts already computed —
    not a separate AI judgment, so there's nothing to fabricate.
    """
    tagged = action_count + decision_count + deadline_count
    discussion = max(sentence_count - tagged, 0) if sentence_count else 0
    if discussion == 0 and tagged == 0:
        discussion = 1  # avoid an entirely empty chart
    return {
        "discussion": discussion,
        "action_items": action_count,
        "decisions": decision_count,
        "deadlines": deadline_count,
    }
