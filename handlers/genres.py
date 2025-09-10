from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from storage import get_genres, add_genre, delete_genre, get_books_by_genre
from utils import is_admin, safe_edit_message

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
        await safe_edit_message(query.message, "🏷 Hali janrlar qo‘shilmagan.", InlineKeyboardMarkup(kb))
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

    await safe_edit_message(
        query.message,
        "🏷 Janrlar ro‘yxati:",
        InlineKeyboardMarkup(keyboard)
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
        await safe_edit_message(
            query.message,
            "ℹ️ Bu janrda hozircha kitob yo‘q.",
            InlineKeyboardMarkup(kb)
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

    await safe_edit_message(
        query.message,
        "📚 Tanlangan janrdagi kitoblar:",
        InlineKeyboardMarkup(keyboard)
    )


# ========================= Admin oqimi =========================

async def admin_genre_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin uchun janr boshqaruv menyusi."""
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await safe_edit_message(query.message, "⛔ Sizda bu bo‘limga kirish huquqi yo‘q.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("➕ Janr qo‘shish", callback_data="admin_add_genre")],
        [InlineKeyboardButton("🗑 Janrni o‘chirish", callback_data="admin_delete_genre")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")],
    ]
    await safe_edit_message(
        query.message,
        "🏷 <b>Janrlarni boshqarish</b>",
        InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
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
    await safe_edit_message(
        query.message,
        "🆕 Yangi janr nomini yuboring:",
        InlineKeyboardMarkup(kb)
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
        await safe_edit_message(query.message, "ℹ️ O‘chiradigan janr yo‘q.", InlineKeyboardMarkup(kb))
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

    await safe_edit_message(
        query.message,
        "🗑 Qaysi janrni o‘chirmoqchisiz?",
        InlineKeyboardMarkup(keyboard)
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
    await safe_edit_message(
        query.message,
        "⚠️ Ushbu janr o‘chirilsinmi? (Kitoblar o‘chmaydi, faqat bog‘lanishlar o‘chadi.)",
        InlineKeyboardMarkup(kb)
    )
    return CONFIRM_DELETE_GENRE


async def really_delete_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Janrni o‘chirish (kitoblar o‘chmaydi)."""
    query = update.callback_query
    await query.answer()

    gid = context.user_data.get("delete_genre_id")
    if gid is None:
        await safe_edit_message(
            query.message,
            "❌ Xatolik.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🏷 Janr menyusi", callback_data="admin_manage_genres")]])
        )
        return ConversationHandler.END

    delete_genre(int(gid))
    context.user_data.pop("delete_genre_id", None)

    kb = [[InlineKeyboardButton("🏷 Janr menyusi", callback_data="admin_manage_genres")]]
    await safe_edit_message(query.message, "✅ Janr o‘chirildi.", InlineKeyboardMarkup(kb))
    return ConversationHandler.END

