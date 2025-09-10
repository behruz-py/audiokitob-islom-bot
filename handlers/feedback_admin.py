from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from storage import get_feedback, deduplicate_feedback
from utils import safe_edit_message


async def show_last_feedbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    feedbacks = get_feedback(10)

    if not feedbacks:
        text = "ℹ️ Hozircha hech qanday fikr bildirilmagan."
    else:
        text = "💬 So‘nggi 10 ta foydalanuvchi fikri:\n\n"
        for fb in feedbacks:
            name = fb.get("name") or "Nomaʼlum"
            username = fb.get("username") or ""
            message = fb.get("text") or ""
            username_str = f"@{username}" if username else "username: yo‘q"
            text += f"<b>{name}</b> ({username_str}):\n{message}\n\n"

    keyboard = [
        [InlineKeyboardButton("♻️ Takrorlarni tozalash", callback_data="admin_dedupe_feedback")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]
    ]

    await safe_edit_message(
        query.message,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ♻️ Takrorlarni tozalash
async def dedupe_feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    removed = deduplicate_feedback()
    text = f"✅ Tayyor. Takror fikrlar tozalandi.\n\n🗑 O‘chirilganlar soni: <b>{removed}</b> ta"

    keyboard = [
        [InlineKeyboardButton("🔙 Ortga (fikrlar)", callback_data="admin_view_feedback")],
        [InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")],
    ]

    await safe_edit_message(
        query.message,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

