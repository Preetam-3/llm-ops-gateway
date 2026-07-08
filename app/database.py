"""SQLite persistence layer — stores conversations and messages locally."""

import asyncio
import hashlib
import secrets
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
        CREATE TABLE IF NOT EXISTS api_keys (
            id          TEXT PRIMARY KEY,
            key_hash    TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            prefix      TEXT NOT NULL,
            is_active   INTEGER DEFAULT 1,
            created_at  TIMESTAMP DEFAULT (datetime('now')),
            revoked_at  TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS request_logs (
            id                TEXT PRIMARY KEY,
            conversation_id   TEXT,
            request_body      TEXT,
            response_body     TEXT,
            model             TEXT,
            prompt_tokens     INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens      INTEGER DEFAULT 0,
            estimated_cost    REAL DEFAULT 0,
            duration_seconds  REAL DEFAULT 0,
            ip_address        TEXT,
            api_key_prefix    TEXT,
            status            TEXT DEFAULT 'success',
            created_at        TIMESTAMP DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
        CREATE INDEX IF NOT EXISTS idx_request_logs_created ON request_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_request_logs_model ON request_logs(model);
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


# ── API key helpers ──


def _create_api_key(name: str) -> dict:
    """Generate a key, store its hash, return the raw key (shown once)."""
    raw_key = "gw_" + secrets.token_hex(16)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    prefix = raw_key[:10]  # e.g. "gw_a1b2c3d4"
    key_id = str(uuid.uuid4())
    _db.execute(
        "INSERT INTO api_keys (id, key_hash, name, prefix) VALUES (?, ?, ?, ?)",
        (key_id, key_hash, name, prefix),
    )
    _db.commit()
    return {"id": key_id, "raw_key": raw_key, "name": name, "prefix": prefix}


def _list_api_keys() -> list[dict]:
    cursor = _db.execute(
        "SELECT id, name, prefix, is_active, created_at, revoked_at "
        "FROM api_keys ORDER BY created_at DESC"
    )
    return [dict(row) for row in cursor.fetchall()]


def _revoke_api_key(key_id: str) -> bool:
    cursor = _db.execute(
        "UPDATE api_keys SET is_active = 0, revoked_at = datetime('now') "
        "WHERE id = ? AND is_active = 1",
        (key_id,),
    )
    _db.commit()
    return cursor.rowcount > 0


def _get_api_key_by_hash(key_hash: str) -> dict | None:
    cursor = _db.execute(
        "SELECT id, name, prefix, is_active FROM api_keys WHERE key_hash = ?",
        (key_hash,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


# ── Request log helpers ──


def _log_request(
    conversation_id: str | None = None,
    request_body: str | None = None,
    response_body: str | None = None,
    model: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    estimated_cost: float = 0.0,
    duration_seconds: float = 0.0,
    ip_address: str | None = None,
    api_key_prefix: str | None = None,
    status: str = "success",
) -> str:
    log_id = str(uuid.uuid4())
    _db.execute(
        """INSERT INTO request_logs
           (id, conversation_id, request_body, response_body, model,
            prompt_tokens, completion_tokens, total_tokens,
            estimated_cost, duration_seconds, ip_address, api_key_prefix, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            log_id, conversation_id, request_body, response_body, model,
            prompt_tokens, completion_tokens, total_tokens,
            estimated_cost, duration_seconds, ip_address, api_key_prefix, status,
        ),
    )
    _db.commit()
    return log_id


def _search_request_logs(
    q: str | None = None,
    model: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = []
    params: list = []

    if q:
        conditions.append("(request_body LIKE ? OR response_body LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if model:
        conditions.append("model = ?")
        params.append(model)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if start_date:
        conditions.append("created_at >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("created_at <= ?")
        params.append(end_date)

    where = " AND ".join(conditions) if conditions else "1"
    cursor = _db.execute(
        f"SELECT * FROM request_logs WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    )
    return [dict(row) for row in cursor.fetchall()]


def _get_log_stats() -> dict:
    """Aggregate stats across all request logs."""
    cursor = _db.execute(
        "SELECT COUNT(*) as total_requests, "
        "COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens, "
        "COALESCE(SUM(completion_tokens), 0) as total_completion_tokens, "
        "COALESCE(SUM(total_tokens), 0) as total_tokens, "
        "COALESCE(SUM(estimated_cost), 0) as total_cost, "
        "COALESCE(AVG(duration_seconds), 0) as avg_duration "
        "FROM request_logs"
    )
    return dict(cursor.fetchone())


def _get_cost_by_period(period: str = "day") -> list[dict]:
    """Cumulative cost grouped by day or month."""
    if period == "month":
        date_expr = "strftime('%Y-%m', created_at)"
    else:
        date_expr = "date(created_at)"
    cursor = _db.execute(
        f"SELECT {date_expr} as period, "
        "COUNT(*) as requests, "
        "COALESCE(SUM(prompt_tokens), 0) as prompt_tokens, "
        "COALESCE(SUM(completion_tokens), 0) as completion_tokens, "
        "COALESCE(SUM(total_tokens), 0) as total_tokens, "
        "COALESCE(SUM(estimated_cost), 0) as cost "
        "FROM request_logs "
        "GROUP BY period ORDER BY period DESC LIMIT 90"
    )
    return [dict(row) for row in cursor.fetchall()]


def _get_cost_by_model() -> list[dict]:
    """Cumulative cost grouped by model."""
    cursor = _db.execute(
        "SELECT model, "
        "COUNT(*) as requests, "
        "COALESCE(SUM(prompt_tokens), 0) as prompt_tokens, "
        "COALESCE(SUM(completion_tokens), 0) as completion_tokens, "
        "COALESCE(SUM(total_tokens), 0) as total_tokens, "
        "COALESCE(SUM(estimated_cost), 0) as cost "
        "FROM request_logs WHERE model IS NOT NULL "
        "GROUP BY model ORDER BY cost DESC"
    )
    return [dict(row) for row in cursor.fetchall()]


def _get_cost_by_key_prefix() -> list[dict]:
    """Cumulative cost grouped by API key prefix."""
    cursor = _db.execute(
        "SELECT r.api_key_prefix, "
        "COALESCE(a.name, 'admin') as key_name, "
        "COUNT(*) as requests, "
        "COALESCE(SUM(r.prompt_tokens), 0) as prompt_tokens, "
        "COALESCE(SUM(r.completion_tokens), 0) as completion_tokens, "
        "COALESCE(SUM(r.total_tokens), 0) as total_tokens, "
        "COALESCE(SUM(r.estimated_cost), 0) as cost "
        "FROM request_logs r "
        "LEFT JOIN api_keys a ON a.prefix = r.api_key_prefix "
        "WHERE r.api_key_prefix IS NOT NULL "
        "GROUP BY r.api_key_prefix ORDER BY cost DESC"
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


async def create_api_key(name: str) -> dict:
    return await asyncio.to_thread(_create_api_key, name)


async def list_api_keys() -> list[dict]:
    return await asyncio.to_thread(_list_api_keys)


async def revoke_api_key(key_id: str) -> bool:
    return await asyncio.to_thread(_revoke_api_key, key_id)


async def get_api_key_by_hash(key_hash: str) -> dict | None:
    return await asyncio.to_thread(_get_api_key_by_hash, key_hash)


async def log_request(
    conversation_id: str | None = None,
    request_body: str | None = None,
    response_body: str | None = None,
    model: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    estimated_cost: float = 0.0,
    duration_seconds: float = 0.0,
    ip_address: str | None = None,
    api_key_prefix: str | None = None,
    status: str = "success",
) -> str:
    return await asyncio.to_thread(
        _log_request, conversation_id, request_body, response_body, model,
        prompt_tokens, completion_tokens, total_tokens,
        estimated_cost, duration_seconds, ip_address, api_key_prefix, status,
    )


async def search_request_logs(
    q: str | None = None,
    model: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    return await asyncio.to_thread(
        _search_request_logs, q, model, status, start_date, end_date, limit, offset,
    )


async def get_log_stats() -> dict:
    return await asyncio.to_thread(_get_log_stats)


async def get_cost_by_period(period: str = "day") -> list[dict]:
    return await asyncio.to_thread(_get_cost_by_period, period)


async def get_cost_by_model() -> list[dict]:
    return await asyncio.to_thread(_get_cost_by_model)


async def get_cost_by_key_prefix() -> list[dict]:
    return await asyncio.to_thread(_get_cost_by_key_prefix)
