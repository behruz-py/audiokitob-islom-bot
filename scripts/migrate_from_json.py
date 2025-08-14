from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # project root ni import yo'liga qo'shish

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Loyiha ildizidan ishga tushiriladi deb faraz qilamiz
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
DB_FILE = DATA_DIR / "app.db"

# storage dagi CRUD funksiyalar

from storage import (
    init_db,
    add_book,
    get_books,
    add_part,
    get_parts,
    add_user,
    add_admin,
    add_feedback,
    increment_book_view,
)


# ---------- Yordamchi funksiyalar ----------

def ts() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def safe_read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def backup_file(path: Path) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if path.exists():
        dest = BACKUP_DIR / f"{path.name}.{ts()}.bak"
        shutil.copy2(path, dest)


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def index_books_by_id() -> Dict[str, dict]:
    """DB dagi books ni id->row ko'rinishida qaytaradi."""
    rows = get_books()
    return {row["id"]: row for row in rows}


def index_parts_by_book(book_id: str) -> Dict[Tuple[str, str], dict]:
    """(nomi, audio_url) bo'yicha indeks — dublikatni oldini olish uchun."""
    rows = get_parts(book_id)
    return {(row["nomi"], row["audio_url"]): row for row in rows}


# ---------- Migratsiya bosqichlari ----------

def migrate_books_and_parts() -> Tuple[int, int, int, int]:
    """
    data/books.json dan:
    {
      "kitoblar": [
        {
          "id": "1",
          "nomi": "Kitob nomi",
          "qismlar": [
            {"nomi": "1-qism", "audio_url": "https://t.me/kanal/123"},
            ...
          ]
        },
        ...
      ]
    }
    """
    books_json = safe_read_json(DATA_DIR / "books.json", default={})
    all_books = books_json.get("kitoblar", [])
    if not isinstance(all_books, list):
        all_books = []

    # Backup qilamiz (asliga tegmaydi)
    backup_file(DATA_DIR / "books.json")

    existed_books = index_books_by_id()

    added_books = 0
    skipped_books = 0
    added_parts = 0
    skipped_parts = 0

    for b in all_books:
        book_id = str(b.get("id") or "").strip()
        nomi = str(b.get("nomi") or "").strip()

        if not book_id or not nomi:
            # invalid yozuv — tashlab ketamiz
            skipped_books += 1
            continue

        if book_id in existed_books:
            skipped_books += 1
        else:
            try:
                add_book(book_id, nomi)
                added_books += 1
            except Exception:
                # ehtimol parallel ishga tushirishda poyga — tashlab ketamiz
                skipped_books += 1

        # Qismlar
        parts = b.get("qismlar", [])
        if isinstance(parts, list):
            # dublikatni oldini olish uchun mavjudlarni indekslaymiz
            existing_map = index_parts_by_book(book_id)
            for p in parts:
                p_nomi = str(p.get("nomi") or "").strip()
                p_url = str(p.get("audio_url") or "").strip()
                key = (p_nomi, p_url)
                if not p_nomi or not p_url:
                    skipped_parts += 1
                    continue
                if key in existing_map:
                    skipped_parts += 1
                    continue
                try:
                    add_part(book_id, p_nomi, p_url)
                    added_parts += 1
                except Exception:
                    skipped_parts += 1

    return added_books, skipped_books, added_parts, skipped_parts


def migrate_book_views() -> Tuple[int, int]:
    """
    data/book_views.json dan:
    {
      "Kitob nomi": 12,
      ...
    }
    """
    views_json = safe_read_json(DATA_DIR / "book_views.json", default={})
    if not isinstance(views_json, dict):
        views_json = {}

    backup_file(DATA_DIR / "book_views.json")

    added = 0
    skipped = 0
    for book_name, count in views_json.items():
        try:
            cnt = int(count)
        except Exception:
            skipped += 1
            continue
        if not book_name:
            skipped += 1
            continue
        try:
            # count marta increment qilamiz (kichik son bo'lsa ok; juda katta bo'lsa sekinlashishi mumkin)
            for _ in range(cnt):
                increment_book_view(book_name)
            added += 1
        except Exception:
            skipped += 1

    return added, skipped


