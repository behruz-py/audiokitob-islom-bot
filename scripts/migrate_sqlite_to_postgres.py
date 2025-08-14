"""
One-time migration: copy data from local SQLite (data/app.db) to PostgreSQL (DATABASE_URL).
Usage:
  1) Ensure storage.py (Postgres version) is in place and `pip install -r requirements.txt` is done.
  2) Set env var: DATABASE_URL="postgresql://user:pass@host:port/db"
  3) Run: python scripts/migrate_sqlite_to_postgres.py
"""

import os
import sqlite3
import psycopg
from psycopg.rows import dict_row

SQLITE_PATH = "data/app.db"
PG_DSN = os.getenv("DATABASE_URL")

def main():
    if not PG_DSN:
        raise SystemExit("DATABASE_URL env var is required.")
    if not os.path.exists(SQLITE_PATH):
        raise SystemExit(f"SQLite file not found: {SQLITE_PATH}")

    # Open sources
    sconn = sqlite3.connect(SQLITE_PATH)
    sconn.row_factory = sqlite3.Row
    pconn = psycopg.connect(PG_DSN, autocommit=True)
    pconn.row_factory = dict_row

    # Create schema on PG (calls storage.init_db)
    try:
        from storage import init_db
        init_db()
    except Exception as e:
        print("Warning: init_db failed or not found:", e)

    try:
        with pconn, pconn.cursor() as pc, sconn, sconn.cursor() as sc:
            # books
            for r in sc.execute("SELECT id, nomi FROM books"):
                pc.execute("INSERT INTO books (id, nomi) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (r["id"], r["nomi"]))

            # parts
            for r in sc.execute("SELECT id, book_id, nomi, audio_url FROM parts ORDER BY id"):
                pc.execute(
                    "INSERT INTO parts (id, book_id, nomi, audio_url) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING;",
                    (r["id"], r["book_id"], r["nomi"], r["audio_url"])
                )

            # genres
            for r in sc.execute("SELECT id, nomi FROM genres"):
                pc.execute("INSERT INTO genres (id, nomi) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (r["id"], r["nomi"]))

            # book_genres
            for r in sc.execute("SELECT book_id, genre_id FROM book_genres"):
                pc.execute(
                    "INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                    (r["book_id"], r["genre_id"])
                )

            # users
            for r in sc.execute("SELECT id, name FROM users"):
                pc.execute("INSERT INTO users (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (r["id"], r["name"]))

            # admins
            for r in sc.execute("SELECT id, name FROM admins"):
                pc.execute("INSERT INTO admins (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (r["id"], r["name"]))

            # feedback
            # created_at in SQLite stored as TEXT; try to parse on PG side
            for r in sc.execute("SELECT id, name, username, text, created_at FROM feedback"):
                pc.execute(
                    "INSERT INTO feedback (id, name, username, text, created_at) VALUES (%s, %s, %s, %s, %s::timestamptz);",
                    (r["id"], r["name"], r["username"], r["text"], r["created_at"])
                )

            # book_views
            for r in sc.execute("SELECT book_name, count FROM book_views"):
                pc.execute(
                    "INSERT INTO book_views (book_name, count) VALUES (%s, %s) ON CONFLICT (book_name) DO UPDATE SET count = EXCLUDED.count;",
                    (r["book_name"], r["count"])
                )
        print("✅ Migration finished.")
    finally:
        sconn.close()
        pconn.close()

if __name__ == "__main__":
    main()
