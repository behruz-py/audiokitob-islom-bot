import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

BOOKS_FILE = "data/books.json"
USERS_FILE = "data/users.json"
BOOK_STATS_FILE = "data/book_views.json"


# Statistik menyu
async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("👥 Foydalanuvchilar soni", callback_data="stat_users")],
        [InlineKeyboardButton("📖 Kitoblar statistikasi", callback_data="stat_books")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]
    ]

    await query.edit_message_text(
        text="📊 Statistika menyusi:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# 1. Foydalanuvchilar sonini ko‘rsatish
async def show_user_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        count = len(users)
    except:
        count = 0

    keyboard = [
        [
            InlineKeyboardButton("🔙 Ortga", callback_data="stats"),
            InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")
        ]
    ]

    await query.edit_message_text(
        text=f"👥 Botdan foydalanuvchilar soni: <b>{count}</b> ta",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# 2. Kitoblar statistikasi (faqat mavjud kitoblar bo‘yicha)
async def show_book_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # 1. Mavjud kitob nomlarini to‘plab olamiz
    try:
        with open(BOOKS_FILE, 'r', encoding='utf-8') as f:
            books_data = json.load(f)
        if isinstance(books_data, dict) and "kitoblar" in books_data:
            books = books_data["kitoblar"]
        else:
            books = books_data
        available_titles = {book["nomi"] for book in books}
    except:
        available_titles = set()

    # 2. Statistikani o‘qiymiz
    try:
        with open(BOOK_STATS_FILE, 'r', encoding='utf-8') as f:
            stats = json.load(f)
    except:
        stats = {}

    # 3. Faqat mavjud kitoblar bo‘yicha filtrlash
    filtered_stats = {title: count for title, count in stats.items() if title in available_titles}

    if not filtered_stats:
        text = "📚 Hali hech qanday kitob statistikasi mavjud emas yoki mavjud kitoblarga tegishli emas."
    else:
        sorted_stats = sorted(filtered_stats.items(), key=lambda x: x[1], reverse=True)
        text = "📖 Kitoblar bo‘yicha statistika:\n\n"
        for book_name, count in sorted_stats:
            text += f"• <b>{book_name}</b>: {count} marta ochilgan\n"

    keyboard = [
        [
            InlineKeyboardButton("🔙 Ortga", callback_data="stats"),
            InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")
        ]
    ]

    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
