from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import is_admin


# ✅ Admin panelga kirish
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    query = getattr(update, "callback_query", None)
    if query:
        await query.answer()

    if not is_admin(user_id):
        text = "⛔ Sizda bu bo‘limga kirish huquqi yo‘q."
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    keyboard = [
        [InlineKeyboardButton("📥 Yangi kitob qo‘shish", callback_data="admin_add_book")],
        [InlineKeyboardButton("➕ Yangi qism qo‘shish", callback_data="admin_add_part")],
        [InlineKeyboardButton("🗑️ Kitobni o‘chirish", callback_data="admin_delete_book")],
        [InlineKeyboardButton("➖Qismni o‘chirish", callback_data="admin_delete_part")],
        [InlineKeyboardButton("🏷 Janrlarni boshqarish", callback_data="admin_manage_genres")],
        [InlineKeyboardButton("✒️ Kitobga janr belgilash", callback_data="admin_assign_genres")],
        [InlineKeyboardButton("✏️ Kitob nomini tahrirlash", callback_data="admin_rename_book")],
        [InlineKeyboardButton("📚 Kitoblar ro‘yxati", callback_data="admin_list_books")],
        [InlineKeyboardButton("📬 Xabar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💬 Oxirgi 10 ta fikr", callback_data="admin_view_feedback")],
        [InlineKeyboardButton("👤 Adminlarni boshqarish", callback_data="admin_manage_admins")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")],
    ]

    text = "🛠️ <b>Admin panel</b>\n\nQuyidagi bo‘limlardan birini tanlang:"
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
