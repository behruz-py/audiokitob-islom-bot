from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from storage import get_genres, add_genre, delete_genre, get_books_by_genre
from utils import is_admin

# States
GENRE_MENU = 590
ASK_GENRE_NAME = 591
DELETE_GENRE_SELECT = 592
CONFIRM_DELETE_GENRE = 593


# ========================= Foydalanuvchi oqimi =========================

async def show_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi uchun janrlar ro'yxati (2 ustun)."""
    query = update.callback_query
    await query.answer()

    genres = get_genres()
    if not genres:
        kb = [[InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]]
        await query.edit_message_text("🏷 Hali janrlar qo‘shilmagan.", reply_markup=InlineKeyboardMarkup(kb))
        return

    keyboard = []
    row = []
    for g in genres:
        row.append(InlineKeyboardButton(g["nomi"], callback_data=f"genre_{g['id']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("🔙 Ortga", callback_data="home"),
        InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home"),
    ])

    await query.edit_message_text(
        "🏷 Janrlar ro‘yxati:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_books_in_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tanlangan janrdagi kitoblar ro‘yxati (2 ustun)."""
    query = update.callback_query
    await query.answer()

    gid = int(query.data.replace("genre_", ""))
    books = get_books_by_genre(gid)

    if not books:
        kb = [[
            InlineKeyboardButton("🔙 Ortga (janrlar)", callback_data="genres"),
            InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home"),
        ]]
        await query.edit_message_text(
            "ℹ️ Bu janrda hozircha kitob yo‘q.",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    keyboard = []
    row = []
    for b in books:
        row.append(InlineKeyboardButton(b["nomi"], callback_data=f"book_{b['id']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("🔙 Ortga (janrlar)", callback_data="genres"),
        InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home"),
    ])

    await query.edit_message_text(
        "📚 Tanlangan janrdagi kitoblar:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ========================= Admin oqimi =========================

async def admin_genre_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin uchun janr boshqaruv menyusi."""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.edit_message_text("⛔ Sizda bu bo‘limga kirish huquqi yo‘q.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("➕ Janr qo‘shish", callback_data="admin_add_genre")],
        [InlineKeyboardButton("🗑 Janrni o‘chirish", callback_data="admin_delete_genre")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")],
    ]
    await query.edit_message_text(
        "🏷 <b>Janrlarni boshqarish</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return GENRE_MENU


async def ask_genre_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi janr nomini so'rash."""
    query = update.callback_query
    await query.answer()

    kb = [[
        InlineKeyboardButton("🔙 Ortga", callback_data="admin_manage_genres"),
        InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home"),
    ]]
    await query.edit_message_text(
        "🆕 Yangi janr nomini yuboring:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return ASK_GENRE_NAME


async def receive_genre_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi janrni DB ga yozish."""
    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text("❌ Janr nomi bo‘sh bo‘lmasin. Qayta yuboring.")
        return ASK_GENRE_NAME

    add_genre(name)

    kb = [[InlineKeyboardButton("🏷 Janr menyusi", callback_data="admin_manage_genres")]]
    await update.message.reply_text("✅ Janr qo‘shildi.", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END


async def delete_genre_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Janrni o‘chirish uchun tanlash (2 ustun)."""
    query = update.callback_query
    await query.answer()

    genres = get_genres()
    if not genres:
        kb = [[InlineKeyboardButton("🏷 Janr menyusi", callback_data="admin_manage_genres")]]
        await query.edit_message_text("ℹ️ O‘chiradigan janr yo‘q.", reply_markup=InlineKeyboardMarkup(kb))
        return ConversationHandler.END

    keyboard = []
    row = []
    for g in genres:
        row.append(InlineKeyboardButton(g["nomi"], callback_data=f"delgenre_{g['id']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("🔙 Ortga", callback_data="admin_manage_genres"),
        InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home"),
    ])

    await query.edit_message_text(
        "🗑 Qaysi janrni o‘chirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DELETE_GENRE_SELECT


async def confirm_delete_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Janr o‘chirishni tasdiqlash."""
    query = update.callback_query
    await query.answer()

    gid = int(query.data.replace("delgenre_", ""))
    context.user_data["delete_genre_id"] = gid

    kb = [
        [InlineKeyboardButton("✅ Ha, o‘chirilsin", callback_data="confirm_delete_genre")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_delete_genre")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")],
    ]
    await query.edit_message_text(
        "⚠️ Ushbu janr o‘chirilsinmi? (Kitoblar o‘chmaydi, faqat bog‘lanishlar o‘chadi.)",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return CONFIRM_DELETE_GENRE


async def really_delete_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Janrni o‘chirish (kitoblar o‘chmaydi)."""
    query = update.callback_query
    await query.answer()

    gid = context.user_data.get("delete_genre_id")
    if gid is None:
        await query.edit_message_text("❌ Xatolik.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏷 Janr menyusi", callback_data="admin_manage_genres")]
        ]))
        return ConversationHandler.END

    delete_genre(int(gid))
    context.user_data.pop("delete_genre_id", None)

    kb = [[InlineKeyboardButton("🏷 Janr menyusi", callback_data="admin_manage_genres")]]
    await query.edit_message_text("✅ Janr o‘chirildi.", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END
