import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

FEEDBACK_FILE = "data/feedback.json"


async def show_last_feedbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Fayldan feedbacklar ro'yxatini yuklash
    feedbacks = []
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            feedbacks = json.load(f)

    # Fikrlar mavjud bo'lmasa
    if not feedbacks:
        text = "ℹ️ Hozircha hech qanday fikr bildirilmagan."
    else:
        text = "💬 So‘nggi 10 ta foydalanuvchi fikri:\n\n"
        for fb in reversed(feedbacks[-10:]):
            name = fb.get("name", "Nomaʼlum")
            username = fb.get("username", "Nomaʼlum")
            message = fb.get("text", "")

            username_str = f"@{username}" if username != "Nomaʼlum" and username else "username: yo‘q"
            text += f"<b>{name}</b> ({username_str}):\n{message}\n\n"

    # Tugmalar
    keyboard = [
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]
    ]

    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
