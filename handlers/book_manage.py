from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import re

from storage import (
    get_books, add_book, get_parts, add_part, delete_part_by_index,
    delete_book, get_genres, set_book_genres, get_next_book_id
)

TELEGRAM_LINK_PATTERN = re.compile(r"^https://t\.me/[\w\d_]+/\d+$")

# States
ADD_BOOK_NAME, SELECT_BOOK_GENRES, ADD_BOOK_PARTS = range(3)
ADD_PART_SELECT_BOOK, ADD_PART_URL = range(100, 102)
DELETE_PART_SELECT_BOOK, DELETE_PART_SELECT, CONFIRM_DELETE_PART = range(200, 203)
ASK_BOOK_DELETE, CONFIRM_BOOK_DELETE = range(300, 302)

# Temp storage
TEMP_BOOK = {}  # user_id -> {'title':..., 'genres': set([...]), 'book_id': '...'}
TEMP_ADD_PART = {}


# ==================== KITOB QO‘SHISH ====================

async def ask_book_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add_book")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")],
    ]
    await query.edit_message_text(
        "📖 Yangi kitob nomini yuboring:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_BOOK_NAME


async def receive_book_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = (update.message.text or "").strip()
    TEMP_BOOK[update.effective_user.id] = {"title": title, "genres": set()}
    # Janrlar ro'yxatini chiqaramiz (multi-select)
    genres = get_genres()
    if not genres:
        await update.message.reply_text(
            f"✅ <b>{title}</b> qabul qilindi.\nHozircha janr yo‘q. To‘g‘ridan-to‘g‘ri qismlar kiriting:\n"
            "<code>https://t.me/your_channel/123</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Tugatdim", callback_data="finish_add_book")],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add_book")]
            ])
        )
        return ADD_BOOK_PARTS

    # Multi-select
    kb = []
    row = []
    for g in genres:
        row.append(InlineKeyboardButton(f"▫️ {g['nomi']}", callback_data=f"toggle_genre_{g['id']}"))
        if len(row) == 2:
            kb.append(row);
            row = []
    if row: kb.append(row)
    kb.append([InlineKeyboardButton("✅ Tugatdim (janrlar)", callback_data="genres_done")])
    kb.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add_book")])

    await update.message.reply_text(
        f"📌 <b>{title}</b> — janr(lar)ni tanlang (bir nechtasini tanlashingiz mumkin):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return SELECT_BOOK_GENRES


async def toggle_select_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = TEMP_BOOK.get(user_id)
    if not data:
        await query.edit_message_text("❌ Holat topilmadi.")
        return ConversationHandler.END

    gid = int(query.data.split("_")[2])
    if gid in data["genres"]:
        data["genres"].remove(gid)
    else:
        data["genres"].add(gid)

    # Qayta chizamiz
    genres = get_genres()
    kb = []
    row = []
    for g in genres:
        marker = "✅" if g["id"] in data["genres"] else "▫️"
        row.append(InlineKeyboardButton(f"{marker} {g['nomi']}", callback_data=f"toggle_genre_{g['id']}"))
        if len(row) == 2:
            kb.append(row);
            row = []
    if row: kb.append(row)
    kb.append([InlineKeyboardButton("✅ Tugatdim (janrlar)", callback_data="genres_done")])
    kb.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add_book")])

    await query.edit_message_text(
        "🏷 Tanlangan janrlar:",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def genres_done_then_parts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("✅ Tugatdim", callback_data="finish_add_book")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_add_book")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")],
    ]
    await query.edit_message_text(
        "🎧 Endi qismlar havolasini yuboring (har birini alohida xabar bilan):\n<code>https://t.me/kanal/123</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_BOOK_PARTS


async def receive_book_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()
    keyboard = [
        [InlineKeyboardButton("✅ Tugatdim", callback_data="finish_add_book")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_add_book")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")],
    ]
    if not TELEGRAM_LINK_PATTERN.match(text):
        await update.message.reply_text(
            "❌ Noto‘g‘ri format.\n<code>https://t.me/kanal/123</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADD_BOOK_PARTS

    # DBga yozish: agar hali kitob yaratilmagan bo'lsa, avval uni yaratamiz
    data = TEMP_BOOK.get(user_id)
    if "book_id" not in data:
        book_id = get_next_book_id()
        add_book(book_id, data["title"])
        # janr bog'lash
        if data["genres"]:
            set_book_genres(book_id, list(data["genres"]))
        data["book_id"] = book_id

    book_id = data["book_id"]
    # navbatdagi qism nomi
    parts = get_parts(book_id)
    part_name = f"{len(parts) + 1}-qism"
    add_part(book_id, part_name, text)

    await update.message.reply_text(
        f"🎧 Qism qo‘shildi. Jami: {len(parts) + 1}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_BOOK_PARTS


async def finish_add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    TEMP_BOOK.pop(user_id, None)  # tozalash

    keyboard = [[InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]]
    await query.edit_message_text(
        "✅ Kitob saqlandi!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END


async def cancel_add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    TEMP_BOOK.pop(query.from_user.id, None)
    await query.edit_message_text(
        "❌ Kitob qo‘shish bekor qilindi.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]
        ])
    )
    return ConversationHandler.END


# ==================== QISM QO‘SHISH (Mavjud kitobga) ====================

async def start_add_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mavjud kitobni tanlash — 2 ustun."""
    query = update.callback_query
    await query.answer()
    books = get_books()
    if not books:
        await query.edit_message_text("📚 Hech qanday kitob mavjud emas.")
        return ConversationHandler.END

    # 2 ustunli klaviatura
    keyboard = []
    row = []
    for b in books:
        row.append(InlineKeyboardButton(b["nomi"], callback_data=f"addpart_{b['id']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")])

    await query.edit_message_text(
        "➕ Qism qo‘shiladigan kitobni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_PART_SELECT_BOOK


async def select_book_for_part_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = query.data.replace("addpart_", "")
    TEMP_ADD_PART[query.from_user.id] = book_id
    keyboard = [
        [InlineKeyboardButton("🏁 Tugatish", callback_data="cancel_add_part")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_add_part")]
    ]
    await query.edit_message_text(
        "🎧 Qism havolasini yuboring:\n<code>https://t.me/kanal/123</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_PART_URL


async def receive_part_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()
    keyboard = [
        [InlineKeyboardButton("🏁 Tugatish", callback_data="cancel_add_part")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_add_part")]
    ]

    if not TELEGRAM_LINK_PATTERN.match(text):
        await update.message.reply_text(
            "❌ Noto‘g‘ri havola. <code>https://t.me/kanal/123</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADD_PART_URL

    book_id = TEMP_ADD_PART[user_id]
    parts = get_parts(book_id)
    part_name = f"{len(parts) + 1}-qism"
    add_part(book_id, part_name, text)

    await update.message.reply_text(
        "✅ Qism qo‘shildi.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_PART_URL


async def cancel_add_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    TEMP_ADD_PART.pop(query.from_user.id, None)
    await query.edit_message_text(
        "✔️ Qism qo‘shish yakunlandi.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]
        ])
    )
    return ConversationHandler.END


# ==================== QISM O‘CHIRISH ====================

async def start_delete_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    books = get_books()
    if not books:
        await query.edit_message_text(
            "📚 Hali hech qanday kitob mavjud emas.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]
            ])
        )
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(b["nomi"], callback_data=f"delpartbook_{b['id']}")] for b in books]
    keyboard.append([InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")])

    await query.edit_message_text(
        "🗂 Qaysi kitobdan qism o‘chirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DELETE_PART_SELECT_BOOK


async def select_part_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = query.data.replace("delpartbook_", "")
    context.user_data["delete_book_id"] = book_id
    parts = get_parts(book_id)
    if not parts:
        await query.edit_message_text(
            "📭 Bu kitobda hech qanday qism yo‘q.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")],
                [InlineKeyboardButton("🔙 Ortga", callback_data="admin_delete_part")],
            ])
        )
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(p["nomi"], callback_data=f"delpart_{i}")] for i, p in enumerate(parts)]
    keyboard.append([
        InlineKeyboardButton("🔙 Ortga", callback_data="admin_delete_part"),
        InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")
    ])

    await query.edit_message_text(
        "🤔 Qaysi qismini o‘chirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DELETE_PART_SELECT


async def confirm_delete_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = int(query.data.replace("delpart_", ""))
    context.user_data["delete_part_index"] = index
    keyboard = [
        [InlineKeyboardButton("✅ Ha, o‘chirilsin", callback_data="confirm_delete_part")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_delete_part")],
        [InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")]
    ]
    await query.edit_message_text(
        f"⚠️ {index + 1}-qism o‘chirilsinmi?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM_DELETE_PART


async def really_delete_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = context.user_data.get("delete_book_id")
    index = context.user_data.get("delete_part_index")
    if book_id is None or index is None:
        await query.edit_message_text("❌ Xatolik.")
        return ConversationHandler.END

    delete_part_by_index(book_id, index)

    await query.edit_message_text(
        "✅ Qism o‘chirildi.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Ortga", callback_data="admin_delete_part")]]
        )
    )
    return ConversationHandler.END


# ==================== KITOB O‘CHIRISH / RO‘YXAT (ADMINDA 2 USTUN) ====================

async def admin_list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin paneldagi "Kitoblar ro‘yxati" sahifasi — 2 USTUNDA.
    """
    query = update.callback_query
    await query.answer()
    books = get_books()
    if not books:
        await query.edit_message_text(
            "📚 Hozircha hech qanday kitob mavjud emas.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")],
                [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]
            ])
        )
        return ConversationHandler.END

    # 2 ustunli klaviatura
    keyboard = []
    row = []
    for b in books:
        row.append(InlineKeyboardButton(b["nomi"], callback_data=f"deletebook_{b['id']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")])

    await query.edit_message_text(
        "🗑 Qaysi kitobni o‘chirmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASK_BOOK_DELETE


async def ask_confirm_book_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = query.data.replace("deletebook_", "")
    context.user_data["delete_book_id"] = book_id
    keyboard = [
        [InlineKeyboardButton("✅ Ha, o‘chirish", callback_data="confirm_delete_book")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]
    ]
    await query.edit_message_text(
        "⚠️ Kitob o‘chirilsinmi?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM_BOOK_DELETE


async def confirm_book_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = context.user_data.get("delete_book_id")
    if not book_id:
        await query.edit_message_text("❌ Xatolik yuz berdi.")
        return ConversationHandler.END

    delete_book(book_id)

    keyboard = [
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_list_books")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]
    ]
    await query.edit_message_text(
        "✅ Kitob o‘chirildi.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END