def migrate_users() -> Tuple[int, int]:
    """
    data/users.json — ko‘rganlaridan kelib chiqib:
    {
      "8027031316": {"id": 8027031316, "name": "Behruz"},
      ...
    }
    yoki ba'zan shunchaki dict bo‘lishi mumkin.
    """
    users_json = safe_read_json(DATA_DIR / "users.json", default={})
    if not isinstance(users_json, dict):
        users_json = {}

    backup_file(DATA_DIR / "users.json")

    added = 0
    skipped = 0
    for key, val in users_json.items():
        try:
            if isinstance(val, dict):
                uid = int(val.get("id") or key)
                name = str(val.get("name") or "")[:255]
            else:
                uid = int(key)
                name = str(val)[:255]
            if uid <= 0:
                skipped += 1
                continue
            try:
                add_user(uid, name)
                added += 1
            except Exception:
                # PK bor — demak avvaldan mavjud
                skipped += 1
        except Exception:
            skipped += 1

    return added, skipped


def migrate_admins() -> Tuple[int, int]:
    """
    data/admins.json — admin_manage.py’dagi load_admins() formatiga mos:
    {
      "8027031316": {"id": 8027031316, "name": "Behruz"},
      ...
    }
    """
    admins_json = safe_read_json(DATA_DIR / "admins.json", default={})
    if not isinstance(admins_json, dict):
        admins_json = {}

    backup_file(DATA_DIR / "admins.json")

    added = 0
    skipped = 0
    for key, val in admins_json.items():
        try:
            if isinstance(val, dict):
                aid = int(val.get("id") or key)
                name = str(val.get("name") or "")[:255]
            else:
                aid = int(key)
                name = str(val)[:255]
            if aid <= 0:
                skipped += 1
                continue
            try:
                add_admin(aid, name)
                added += 1
            except Exception:
                skipped += 1
        except Exception:
            skipped += 1

    return added, skipped


def migrate_feedback() -> Tuple[int, int]:
    """
    data/feedback.json:
    [
      {"id": 123, "name": "...", "username": "...", "text": "..."},
      ...
    ]
    """
    feedback_json = safe_read_json(DATA_DIR / "feedback.json", default=[])
    if not isinstance(feedback_json, list):
        feedback_json = []

    backup_file(DATA_DIR / "feedback.json")

    added = 0
    skipped = 0
    for fb in feedback_json:
        try:
            uid = int(fb.get("id"))
            name = str(fb.get("name") or "")[:255]
            username = str(fb.get("username") or "")[:255]
            text = str(fb.get("text") or "")
            if not text:
                skipped += 1
                continue
            try:
                add_feedback(uid, name, username, text)
                added += 1
            except Exception:
                skipped += 1
        except Exception:
            skipped += 1

    return added, skipped


def main():
    print("➡️  Migratsiya boshlandi...")
    ensure_data_dir()

    # DB tayyorlab olamiz
    print("ℹ️  DB init (tables, pragmas)...")
    init_db()
    if not DB_FILE.exists():
        print("❌ DB fayli yaratilmagan ko‘rinadi (data/app.db yo‘q). storage.init_db() ni tekshiring.")
        return

    # Har bir blokni alohida migratsiya qilamiz
    b_add, b_skip, p_add, p_skip = migrate_books_and_parts()
    print(f"📚 Books: +{b_add}, skip {b_skip} | 🎧 Parts: +{p_add}, skip {p_skip}")

    v_add, v_skip = migrate_book_views()
    print(f"📊 Book views: +{v_add}, skip {v_skip}")

    u_add, u_skip = migrate_users()
    print(f"👥 Users: +{u_add}, skip {u_skip}")

    a_add, a_skip = migrate_admins()
    print(f"👮 Admins: +{a_add}, skip {a_skip}")

    f_add, f_skip = migrate_feedback()
    print(f"💬 Feedback: +{f_add}, skip {f_skip}")

    print("✅ Migratsiya yakunlandi.")


if __name__ == "__main__":
    main()
