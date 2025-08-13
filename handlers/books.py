from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from storage import get_books, get_parts, get_book, increment_book_view


# 📚 Barcha kitoblar ro'yxati (qismlari bo'lmasa ham ko'rsatiladi)
async def show_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    books = get_books()  # <- faqat books jadvalidan
    if not books:
        keyboard = [[
            InlineKeyboardButton("🏠 Asosiy sahifa", callback_data="home"),
        ]]
        await query.edit_message_text(
            "📚 Hozircha kitoblar mavjud emas.",
            reply_markup=InlineKeyboardMarkup(keyboard)
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
        InlineKeyboardButton("🔙 Ortga", callback_data="home"),
        InlineKeyboardButton("🏠 Asosiy sahifa", callback_data="home"),
    ])

    await query.edit_message_text(
        "📚 Mavjud kitoblar ro'yxati:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# 🎧 Tanlangan kitob qismlari (bo'lmasa xabar chiqadi)
async def show_book_parts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, book_id = query.data.split("_", 1)

    # Statistikani kitob ochilganda ham yuritamiz
    book = get_book(book_id)
    if book:
        increment_book_view(book["nomi"])

    parts = get_parts(book_id)

    # Qismlar yo'q bo'lsa — foydalanuvchiga xabar
    if not parts:
        keyboard = [
            [
                InlineKeyboardButton("🔙 Ortga", callback_data="books"),
                InlineKeyboardButton("🏠 Asosiy sahifa", callback_data="home"),
            ]
        ]
        await query.edit_message_text(
            "ℹ️ Bu kitob uchun hozircha qismlar yuklanmagan.\n"
            "Yaqinda qo‘shiladi.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Qismlar mavjud — menyuni chiqaramiz
    keyboard = []
    row = []
    for i, p in enumerate(parts):
        row.append(InlineKeyboardButton(p["nomi"], callback_data=f"part_{book_id}_{i}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("🔙 Ortga", callback_data="books"),
        InlineKeyboardButton("🏠 Asosiy sahifa", callback_data="home"),
    ])

    await query.edit_message_text(
        f"🎧 Qismlar ro‘yxati:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ⬇️ Qismni yuborish
async def send_audio_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, book_id, part_index = query.data.split("_")
    part_index = int(part_index)

    parts = get_parts(book_id)
    if not parts or part_index < 0 or part_index >= len(parts):
        await query.edit_message_text(
            "❌ Qism topilmadi yoki hali qo‘shilmagan.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔙 Ortga", callback_data=f"book_{book_id}"),
                    InlineKeyboardButton("🏠 Asosiy sahifa", callback_data="home"),
                ]
            ])
        )
        return

    part = parts[part_index]
    await query.message.reply_audio(
        audio=part["audio_url"],
        caption=f"{part['nomi']}"
    )

    keyboard = [[
        InlineKeyboardButton("🔙 Ortga", callback_data=f"book_{book_id}"),
        InlineKeyboardButton("🏠 Asosiy sahifa", callback_data="home"),
    ]]
    await query.message.reply_text(
        "⬆️ Yana boshqa qismlarni tanlashingiz mumkin:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
