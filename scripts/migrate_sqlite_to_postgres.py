"""
One-time migration: copy data from local SQLite (data/app.db) to PostgreSQL (DATABASE_URL).

How to run (Windows PowerShell):
  1) pip install -r requirements.txt
  2) $env:DATABASE_URL = 'postgresql://USER:PASSWORD@HOST:PORT/DB?sslmode=require'
  3) python scripts/migrate_sqlite_to_postgres.py
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# --- Ensure project root is importable so we can import storage.init_db() ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SQLITE_PATH = ROOT / "data" / "app.db"
PG_DSN = os.getenv("DATABASE_URL")


def ensure_schema_with_storage():
    """Try to create schema via storage.init_db() if storage is available."""
    try:
        from storage import init_db  # type: ignore
        init_db()
        print("Schema created via storage.init_db().")
        return True
    except Exception as e:
        print("Warning: storage.init_db() unavailable, falling back to local DDL. Reason:", e)
        return False


def ensure_schema_with_fallback(conn: psycopg.Connection):
    """Create tables and indexes directly (fallback if storage not importable)."""
    ddl = [
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
            created_at TIMESTAMPTZ
        );
        """,
        # Book views
        """
        CREATE TABLE IF NOT EXISTS book_views (
            book_name TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        );
        """,
        # Helpful index
        "CREATE INDEX IF NOT EXISTS idx_feedback_user_text ON feedback (id, text);",
    ]
    with conn.cursor() as cur:
        for stmt in ddl:
            cur.execute(stmt)
    print("Schema created via fallback DDL.")


def try_parse_dt(value):
    """Try to parse various datetime string formats; return datetime or None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    txt = str(value).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(txt, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(txt)
    except Exception:
        return None


def _bump_seq(conn: psycopg.Connection, table: str, col: str = "id"):
    """
    Robust sequence bump:
    - If table has rows: setval(seq, MAX(id), true)  -> nextval = MAX+1
    - If empty:         setval(seq, 1, false)       -> nextval = 1
    """
    with conn.cursor() as cur:
        cur.execute(f"SELECT MAX({col}) AS max_id FROM {table};")
        row = cur.fetchone()
        max_id = row["max_id"] if isinstance(row, dict) else row[0]

        cur.execute("SELECT pg_get_serial_sequence(%s, %s) AS seq_name;", (table, col))
        row = cur.fetchone()
        seq = row["seq_name"] if isinstance(row, dict) else row[0]
        if not seq:
            return  # no serial/bigserial sequence

        if max_id is None or int(max_id) < 1:
            # empty table -> start from 1 (uncalled)
            cur.execute("SELECT setval(%s, %s, %s);", (seq, 1, False))
        else:
            cur.execute("SELECT setval(%s, %s, %s);", (seq, int(max_id), True))


def fix_sequences(conn: psycopg.Connection):
    """Fix sequences for tables with SERIAL ids after explicit inserts."""
    _bump_seq(conn, "parts", "id")
    _bump_seq(conn, "genres", "id")
    print("Sequences fixed (parts.id, genres.id).")


def main():
    if not PG_DSN:
        raise SystemExit("DATABASE_URL env var is required.")

    if not SQLITE_PATH.exists():
        raise SystemExit(f"SQLite file not found: {SQLITE_PATH}")

    # Open SQLite (row factory to dict-like)
    sconn = sqlite3.connect(str(SQLITE_PATH))
    sconn.row_factory = sqlite3.Row

    # Open Postgres
    pconn = psycopg.connect(PG_DSN, autocommit=True)
    pconn.row_factory = dict_row

    try:
        # Ensure schema
        if not ensure_schema_with_storage():
            ensure_schema_with_fallback(pconn)

        sc = sconn.cursor()
        pc = pconn.cursor()

        # --- books ---
        for r in sc.execute("SELECT id, nomi FROM books"):
            pc.execute(
                "INSERT INTO books (id, nomi) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                (r["id"], r["nomi"])
            )
        print("✔ books migrated.")

        # --- parts ---
        for r in sc.execute("SELECT id, book_id, nomi, audio_url FROM parts ORDER BY id"):
            pc.execute(
                "INSERT INTO parts (id, book_id, nomi, audio_url) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING;",
                (r["id"], r["book_id"], r["nomi"], r["audio_url"])
            )
        print("✔ parts migrated.")

        # --- genres ---
        for r in sc.execute("SELECT id, nomi FROM genres"):
            pc.execute(
                "INSERT INTO genres (id, nomi) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                (r["id"], r["nomi"])
            )
        print("✔ genres migrated.")

        # --- book_genres ---
        for r in sc.execute("SELECT book_id, genre_id FROM book_genres"):
            pc.execute(
                "INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                (r["book_id"], r["genre_id"])
            )
        print("✔ book_genres migrated.")

        # --- users ---
        for r in sc.execute("SELECT id, name FROM users"):
            pc.execute(
                "INSERT INTO users (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                (r["id"], r["name"])
            )
        print("✔ users migrated.")

        # --- admins ---
        for r in sc.execute("SELECT id, name FROM admins"):
            pc.execute(
                "INSERT INTO admins (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                (r["id"], r["name"])
            )
        print("✔ admins migrated.")

        # --- feedback ---
        for r in sc.execute("SELECT id, name, username, text, created_at FROM feedback"):
            dt = try_parse_dt(r["created_at"])
            if dt is None:
                dt = datetime.utcnow()
            pc.execute(
                "INSERT INTO feedback (id, name, username, text, created_at) VALUES (%s, %s, %s, %s, %s);",
                (r["id"], r["name"], r["username"], r["text"], dt)
            )
        print("✔ feedback migrated.")

        # --- book_views ---
        for r in sc.execute("SELECT book_name, count FROM book_views"):
            pc.execute(
                "INSERT INTO book_views (book_name, count) VALUES (%s, %s) "
                "ON CONFLICT (book_name) DO UPDATE SET count = EXCLUDED.count;",
                (r["book_name"], r["count"])
            )
        print("✔ book_views migrated.")

        fix_sequences(pconn)

        sc.close()
        pc.close()

        print("✅ Migration finished successfully.")
    finally:
        sconn.close()
        pconn.close()


if __name__ == "__main__":
    main()
