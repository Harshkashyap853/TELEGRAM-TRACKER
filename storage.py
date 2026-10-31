"""
SQLite storage.

Stores:
    - channel active/inactive state
    - previously posted products
"""

import sqlite3
import threading

from config import DB_PATH


_lock = threading.RLock()


_conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False,
)


_conn.execute(
    """
    CREATE TABLE IF NOT EXISTS channel_state (
        chat_id INTEGER PRIMARY KEY,
        active INTEGER NOT NULL
    )
    """
)


_conn.execute(
    """
    CREATE TABLE IF NOT EXISTS seen (
        deal_id TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)


_conn.commit()


def set_active(
    chat_id: int,
    active: bool,
) -> None:

    with _lock:

        _conn.execute(
            """
            INSERT OR REPLACE INTO channel_state
            (chat_id, active)
            VALUES (?, ?)
            """,
            (
                chat_id,
                int(active),
            ),
        )

        _conn.commit()


def is_active(
    chat_id: int,
) -> bool:

    with _lock:

        row = _conn.execute(
            """
            SELECT active
            FROM channel_state
            WHERE chat_id = ?
            """,
            (chat_id,),
        ).fetchone()


    return bool(
        row and row[0]
    )


def already_seen(
    deal_id: str,
) -> bool:

    with _lock:

        row = _conn.execute(
            """
            SELECT 1
            FROM seen
            WHERE deal_id = ?
            LIMIT 1
            """,
            (deal_id,),
        ).fetchone()


    return row is not None


def mark_seen(
    deal_id: str,
) -> None:

    with _lock:

        _conn.execute(
            """
            INSERT OR IGNORE INTO seen
            (deal_id)
            VALUES (?)
            """,
            (deal_id,),
        )

        _conn.commit()


def clear_seen() -> None:

    with _lock:

        _conn.execute(
            "DELETE FROM seen"
        )

        _conn.commit()