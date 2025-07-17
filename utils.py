import json
import os
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

ADMINS_FILE = "data/admins.json"
BOOK_FILE = "data/books.json"


def load_admins():
    if not os.path.exists(ADMINS_FILE):
        return {}
    with open(ADMINS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_admins(admins):
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(admins, f, indent=4, ensure_ascii=False)


def is_admin(user_id: int) -> bool:
    admins = load_admins()
    return str(user_id) in admins


BACK_HOME_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔙 Ortga", callback_data="admin_manage_admins"),
        InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")
    ]
])


# utils.py


def load_books():
    if os.path.exists(BOOK_FILE):
        with open(BOOK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"kitoblar": []}


def save_books(data):
    with open(BOOK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
