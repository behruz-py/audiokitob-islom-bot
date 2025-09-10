from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from utils import load_admins, save_admins, BACK_HOME_KB, safe_edit_message

ASK_NEW_ADMIN_ID = range(1)


# 👤 Adminlarni boshqarish menyusi
async def admin_manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ Admin qo‘shish", callback_data="admin_add_admin")],
        [InlineKeyboardButton("➖ Adminni o‘chirish", callback_data="admin_delete_admin")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")]
    ]
    await safe_edit_message(query.message, "👤 Adminlarni boshqarish menyusi:", InlineKeyboardMarkup(keyboard))


# ➕ Admin qo‘shish
async def ask_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_message(
        query.message,
        "🆔 Yangi adminning foydalanuvchi ID sini yuboring:",
        BACK_HOME_KB
    )
    return ASK_NEW_ADMIN_ID


async def receive_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    if not user_input.isdigit():
        await update.message.reply_text("❌ Noto‘g‘ri ID. Iltimos, raqam yuboring.", reply_markup=BACK_HOME_KB)
        return ASK_NEW_ADMIN_ID

    user_id = user_input
    admins = load_admins()
    if user_id in admins:
        await update.message.reply_text("⚠️ Bu foydalanuvchi allaqachon admin.", reply_markup=BACK_HOME_KB)
        return ASK_NEW_ADMIN_ID

    admins[user_id] = {
        "id": int(user_id),
        "name": update.message.from_user.full_name
    }
    save_admins(admins)

    await update.message.reply_text("✅ Yangi admin muvaffaqiyatli qo‘shildi!", reply_markup=BACK_HOME_KB)
    return ConversationHandler.END


# ➖ Adminni o‘chirish menyusi
async def delete_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admins = load_admins()
    user_id = str(query.from_user.id)

    keyboard = []
    for uid, data in admins.items():
        if uid != user_id:  # o‘zini o‘chira olmaydi
            keyboard.append([
                InlineKeyboardButton(f"{data['name']} ({uid})", callback_data=f"remove_admin_{uid}")
            ])

    keyboard.append([InlineKeyboardButton("🔙 Ortga", callback_data="admin_manage_admins")])

    if len(keyboard) == 1:
        await safe_edit_message(query.message, "📛 Siz yagona adminsiz. O‘zingizni o‘chira olmaysiz!", BACK_HOME_KB)
        return

    await safe_edit_message(
        query.message,
        "🗑 Qaysi adminni o‘chirmoqchisiz?",
        InlineKeyboardMarkup(keyboard)
    )


# ✅ Adminni o‘chirish
async def remove_admin_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = query.data.replace("remove_admin_", "")
    admins = load_admins()

    if admin_id not in admins:
        await safe_edit_message(query.message, "❌ Admin topilmadi.", BACK_HOME_KB)
        return

    del admins[admin_id]
    save_admins(admins)
    await safe_edit_message(query.message, "✅ Admin muvaffaqiyatli o‘chirildi.", BACK_HOME_KB)
