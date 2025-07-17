from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
import json
import re

from handlers import books
from utils import load_books, save_books

BOOKS_FILE = "data/books.json"
TELEGRAM_LINK_PATTERN = re.compile(r"^https://t\.me/[\w\d_]+/\d+$")

# States
ADD_BOOK_NAME, ADD_BOOK_PARTS = range(2)
ADD_PART_SELECT_BOOK, ADD_PART_URL = range(100, 102)
DELETE_PART_SELECT_BOOK, DELETE_PART_SELECT, CONFIRM_DELETE_PART = range(200, 203)
ASK_NEW_BOOK_DELETE, CONFIRM_BOOK_DELETE = range(300, 302)

# Temp storage
TEMP_BOOK = {}
TEMP_ADD_PART = {}
TEMP_DELETE_PART = {}


# ==================== KITOB QO‘SHISH ====================

async def ask_book_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add_book")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")],
    ]
    await query.edit_message_text("📖 Yangi kitob nomini yuboring:",
                                  reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_BOOK_NAME


async def receive_book_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    TEMP_BOOK[update.effective_user.id] = {"title": title, "parts": []}
    keyboard = [
        [InlineKeyboardButton("✅ Tugatdim", callback_data="finish_add_book")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_add_book")]
    ]
    await update.message.reply_text(
        f"✅ <b>{title}</b> nomli kitob qabul qilindi.\nEndi qismlarni yuboring:\n<code>https://t.me/your_channel/123</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_BOOK_PARTS


async def receive_book_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("✅ Tugatdim", callback_data="finish_add_book")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_add_book")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")],
    ]
    if not TELEGRAM_LINK_PATTERN.match(text):
        await update.message.reply_text(
            "❌ Noto‘g‘ri format kiritildi.\n\n Quyidagi fromatda yuboring: <code>https://t.me/your_channel/123</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Admin panelga qaytish", callback_data="admin_panel")]]))
        return ADD_BOOK_PARTS
    TEMP_BOOK[user_id]["parts"].append(text)
    await update.message.reply_text(f"🎧 Qism qo‘shildi. Jami: {len(TEMP_BOOK[user_id]['parts'])}",
                                    parse_mode="HTML",
                                    reply_markup=InlineKeyboardMarkup(keyboard)
                                    )
    return ADD_BOOK_PARTS


async def finish_add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]
    ]
    await query.answer()
    user_id = query.from_user.id
    book = TEMP_BOOK.pop(user_id, None)
    if not book:
        await query.edit_message_text("❌ Kitob topilmadi.")
        return ConversationHandler.END
    books = load_books()
    books["kitoblar"].append({
        "id": str(len(books["kitoblar"]) + 1),
        "nomi": book["title"],
        "qismlar": [{"nomi": f"{i + 1}-qism", "audio_url": url} for i, url in enumerate(book["parts"])]
    })
    save_books(books)
    await query.edit_message_text(f"✅ <b>{book['title']}</b> kitobi saqlandi!",
                                  parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(keyboard)
                                  )
    return ConversationHandler.END


async def cancel_add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    TEMP_BOOK.pop(query.from_user.id, None)
    await query.edit_message_text("❌ Kitob qo‘shish bekor qilindi.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]
    ]))
    return ConversationHandler.END


# ==================== QISM QO‘SHISH ====================

