"""SQLite persistence layer — stores conversations and messages locally."""

import asyncio
import sqlite3
import uuid

_db: sqlite3.Connection | None = None


def init_db(db_path: str) -> None:
    """Create tables and indices. Call once at startup from the main thread."""
    global _db
    _db = sqlite3.connect(db_path, check_same_thread=False)
    _db.row_factory = sqlite3.Row
    _db.execute("PRAGMA journal_mode=WAL")
    _db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          TEXT PRIMARY KEY,
            title       TEXT DEFAULT '',
            created_at  TIMESTAMP DEFAULT (datetime('now')),
            updated_at  TIMESTAMP DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS messages (
            id                TEXT PRIMARY KEY,
            conversation_id   TEXT NOT NULL,
            role              TEXT NOT NULL,
            content           TEXT NOT NULL,
            model             TEXT,
            prompt_tokens     INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens      INTEGER DEFAULT 0,
            estimated_cost    REAL    DEFAULT 0,
            duration_seconds  REAL    DEFAULT 0,
            created_at        TIMESTAMP DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
    """)
    _db.commit()


def close_db() -> None:
    global _db
    if _db is not None:
        _db.close()
        _db = None


# ── Sync helpers (run via asyncio.to_thread) ──


def _save_conversation(conv_id: str) -> None:
    _db.execute(
        "INSERT INTO conversations (id, updated_at) VALUES (?, datetime('now')) "
        "ON CONFLICT(id) DO UPDATE SET updated_at = datetime('now')",
        (conv_id,),
    )
    _db.commit()


def _save_message(
    conv_id: str,
    role: str,
    content: str,
    model: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    estimated_cost: float = 0.0,
    duration_seconds: float = 0.0,
) -> str:
    msg_id = str(uuid.uuid4())
    _db.execute(
        """INSERT INTO messages
           (id, conversation_id, role, content, model,
            prompt_tokens, completion_tokens, total_tokens,
            estimated_cost, duration_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            msg_id, conv_id, role, content, model,
            prompt_tokens, completion_tokens, total_tokens,
            estimated_cost, duration_seconds,
        ),
    )
    _db.commit()
    return msg_id


def _get_conversations(limit: int = 20, offset: int = 0) -> list[dict]:
    cursor = _db.execute(
        """SELECT c.*,
                  (SELECT content FROM messages
                   WHERE conversation_id = c.id
                   ORDER BY created_at LIMIT 1) AS preview
           FROM conversations c
           ORDER BY updated_at DESC
           LIMIT ? OFFSET ?""",
        (limit, offset),
    )
    return [dict(row) for row in cursor.fetchall()]


def _get_messages(conv_id: str) -> list[dict]:
    cursor = _db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
        (conv_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


# ── Public async API ──


async def save_conversation(conv_id: str) -> None:
    await asyncio.to_thread(_save_conversation, conv_id)


async def save_message(
    conv_id: str,
    role: str,
    content: str,
    model: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    estimated_cost: float = 0.0,
    duration_seconds: float = 0.0,
) -> str:
    return await asyncio.to_thread(
        _save_message, conv_id, role, content, model,
        prompt_tokens, completion_tokens, total_tokens,
        estimated_cost, duration_seconds,
    )


async def get_conversations(limit: int = 20, offset: int = 0) -> list[dict]:
    return await asyncio.to_thread(_get_conversations, limit, offset)


async def get_messages(conv_id: str) -> list[dict]:
    return await asyncio.to_thread(_get_messages, conv_id)
