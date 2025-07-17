from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


async def back_to_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📚 Kitoblar", callback_data='books')],
        [InlineKeyboardButton("📊 Statistika", callback_data='stats')],
        [InlineKeyboardButton("💬 Fikr bildirish", callback_data='feedback')],
        [InlineKeyboardButton("👤 Admin bilan bog‘lanish", callback_data='admin_contact')],
    ]

    await query.edit_message_text(
        text="🏠 Asosiy menyuga xush kelibsiz!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
