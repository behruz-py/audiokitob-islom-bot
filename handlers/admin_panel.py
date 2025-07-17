from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMINS


# ✅ Admin panelga kirish
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()

    # 👮 Faqat adminlar uchun
    if user_id not in ADMINS:
        await query.edit_message_text("⛔ Sizda bu bo‘limga kirish huquqi yo‘q.")
        return

    # 🛠️ Admin menyusi
    keyboard = [
        [InlineKeyboardButton("📥 Yangi kitob qo‘shish", callback_data="admin_add_book")],
        [InlineKeyboardButton("➕ Yangi qism qo‘shish", callback_data="admin_add_part")],
        [InlineKeyboardButton("🗑️ Kitobni o‘chirish", callback_data="admin_delete_book")],
        [InlineKeyboardButton("🗑 Kitobni qismini o‘chirish", callback_data="admin_delete_part")],  # ✅ Yangi tugma
        [InlineKeyboardButton("📬 Xabar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📚 Kitoblar ro‘yxati", callback_data="admin_list_books")],
        [InlineKeyboardButton("💬 Oxirgi 10 ta fikr", callback_data="admin_view_feedback")],
        [InlineKeyboardButton("👤 Adminlarni boshqarish", callback_data="admin_manage_admins")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")],
    ]

    await query.edit_message_text(
        "🛠️ <b>Admin panel</b>\n\nQuyidagi bo‘limlardan birini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