async def start_add_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    books = load_books()["kitoblar"]
    if not books:
        await query.edit_message_text("📚 Hech qanday kitob mavjud emas.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(book["nomi"], callback_data=f"addpart_{i}")] for i, book in enumerate(books)]
    keyboard.append([InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")])
    await query.edit_message_text("➕ Qism qo‘shiladigan kitobni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_PART_SELECT_BOOK


async def select_book_for_part_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    index = int(query.data.replace("addpart_", ""))
    TEMP_ADD_PART[query.from_user.id] = index
    keyboard = [[InlineKeyboardButton("🏁 Tugatish", callback_data="cancel_add_part")],
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
    text = update.message.text.strip()
    keyboard = [[InlineKeyboardButton("🏁 Tugatish", callback_data="cancel_add_part")],
                [InlineKeyboardButton("🔙 Ortga", callback_data="admin_add_part")]]

    if not TELEGRAM_LINK_PATTERN.match(text):
        await update.message.reply_text("❌ Noto‘g‘ri havola. <code>https://t.me/kanal/123</code>",
                                        parse_mode="HTML",
                                        reply_markup=InlineKeyboardMarkup(keyboard)
                                        )
        return ADD_PART_URL
    books = load_books()
    book_index = TEMP_ADD_PART[user_id]
    books["kitoblar"][book_index]["qismlar"].append({
        "nomi": f"{len(books['kitoblar'][book_index]['qismlar']) + 1}-qism",
        "audio_url": text
    })
    save_books(books)
    await update.message.reply_text("✅ Qism qo‘shildi.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_PART_URL


async def cancel_add_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    TEMP_ADD_PART.pop(query.from_user.id, None)
    await query.edit_message_text("✔️ Qism qo‘shish yakunlandi.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]
    ]))
    return ConversationHandler.END


# ==================== QISM O‘CHIRISH ====================

async def start_delete_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()  # <-- ✅ Qo‘shildi
    from utils import load_books
    books = load_books()

    if not books["kitoblar"]:
        await query.edit_message_text(
            "📚 Hali hech qanday kitob mavjud emas.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]])
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(book["nomi"], callback_data=f"delpartbook_{book['nomi']}")]
        for book in books["kitoblar"]
    ]
    keyboard.append([InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")])

    await query.edit_message_text("🗂 Qaysi kitobdan qism o‘chirmoqchisiz?", reply_markup=InlineKeyboardMarkup(keyboard))
    return DELETE_PART_SELECT_BOOK


async def select_part_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_name = query.data.replace("delpartbook_", "")
    context.user_data["delete_book_name"] = book_name
    books = load_books()
    parts = next((b["qismlar"] for b in books["kitoblar"] if b["nomi"] == book_name), None)
    if not parts:
        await query.edit_message_text("📭 Bu kitobda hech qanday qism yo‘q.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")],
            [InlineKeyboardButton("🔙 Ortga", callback_data="admin_delete_part")],

        ]))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(part["nomi"], callback_data=f"delpart_{i}")] for i, part in enumerate(parts)]
    keyboard.append([
        InlineKeyboardButton("🔙 Ortga", callback_data="admin_delete_part"),
        InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")
    ])
    await query.edit_message_text("🤔 Qaysi qismini o‘chirmoqchisiz?", reply_markup=InlineKeyboardMarkup(keyboard))
    return DELETE_PART_SELECT


async def confirm_delete_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = int(query.data.replace("delpart_", ""))
    context.user_data["delete_part_index"] = index
    book_name = context.user_data.get("delete_book_name")
    keyboard = [
        [InlineKeyboardButton("✅ Ha, o‘chirilsin", callback_data="confirm_delete_part")],
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_delete_part")],
        [InlineKeyboardButton("🏠 Admin panel", callback_data="admin_panel")]
    ]
    await query.edit_message_text(
        f"⚠️ <b>{book_name}</b> kitobining {index + 1}-qismini o‘chirmoqchimisiz?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM_DELETE_PART


async def really_delete_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_name = context.user_data.get("delete_book_name")
    index = context.user_data.get("delete_part_index")
    books = load_books()
    for book in books["kitoblar"]:
        if book["nomi"] == book_name:
            try:
                deleted_part = book["qismlar"].pop(index)
                save_books(books)
                await query.edit_message_text(
                    f"✅ <b>{deleted_part['nomi']}</b> muvaffaqiyatli o‘chirildi.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🔙 Ortga", callback_data="admin_delete_part")]])
                )
                return ConversationHandler.END
            except IndexError:
                await query.edit_message_text("❌ Qism topilmadi.")
                return ConversationHandler.END
    await query.edit_message_text("❌ Kitob topilmadi.")
    return ConversationHandler.END


# ==================== KITOB O‘CHIRISH ====================

async def admin_list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    books = load_books()["kitoblar"]
    if not books:
        await query.edit_message_text("📚 Hozircha hech qanday kitob mavjud emas.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(book["nomi"], callback_data=f"delete_{i}")] for i, book in enumerate(books)]
    keyboard.append([InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel")])
    await query.edit_message_text("🗑 Qaysi kitobni o‘chirmoqchisiz?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_NEW_BOOK_DELETE


async def ask_confirm_book_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = int(query.data.replace("delete_", ""))
    context.user_data["delete_book_index"] = index
    books = load_books()
    book = books["kitoblar"][index]
    keyboard = [
        [InlineKeyboardButton("✅ Ha, o‘chirish", callback_data="confirm_delete_book")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]
    ]
    await query.edit_message_text(f"⚠️ <b>{book['nomi']}</b> kitobini o‘chirmoqchimisiz?", parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_BOOK_DELETE


async def confirm_book_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = context.user_data.get("delete_book_index")
    if index is None:
        await query.edit_message_text("❌ Xatolik yuz berdi.")
        return

    with open(BOOKS_FILE, "r", encoding="utf-8") as f:
        books = json.load(f)
    try:
        deleted = books["kitoblar"].pop(index)
    except IndexError:
        await query.edit_message_text("❌ Noto‘g‘ri indeks.")
        return

    with open(BOOKS_FILE, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=4)

    # ✅ Tugmalar: Ortga va Asosiy menyu
    keyboard = [
        [InlineKeyboardButton("🔙 Ortga", callback_data="admin_list_books")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]
    ]

    await query.edit_message_text(
        f"✅ <b>{deleted['nomi']}</b> kitobi o‘chirildi.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
