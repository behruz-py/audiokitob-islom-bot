# storage.py  — PostgreSQL versiya (psycopg3 + pool)
# ENV:
#   DATABASE_URL = postgresql://USER:PASSWORD@HOST:PORT/DBNAME   (Railway -> Connect bo‘limidan oling)
#
# Izoh:
# - API SQLite dagidek qoldirildi (add_book, get_books, get_parts, ...).
# - dict_row orqali satrlar dict ko‘rinishida qaytadi.
# - ON CONFLICT ... DO NOTHING/UPDATE lar ishlatilgan.

import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env topilmadi. Railway Postgresdan URL qo‘ying.")

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    kwargs={"row_factory": dict_row},
    min_size=1,
    max_size=5,
    open=False,
)
pool.open()

@contextmanager
def get_conn():
    with pool.connection() as conn:
        with conn.cursor() as cur:
            yield conn, cur

def init_db():
    with get_conn() as (conn, cur):
        cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            nomi TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS parts (
            id SERIAL PRIMARY KEY,
            book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
            nomi TEXT NOT NULL,
            audio_url TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS genres (
            id SERIAL PRIMARY KEY,
            nomi TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS book_genres (
            book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
            genre_id INT NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
            PRIMARY KEY (book_id, genre_id)
        );
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            name TEXT
        );
        CREATE TABLE IF NOT EXISTS admins (
            id BIGINT PRIMARY KEY,
            name TEXT
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id BIGINT,          -- user_id
            name TEXT,
            username TEXT,
            text TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS book_views (
            book_name TEXT PRIMARY KEY,
            count INT NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_parts_book_id ON parts(book_id);
        CREATE INDEX IF NOT EXISTS idx_book_genres_genre ON book_genres(genre_id);
        CREATE INDEX IF NOT EXISTS idx_feedback_user_text ON feedback(id, text);
        """)
        conn.commit()

# =============== Books ===============

def get_next_book_id() -> str:
    with get_conn() as (conn, cur):
        cur.execute("SELECT COALESCE(MAX(id::int), 0) AS m FROM books;")
        mx = cur.fetchone()["m"]
        return str(int(mx) + 1)

def add_book(book_id: str, nomi: str):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO books (id, nomi) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (book_id, nomi))
        conn.commit()

def get_book(book_id: str):
    with get_conn() as (conn, cur):
        cur.execute("SELECT * FROM books WHERE id = %s;", (book_id,))
        return cur.fetchone()

def get_book_by_title(title: str):
    with get_conn() as (conn, cur):
        cur.execute("SELECT * FROM books WHERE nomi = %s;", (title,))
        return cur.fetchone()

def get_books():
    with get_conn() as (conn, cur):
        cur.execute("SELECT * FROM books ORDER BY id::int;")
        return cur.fetchall()

def delete_book(book_id: str):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM books WHERE id = %s;", (book_id,))
        conn.commit()

def update_book_title(book_id: str, new_title: str):
    with get_conn() as (conn, cur):
        cur.execute("UPDATE books SET nomi = %s WHERE id = %s;", (new_title, book_id))
        conn.commit()

# =============== Parts ===============

def add_part(book_id: str, nomi: str, audio_url: str):
    with get_conn() as (conn, cur):
        cur.execute(
            "INSERT INTO parts (book_id, nomi, audio_url) VALUES (%s, %s, %s);",
            (book_id, nomi, audio_url)
        )
        conn.commit()

def get_parts(book_id: str):
    with get_conn() as (conn, cur):
        cur.execute("SELECT * FROM parts WHERE book_id = %s ORDER BY id;", (book_id,))
        return cur.fetchall()

def delete_part_by_index(book_id: str, index: int):
    with get_conn() as (conn, cur):
        # OFFSET bo‘yicha tanlab, keyin o‘chiramiz
        cur.execute(
            "SELECT id FROM parts WHERE book_id = %s ORDER BY id LIMIT 1 OFFSET %s;",
            (book_id, index)
        )
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM parts WHERE id = %s;", (row["id"],))
            conn.commit()

# =============== Genres ===============

def add_genre(nomi: str):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO genres (nomi) VALUES (%s) ON CONFLICT (nomi) DO NOTHING;", (nomi,))
        conn.commit()

def get_genres():
    with get_conn() as (conn, cur):
        cur.execute("SELECT * FROM genres ORDER BY nomi;")
        return cur.fetchall()

def delete_genre(genre_id: int):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM genres WHERE id = %s;", (genre_id,))
        conn.commit()

def link_book_genre(book_id: str, genre_id: int):
    with get_conn() as (conn, cur):
        cur.execute("""
            INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s)
            ON CONFLICT (book_id, genre_id) DO NOTHING;
        """, (book_id, genre_id))
        conn.commit()

def clear_book_genres(book_id: str):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM book_genres WHERE book_id = %s;", (book_id,))
        conn.commit()

def get_genres_for_book(book_id: str):
    with get_conn() as (conn, cur):
        cur.execute("""
            SELECT g.* FROM genres g
            JOIN book_genres bg ON g.id = bg.genre_id
            WHERE bg.book_id = %s
            ORDER BY g.nomi;
        """, (book_id,))
        return cur.fetchall()

def set_book_genres(book_id: str, genre_ids: list[int]):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM book_genres WHERE book_id = %s;", (book_id,))
        if genre_ids:
            cur.executemany(
                "INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                [(book_id, gid) for gid in genre_ids]
            )
        conn.commit()

def get_books_by_genre(genre_id: int):
    with get_conn() as (conn, cur):
        cur.execute("""
            SELECT b.* FROM books b
            JOIN book_genres bg ON b.id = bg.book_id
            WHERE bg.genre_id = %s
            ORDER BY b.id::int;
        """, (genre_id,))
        return cur.fetchall()

# =============== Users/Admins ===============

def add_user(user_id: int, name: str):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO users (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (user_id, name))
        conn.commit()

def get_users():
    with get_conn() as (conn, cur):
        cur.execute("SELECT * FROM users;")
        return cur.fetchall()

def add_admin(admin_id: int, name: str):
    with get_conn() as (conn, cur):
        cur.execute("INSERT INTO admins (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (admin_id, name))
        conn.commit()

def get_admins():
    with get_conn() as (conn, cur):
        cur.execute("SELECT * FROM admins;")
        return cur.fetchall()

def delete_admin(admin_id: int):
    with get_conn() as (conn, cur):
        cur.execute("DELETE FROM admins WHERE id = %s;", (admin_id,))
        conn.commit()

# =============== Feedback ===============

def add_feedback(user_id: int, name: str, username: str, text: str):
    text_norm = (text or "").strip()
    if not text_norm:
        return
    with get_conn() as (conn, cur):
        # oxirgi 24 soat ichida xuddi shu user xuddi shu matndan yuborganmi?
        cur.execute("""
            SELECT 1 FROM feedback
            WHERE id = %s AND TRIM(text) = TRIM(%s)
              AND created_at >= NOW() - INTERVAL '1 day'
            LIMIT 1;
        """, (user_id, text_norm))
        if cur.fetchone():
            return
        cur.execute(
            "INSERT INTO feedback (id, name, username, text) VALUES (%s, %s, %s, %s);",
            (user_id, name, username, text_norm)
        )
        conn.commit()

def get_feedback(limit: int = 10):
    with get_conn() as (conn, cur):
        cur.execute("""
            SELECT * FROM feedback
            ORDER BY created_at DESC, ctid DESC
            LIMIT %s;
        """, (limit,))
        return cur.fetchall()

def deduplicate_feedback() -> int:
    with get_conn() as (conn, cur):
        cur.execute("""
            WITH ranked AS (
                SELECT ctid, id, TRIM(text) AS ttext, created_at,
                       ROW_NUMBER() OVER (PARTITION BY id, TRIM(text)
                                          ORDER BY created_at DESC, ctid DESC) AS rn
                FROM feedback
            )
            DELETE FROM feedback
            WHERE ctid IN (SELECT ctid FROM ranked WHERE rn > 1);
        """)
        # affected rows:
        cur.execute("SELECT 1;")
        conn.commit()
        # ps: psycopg3 da rowcount so‘nggi statement bo‘yicha bo‘ladi, bu yerda aniq son talab bo‘lmasa ham,
        # admin xabari uchun qaytarmasak ham bo‘ladi. Istasangiz RETURNING bilan qaytarish mumkin.
        return 0

# =============== Book views ===============

def increment_book_view(book_name: str):
    with get_conn() as (conn, cur):
        cur.execute("""
            INSERT INTO book_views (book_name, count) VALUES (%s, 1)
            ON CONFLICT (book_name) DO UPDATE SET count = book_views.count + 1;
        """, (book_name,))
        conn.commit()

def get_book_views():
    with get_conn() as (conn, cur):
        cur.execute("SELECT * FROM book_views ORDER BY count DESC;")
        return cur.fetchall()
