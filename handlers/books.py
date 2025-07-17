import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


# Kitoblar menyusini chiqarish
async def show_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    with open('data/books.json', 'r') as f:
        data = json.load(f)

    books = data.get("kitoblar", [])
    keyboard = []

    row = []
    for i, book in enumerate(books):
        row.append(InlineKeyboardButton(book["nomi"], callback_data=f"book_{book['id']}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🏠 Asosiy sahifa", callback_data="home")])

    await query.edit_message_text(
        text="📚 Mavjud kitoblar ro'yxati:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# Qismlar menyusi
async def show_book_parts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    book_id = query.data.split("_")[1]

    with open('data/books.json', 'r') as f:
        data = json.load(f)

    selected_book = next((b for b in data["kitoblar"] if b["id"] == book_id), None)
    if not selected_book:
        await query.edit_message_text("Kitob topilmadi.")
        return

    keyboard = []
    parts = selected_book.get("qismlar", [])
    row = []
    for i, part in enumerate(parts):
        row.append(InlineKeyboardButton(part["nomi"], callback_data=f"part_{book_id}_{i}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("🔙 Ortga", callback_data="books"),
        InlineKeyboardButton("🏠 Asosiy sahifa", callback_data="home")
    ])

    await query.edit_message_text(
        text=f"🎧 \"{selected_book['nomi']}\" kitobining qismlari:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Statistikaga yozib borish
    views_path = 'data/book_views.json'
    try:
        with open(views_path, 'r') as f:
            stats = json.load(f)
    except:
        stats = {}

    stats[selected_book['nomi']] = stats.get(selected_book['nomi'], 0) + 1

    with open(views_path, 'w') as f:
        json.dump(stats, f, indent=4)


# Qismni yuborish
async def send_audio_part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, book_id, part_index = query.data.split("_")
    part_index = int(part_index)

    with open('data/books.json', 'r') as f:
        data = json.load(f)

    selected_book = next((b for b in data["kitoblar"] if b["id"] == book_id), None)
    if not selected_book:
        await query.edit_message_text("Kitob topilmadi.")
        return

    part = selected_book["qismlar"][part_index]

    await query.message.reply_audio(
        audio=part["audio_url"],
        caption=f"🎧 {selected_book['nomi']} — {part['nomi']}"
    )

    keyboard = [
        [
            InlineKeyboardButton("🔙 Ortga", callback_data=f"book_{book_id}"),
            InlineKeyboardButton("🏠 Asosiy sahifa", callback_data="home")
        ]
    ]

    await query.message.reply_text(
        text="⬆️ Yana boshqa qismlarni tanlashingiz mumkin:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
