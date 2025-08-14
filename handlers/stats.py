from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from storage import get_users, get_book_views, get_books


async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("👥 Foydalanuvchilar soni", callback_data="stat_users")],
        [InlineKeyboardButton("📖 Kitoblar statistikasi", callback_data="stat_books")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]
    ]
    await query.edit_message_text("📊 Statistika menyusi:", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_user_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    count = len(get_users())
    keyboard = [[
        InlineKeyboardButton("🔙 Ortga", callback_data="stats"),
        InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")
    ]]
    await query.edit_message_text(
        text=f"👥 Botdan foydalanuvchilar soni: <b>{count}</b> ta",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_book_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    views = {row["book_name"]: row["count"] for row in get_book_views()}
    books = get_books()
    titles = {b["nomi"] for b in books}

    filtered = {t: c for t, c in views.items() if t in titles}
    if not filtered:
        text = "📚 Hali statistik ma’lumot yo‘q yoki mavjud kitoblarga tegishli emas.\n\n" \
               "ℹ️ Statistika kitob qismlar ro‘yxatini ochganingizda yangilanadi."
    else:
        sorted_stats = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
        text = "📖 Kitoblar bo‘yicha statistika:\n\n"
        for name, cnt in sorted_stats:
            text += f"• <b>{name}</b>: {cnt} marta ochilgan\n"

    keyboard = [[
        InlineKeyboardButton("🔙 Ortga", callback_data="stats"),
        InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")
    ]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
