from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from storage import get_books, get_book, update_book_title

RENAME_SELECT_BOOK = 820
RENAME_ASK_TITLE = 821


# --- Step 1: Kitob tanlash ---
async def start_rename_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    books = get_books()
    if not books:
        await query.edit_message_text(
            "📚 Hozircha hech qanday kitob mavjud emas.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")]])
        )
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(b["nomi"], callback_data=f"renamebook_{b['id']}")] for b in books]
    keyboard.append([InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")])

    await query.edit_message_text(
        "✏️ Nomini tahrirlamoqchi bo‘lgan kitobni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return RENAME_SELECT_BOOK


# --- Step 2: Yangi nomni so'rash ---
async def pick_book_then_ask_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    book_id = query.data.replace("renamebook_", "")
    context.user_data["rename_book_id"] = book_id

    book = get_book(book_id)
    old = book["nomi"] if book else "—"

    keyboard = [[
        InlineKeyboardButton("🔙 Ortga", callback_data="admin_rename_book"),
        InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel"),
    ]]
    await query.edit_message_text(
        f"Yangi nomni yuboring.\n\nHozirgi nom: <b>{old}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return RENAME_ASK_TITLE


# --- Step 3: Saqlash ---
async def receive_new_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_title = (update.message.text or "").strip()
    if not new_title:
        await update.message.reply_text("❌ Nomi bo‘sh bo‘lmasin. Qayta yuboring.")
        return RENAME_ASK_TITLE

    book_id = context.user_data.get("rename_book_id")
    if not book_id:
        await update.message.reply_text(
            "❌ Xatolik: Kitob aniqlanmadi.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")]])
        )
        return ConversationHandler.END

    update_book_title(book_id, new_title)
    context.user_data.pop("rename_book_id", None)

    keyboard = [[InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")]]
    await update.message.reply_text("✅ Kitob nomi yangilandi.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END
