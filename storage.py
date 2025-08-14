import os
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# --- Connection pool ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL env var is required for PostgreSQL")

# autocommit=True so DDL/DML apply immediately
pool = ConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=5, kwargs={"autocommit": True})

@contextmanager
def get_conn():
    with pool.connection() as conn:
        conn.row_factory = dict_row
        yield conn

# =====================
# 🔧 Init & Schema
# =====================

def init_db():
    """Create tables and indexes if not exist (PostgreSQL version)."""
    ddl_statements = [
        # Books
        """
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            nomi TEXT NOT NULL
        );
        """,
        # Parts (audio chapters)
        """
        CREATE TABLE IF NOT EXISTS parts (
            id SERIAL PRIMARY KEY,
            book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
            nomi TEXT NOT NULL,
            audio_url TEXT NOT NULL
        );
        """,
        # Genres and M2M link
        """
        CREATE TABLE IF NOT EXISTS genres (
            id SERIAL PRIMARY KEY,
            nomi TEXT UNIQUE NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS book_genres (
            book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
            genre_id INTEGER NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
            PRIMARY KEY (book_id, genre_id)
        );
        """,
        # Users & Admins
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            name TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS admins (
            id BIGINT PRIMARY KEY,
            name TEXT
        );
        """,
        # Feedback
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id BIGINT,               -- user_id
            name TEXT,
            username TEXT,
            text TEXT,
            created_at TIMESTAMPTZ   -- ISO time
        );
        """,
        # Book views
        """
        CREATE TABLE IF NOT EXISTS book_views (
            book_name TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        );
        """,
        # Helpful index for feedback dedupe
        """
        CREATE INDEX IF NOT EXISTS idx_feedback_user_text ON feedback (id, text);
        """,
    ]
    with get_conn() as conn:
        with conn.cursor() as cur:
            for stmt in ddl_statements:
                cur.execute(stmt)

# =====================
# 📚 Books
# =====================

def get_next_book_id() -> str:
    """Return next numeric string id based on max(id::int)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT MAX(CASE WHEN id ~ '^\\d+$' THEN id::int ELSE NULL END) AS m FROM books;")
        row = cur.fetchone()
        mx = row["m"] if row and row["m"] is not None else 0
        return str(int(mx) + 1)

def add_book(book_id: str, nomi: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO books (id, nomi) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
            (book_id, nomi)
        )

def get_book(book_id: str) -> Optional[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM books WHERE id = %s;", (book_id,))
        row = cur.fetchone()
        return dict(row) if row else None

def get_book_by_title(title: str) -> Optional[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM books WHERE nomi = %s;", (title,))
        row = cur.fetchone()
        return dict(row) if row else None

def get_books() -> List[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM books ORDER BY (CASE WHEN id ~ '^\\d+$' THEN id::int ELSE NULL END), id;")
        return list(cur.fetchall())

def delete_book(book_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM books WHERE id = %s;", (book_id,))

def update_book_title(book_id: str, new_title: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE books SET nomi = %s WHERE id = %s;", (new_title, book_id))

# =====================
# 🎧 Parts
# =====================

def add_part(book_id: str, nomi: str, audio_url: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO parts (book_id, nomi, audio_url) VALUES (%s, %s, %s);",
            (book_id, nomi, audio_url)
        )

def get_parts(book_id: str) -> List[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM parts WHERE book_id = %s ORDER BY id;", (book_id,))
        return list(cur.fetchall())

def delete_part_by_index(book_id: str, index: int):
    """Delete the N-th part (0-based) within a book by order of id."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM parts WHERE book_id = %s ORDER BY id LIMIT 1 OFFSET %s;",
            (book_id, index)
        )
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM parts WHERE id = %s;", (row["id"],))

# =====================
# 🏷 Genres
# =====================

def add_genre(nomi: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO genres (nomi) VALUES (%s) ON CONFLICT (nomi) DO NOTHING;",
            (nomi,)
        )

