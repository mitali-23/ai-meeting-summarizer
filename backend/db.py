"""
Database layer for Meeting History.
=======================================
Plain sqlite3 (no ORM needed for this size of app). This file has NO
knowledge of how a meeting is analyzed — it only stores/retrieves the
results that app.py hands it after calling the (untouched) AI pipeline
in meeting_summarizer.py.
"""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meetings.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT NOT NULL,
            created_at     TEXT NOT NULL,
            input_type     TEXT NOT NULL,
            summary        TEXT NOT NULL,
            action_items   TEXT NOT NULL,
            decisions      TEXT NOT NULL,
            deadlines      TEXT NOT NULL,
            transcript     TEXT NOT NULL,
            duration_secs  REAL,
            word_count     INTEGER,
            sentence_count INTEGER,
            top_keywords   TEXT,
            processing_secs REAL,
            meeting_type   TEXT,
            primary_topic  TEXT,
            sentiment      TEXT,
            content_hash   TEXT,
            language       TEXT
        )
    """)
    # Safe migration: older databases (from before these columns existed)
    # just get the new columns added, existing rows keep NULL for them.
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(meetings)")}
    for col, coltype in [
        ("processing_secs", "REAL"), ("meeting_type", "TEXT"),
        ("primary_topic", "TEXT"), ("sentiment", "TEXT"),
        ("content_hash", "TEXT"), ("language", "TEXT"),
    ]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE meetings ADD COLUMN {col} {coltype}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_meetings_content_hash ON meetings(content_hash)")
    conn.commit()
    conn.close()


def _row_to_dict(row, include_transcript=True):
    d = {
        "id": row["id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "input_type": row["input_type"],
        "summary": json.loads(row["summary"]),
        "action_items": json.loads(row["action_items"]),
        "decisions": json.loads(row["decisions"]),
        "deadlines": json.loads(row["deadlines"]),
        "duration_secs": row["duration_secs"],
        "word_count": row["word_count"],
        "sentence_count": row["sentence_count"],
        "top_keywords": json.loads(row["top_keywords"]) if row["top_keywords"] else [],
        "processing_secs": row["processing_secs"],
        "meeting_type": row["meeting_type"],
        "primary_topic": row["primary_topic"],
        "sentiment": row["sentiment"],
        "language": row["language"] or "English",
    }
    if include_transcript:
        d["transcript"] = row["transcript"]
    return d


def insert_meeting(title, created_at, input_type, summary, action_items, decisions, deadlines,
                    transcript, duration_secs, word_count, sentence_count, top_keywords,
                    processing_secs=None, meeting_type=None, primary_topic=None, sentiment=None,
                    content_hash=None, language="English"):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO meetings
           (title, created_at, input_type, summary, action_items, decisions,
            deadlines, transcript, duration_secs, word_count, sentence_count, top_keywords,
            processing_secs, meeting_type, primary_topic, sentiment, content_hash, language)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            title,
            created_at,
            input_type,
            json.dumps(summary),
            json.dumps(action_items),
            json.dumps(decisions),
            json.dumps(deadlines),
            transcript,
            duration_secs,
            word_count,
            sentence_count,
            json.dumps(top_keywords),
            processing_secs,
            meeting_type,
            primary_topic,
            sentiment,
            content_hash,
            language,
        ),
    )
    conn.commit()
    meeting_id = cur.lastrowid
    conn.close()
    return meeting_id


def find_by_hash(content_hash):
    """
    Looks up a previously processed meeting with the exact same content hash
    (sha256 of the uploaded audio bytes or the raw pasted text). Used to skip
    re-running transcription + LLM calls when the identical input is submitted
    again. Returns None on no match — never returns a partial/wrong match,
    since the hash is over the full content.
    """
    if not content_hash:
        return None
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM meetings WHERE content_hash = ? ORDER BY id DESC LIMIT 1",
        (content_hash,),
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def list_meetings(search=None):
    conn = get_db()
    if search:
        rows = conn.execute(
            "SELECT * FROM meetings WHERE title LIKE ? ORDER BY id DESC",
            (f"%{search}%",),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM meetings ORDER BY id DESC").fetchall()
    conn.close()
    # Lightweight list view — no transcript, keep the payload small.
    return [_row_to_dict(r, include_transcript=False) for r in rows]


def get_meeting(meeting_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def delete_meeting(meeting_id):
    conn = get_db()
    conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
    conn.commit()
    conn.close()
