from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler
from storage import get_books, get_genres, get_genres_for_book, set_book_genres

# States
SELECT_BOOK_FOR_ASSIGN = 700
TOGGLE_GENRES_FOR_BOOK = 701


# --- Step 1: Kitob tanlash ---
async def start_assign_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    books = get_books()
    if not books:
        await query.edit_message_text(
            "📚 Hozircha hech qanday kitob mavjud emas.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")]])
        )
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(b["nomi"], callback_data=f"assigngenres_{b['id']}")] for b in books]
    keyboard.append([InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")])

    await query.edit_message_text(
        "🏷 Janr belgilamoqchi bo‘lgan kitobni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_BOOK_FOR_ASSIGN


# --- Step 2: Janrlarni multi-select qilib belgilash ---
async def pick_book_then_show_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    book_id = query.data.replace("assigngenres_", "")
    context.user_data["assign_book_id"] = book_id

    all_genres = get_genres()
    current = {g["id"] for g in get_genres_for_book(book_id)}  # mavjud tanlovlar

    context.user_data["assign_selected_genres"] = set(current)

    if not all_genres:
        await query.edit_message_text(
            "Hali hech qanday janr yaratilmagan. Avval janr yarating: 🏷 Janrlarni boshqarish.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏷 Janrlarni boshqarish", callback_data="admin_manage_genres")],
                [InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")],
            ])
        )
        return ConversationHandler.END

    kb = _genres_keyboard(all_genres, context.user_data["assign_selected_genres"])
    await query.edit_message_text(
        "Tanlang: kitobga tegishli janr(lar)ni belgilang (bir nechtasini tanlash mumkin).",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return TOGGLE_GENRES_FOR_BOOK


def _genres_keyboard(all_genres: list[dict], selected: set[int]):
    kb = []
    row = []
    for g in all_genres:
        marker = "✅" if g["id"] in selected else "▫️"
        row.append(InlineKeyboardButton(f"{marker} {g['nomi']}", callback_data=f"toggle_book_genre_{g['id']}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)

    kb.append([InlineKeyboardButton("💾 Saqlash", callback_data="save_book_genres")])
    kb.append([
        InlineKeyboardButton("🔙 Ortga", callback_data="admin_assign_genres"),
        InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel"),
    ])
    return kb


async def toggle_book_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    book_id = context.user_data.get("assign_book_id")
    if not book_id:
        await query.edit_message_text("❌ Xatolik: kitob holati topilmadi.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")]
        ]))
        return ConversationHandler.END

    gid = int(query.data.replace("toggle_book_genre_", ""))
    selected: set[int] = context.user_data.get("assign_selected_genres", set())
    if gid in selected:
        selected.remove(gid)
    else:
        selected.add(gid)
    context.user_data["assign_selected_genres"] = selected

    all_genres = get_genres()
    kb = _genres_keyboard(all_genres, selected)
    await query.edit_message_text(
        "Tanlang: kitobga tegishli janr(lar)ni belgilang (bir nechtasini tanlash mumkin).",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return TOGGLE_GENRES_FOR_BOOK


# --- Step 3: Saqlash ---
async def save_book_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    book_id = context.user_data.get("assign_book_id")
    selected: set[int] = context.user_data.get("assign_selected_genres", set())

    if not book_id:
        await query.edit_message_text("❌ Xatolik: kitob aniqlanmadi.",
                                      reply_markup=InlineKeyboardMarkup(
                                          [[InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")]]))
        return ConversationHandler.END

    set_book_genres(book_id, list(selected))
    # Tozalash
    context.user_data.pop("assign_book_id", None)
    context.user_data.pop("assign_selected_genres", None)

    await query.edit_message_text(
        "✅ Janrlar muvaffaqiyatli saqlandi.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")]])
    )
    return ConversationHandler.END