def get_genres() -> List[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM genres ORDER BY nomi;")
        return list(cur.fetchall())

def delete_genre(genre_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM genres WHERE id = %s;", (genre_id,))

def link_book_genre(book_id: str, genre_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (book_id, genre_id)
        )

def clear_book_genres(book_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM book_genres WHERE book_id = %s;", (book_id,))

def get_genres_for_book(book_id: str) -> List[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT g.* FROM genres g
            JOIN book_genres bg ON bg.genre_id = g.id
            WHERE bg.book_id = %s
            ORDER BY g.nomi;
            """,
            (book_id,)
        )
        return list(cur.fetchall())

def set_book_genres(book_id: str, genre_ids: List[int]):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM book_genres WHERE book_id = %s;", (book_id,))
        for gid in genre_ids:
            cur.execute(
                "INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                (book_id, gid)
            )

def get_books_by_genre(genre_id: int) -> List[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT b.* FROM books b
            JOIN book_genres bg ON bg.book_id = b.id
            WHERE bg.genre_id = %s
            ORDER BY (CASE WHEN b.id ~ '^\\d+$' THEN b.id::int ELSE NULL END), b.id;
            """,
            (genre_id,)
        )
        return list(cur.fetchall())

# =====================
# 👥 Users & Admins
# =====================

def add_user(user_id: int, name: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
            (user_id, name)
        )

def get_users() -> List[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM users ORDER BY id;")
        return list(cur.fetchall())

def add_admin(admin_id: int, name: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO admins (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
            (admin_id, name)
        )

def get_admins() -> List[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM admins ORDER BY id;")
        return list(cur.fetchall())

def delete_admin(admin_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM admins WHERE id = %s;", (admin_id,))

# =====================
# 💬 Feedback
# =====================

def add_feedback(user_id: int, name: str, username: Optional[str], text: str):
    text_norm = (text or "").strip()
    if not text_norm:
        return
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO feedback (id, name, username, text, created_at) VALUES (%s, %s, %s, %s, %s);",
            (user_id, name, username, text_norm, datetime.utcnow())
        )

def get_feedback(limit: int = 10) -> List[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT * FROM feedback
            ORDER BY created_at DESC NULLS LAST, id DESC
            LIMIT %s;
            """,
            (limit,)
        )
        return list(cur.fetchall())

def deduplicate_feedback() -> int:
    """Remove duplicate rows with same (id, text); keep the oldest (smallest ctid). Return removed count."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            WITH deleted AS (
                DELETE FROM feedback a
                USING feedback b
                WHERE a.id = b.id
                  AND a.text = b.text
                  AND a.ctid > b.ctid
                RETURNING 1
            )
            SELECT COUNT(*) AS removed FROM deleted;
            """
        )
        row = cur.fetchone()
        return int(row["removed"] if row and row["removed"] is not None else 0)

# =====================
# 👁 Book Views
# =====================

def increment_book_view(book_name: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO book_views (book_name, count) VALUES (%s, 1)
            ON CONFLICT (book_name) DO UPDATE SET count = book_views.count + 1;
            """,
            (book_name,)
        )

def get_book_views() -> List[Dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM book_views ORDER BY count DESC, book_name;")
        return list(cur.fetchall())










# import sqlite3
# from contextlib import contextmanager
# from pathlib import Path
# from datetime import datetime, timedelta
#
# DB_PATH = Path("data/app.db")
# DB_PATH.parent.mkdir(parents=True, exist_ok=True)
#
#
# @contextmanager
# def get_conn():
#     conn = sqlite3.connect(DB_PATH)
#     conn.execute("PRAGMA foreign_keys = ON;")
#     conn.execute("PRAGMA journal_mode = WAL;")
#     conn.row_factory = sqlite3.Row
#     try:
#         yield conn
#         conn.commit()
#     except Exception:
#         conn.rollback()
#         raise
#     finally:
#         conn.close()
#
#
# def init_db():
#     with get_conn() as conn:
#         conn.executescript("""
#         CREATE TABLE IF NOT EXISTS books (
#             id TEXT PRIMARY KEY,
#             nomi TEXT NOT NULL
#         );
#         CREATE TABLE IF NOT EXISTS parts (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
#             nomi TEXT NOT NULL,
#             audio_url TEXT NOT NULL
#         );
#         CREATE TABLE IF NOT EXISTS genres (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             nomi TEXT UNIQUE NOT NULL
#         );
#         CREATE TABLE IF NOT EXISTS book_genres (
#             book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
#             genre_id INTEGER NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
#             PRIMARY KEY (book_id, genre_id)
#         );
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY,
#             name TEXT
#         );
#         CREATE TABLE IF NOT EXISTS admins (
#             id INTEGER PRIMARY KEY,
#             name TEXT
#         );
#         CREATE TABLE IF NOT EXISTS feedback (
#             id INTEGER,              -- user_id
#             name TEXT,
#             username TEXT,
#             text TEXT,
#             created_at TEXT          -- isoformat
#         );
#         CREATE TABLE IF NOT EXISTS book_views (
#             book_name TEXT PRIMARY KEY,
#             count INTEGER NOT NULL DEFAULT 0
#         );
#
#         CREATE INDEX IF NOT EXISTS idx_parts_book_id ON parts(book_id);
#         CREATE INDEX IF NOT EXISTS idx_book_genres_genre ON book_genres(genre_id);
#         CREATE INDEX IF NOT EXISTS idx_feedback_user_text ON feedback(id, text);
#         """)
#
# # =====================
# # 📚 Books
# # =====================
#
# def get_next_book_id() -> str:
#     with get_conn() as conn:
#         row = conn.execute("SELECT MAX(CAST(id AS INTEGER)) AS m FROM books").fetchone()
#         mx = row["m"] if row and row["m"] is not None else 0
#         return str(int(mx) + 1)
#
# def add_book(book_id: str, nomi: str):
#     with get_conn() as conn:
#         conn.execute("INSERT INTO books (id, nomi) VALUES (?, ?)", (book_id, nomi))
#
# def get_book(book_id: str):
#     with get_conn() as conn:
#         row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
#         return dict(row) if row else None
#
# def get_book_by_title(title: str):
#     with get_conn() as conn:
#         row = conn.execute("SELECT * FROM books WHERE nomi = ?", (title,)).fetchone()
#         return dict(row) if row else None
#
# def get_books():
#     with get_conn() as conn:
#         return [dict(r) for r in conn.execute("SELECT * FROM books ORDER BY CAST(id AS INTEGER)").fetchall()]
#
# def delete_book(book_id: str):
#     with get_conn() as conn:
#         conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
#
# def update_book_title(book_id: str, new_title: str):
#     with get_conn() as conn:
#         conn.execute("UPDATE books SET nomi = ? WHERE id = ?", (new_title, book_id))
#
# # =====================
# # 🎧 Parts
# # =====================
#
# def add_part(book_id: str, nomi: str, audio_url: str):
#     with get_conn() as conn:
#         conn.execute("INSERT INTO parts (book_id, nomi, audio_url) VALUES (?, ?, ?)", (book_id, nomi, audio_url))
#
# def get_parts(book_id: str):
#     with get_conn() as conn:
#         return [dict(r) for r in conn.execute(
#             "SELECT * FROM parts WHERE book_id = ? ORDER BY id", (book_id,)
#         ).fetchall()]
#
# def delete_part_by_index(book_id: str, index: int):
#     with get_conn() as conn:
#         row = conn.execute("SELECT id FROM parts WHERE book_id = ? ORDER BY id LIMIT 1 OFFSET ?",
#                            (book_id, index)).fetchone()
#         if row:
#             conn.execute("DELETE FROM parts WHERE id = ?", (row["id"],))
#
# # =====================
# # 🏷 Genres
# # =====================
#
# def add_genre(nomi: str):
#     with get_conn() as conn:
#         conn.execute("INSERT OR IGNORE INTO genres (nomi) VALUES (?)", (nomi,))
#
# def get_genres():
#     with get_conn() as conn:
#         return [dict(r) for r in conn.execute("SELECT * FROM genres ORDER BY nomi").fetchall()]
#
# def delete_genre(genre_id: int):
#     with get_conn() as conn:
#         conn.execute("DELETE FROM genres WHERE id = ?", (genre_id,))
#
# def link_book_genre(book_id: str, genre_id: int):
#     with get_conn() as conn:
#         conn.execute("INSERT OR IGNORE INTO book_genres (book_id, genre_id) VALUES (?, ?)", (book_id, genre_id))
#
# def clear_book_genres(book_id: str):
#     with get_conn() as conn:
#         conn.execute("DELETE FROM book_genres WHERE book_id = ?", (book_id,))
#
# def get_genres_for_book(book_id: str):
#     with get_conn() as conn:
#         return [dict(r) for r in conn.execute("""
#             SELECT g.* FROM genres g
#             JOIN book_genres bg ON g.id = bg.genre_id
#             WHERE bg.book_id = ?
#             ORDER BY g.nomi
#         """, (book_id,)).fetchall()]
#
# def set_book_genres(book_id: str, genre_ids: list[int]):
#     with get_conn() as conn:
#         conn.execute("DELETE FROM book_genres WHERE book_id = ?", (book_id,))
#         conn.executemany("INSERT OR IGNORE INTO book_genres (book_id, genre_id) VALUES (?, ?)",
#                          [(book_id, gid) for gid in genre_ids])
#
# def get_books_by_genre(genre_id: int):
#     with get_conn() as conn:
#         return [dict(r) for r in conn.execute("""
#             SELECT b.* FROM books b
#             JOIN book_genres bg ON b.id = bg.book_id
#             WHERE bg.genre_id = ?
#             ORDER BY CAST(b.id AS INTEGER)
#         """, (genre_id,)).fetchall()]
#
# # =====================
# # 👥 User/Admin
# # =====================
#
# def add_user(user_id: int, name: str):
#     with get_conn() as conn:
#         conn.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (user_id, name))
#
# def get_users():
#     with get_conn() as conn:
#         return [dict(r) for r in conn.execute("SELECT * FROM users").fetchall()]
#
# def add_admin(admin_id: int, name: str):
#     with get_conn() as conn:
#         conn.execute("INSERT OR IGNORE INTO admins (id, name) VALUES (?, ?)", (admin_id, name))
#
# def get_admins():
#     with get_conn() as conn:
#         return [dict(r) for r in conn.execute("SELECT * FROM admins").fetchall()]
#
# def delete_admin(admin_id: int):
#     with get_conn() as conn:
#         conn.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
#
# # =====================
# # 💬 Feedback
# # =====================
#
# def add_feedback(user_id: int, name: str, username: str, text: str):
#     """
#     Bir xil matnni (id+text) 24 soat ichida qayta saqlamaydi.
#     """
#     text_norm = (text or "").strip()
#     if not text_norm:
#         return
#     with get_conn() as conn:
#         # oxirgi 24 soat ichida shu foydalanuvchi aynan shu matndan yuborganmi?
#         row = conn.execute("""
#             SELECT 1
#             FROM feedback
#             WHERE id = ? AND TRIM(text) = TRIM(?)
#               AND datetime(created_at) >= datetime('now', '-1 day')
#             LIMIT 1
#         """, (user_id, text_norm)).fetchone()
#         if row:
#             return  # duplicate in 24h -> saqlamaymiz
#
#         conn.execute(
#             "INSERT INTO feedback (id, name, username, text, created_at) VALUES (?, ?, ?, ?, ?)",
#             (user_id, name, username, text_norm, datetime.now().isoformat())
#         )
#
# def get_feedback(limit: int = 10):
#     with get_conn() as conn:
#         return [dict(r) for r in conn.execute(
#             "SELECT * FROM feedback ORDER BY datetime(created_at) DESC, rowid DESC LIMIT ?", (limit,)
#         ).fetchall()]
#
# def deduplicate_feedback() -> int:
#     """
#     Takror (id + TRIM(text)) fikrlarni o'chiradi, eng oxirgisini qoldiradi.
#     Qaytaradi: o'chirilgan satrlar soni.
#     """
#     with get_conn() as conn:
#         # SQLite 3.25+ da window functions bor
#         conn.execute("""
#             WITH ranked AS (
#                 SELECT rowid, id, TRIM(text) AS ttext, created_at,
#                        ROW_NUMBER() OVER (PARTITION BY id, TRIM(text)
#                                           ORDER BY datetime(created_at) DESC, rowid DESC) AS rn
#                 FROM feedback
#             )
#             DELETE FROM feedback
#             WHERE rowid IN (SELECT rowid FROM ranked WHERE rn > 1);
#         """)
#         # nechta qator o'chganini aniqlash uchun changes() dan foydalanamiz
#         n = conn.execute("SELECT changes() AS n").fetchone()["n"]
#         return int(n)
#
# # =====================
# # 📊 Book views
# # =====================
#
# def increment_book_view(book_name: str):
#     with get_conn() as conn:
#         conn.execute("""
#             INSERT INTO book_views (book_name, count) VALUES (?, 1)
#             ON CONFLICT(book_name) DO UPDATE SET count = count + 1
#         """, (book_name,))
#
# def get_book_views():
#     with get_conn() as conn:
#         return [dict(r) for r in conn.execute(
#             "SELECT * FROM book_views ORDER BY count DESC"
#         ).fetchall()]
