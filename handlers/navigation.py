from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from utils import is_admin  # <<< qo'shildi


async def back_to_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("📚 Kitoblar", callback_data='books')],
        [InlineKeyboardButton("🏷 Janrlar", callback_data='genres')],
        [InlineKeyboardButton("📊 Statistika", callback_data='stats')],
        [InlineKeyboardButton("💬 Fikr bildirish", callback_data='feedback')],
        [InlineKeyboardButton("👤 Admin bilan bog‘lanish", callback_data='admin_contact')],
    ]
    # <<< MUHIM: home menyuda ham admin panel tugmasini shartli ko'rsatamiz
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("🛠️ Admin panel", callback_data="admin_panel")])

    await query.edit_message_text(
        text="🏠 Asosiy menyuga xush kelibsiz!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
