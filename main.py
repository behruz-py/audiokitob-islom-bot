from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from config import BOT_TOKEN
from storage import init_db, add_user
from utils import is_admin

# --- Admin panel va boshqalar ---
from handlers.admin_panel import admin_panel
from handlers.books import show_books, show_book_parts, send_audio_part
from handlers.stats import show_stats_menu, show_user_count, show_book_stats
from handlers.feedback import ask_feedback, save_feedback, cancel_feedback, ASK_FEEDBACK
from handlers.feedback_admin import show_last_feedbacks, dedupe_feedback_handler
from handlers.broadcast import (
    ask_broadcast_message, handle_broadcast, confirm_broadcast, cancel_broadcast,
    ASK_BROADCAST_MESSAGE, CONFIRM_BROADCAST
)
from handlers.admin_manage import (
    admin_manage_admins, ask_admin_id, receive_admin_id,
    delete_admin_menu, remove_admin_confirm, ASK_NEW_ADMIN_ID
)

# --- Janrlar ---
from handlers.genres import (
    show_genres, show_books_in_genre,
    admin_genre_menu, ask_genre_name, receive_genre_name,
    delete_genre_menu, confirm_delete_genre, really_delete_genre,
    ASK_GENRE_NAME, DELETE_GENRE_SELECT, CONFIRM_DELETE_GENRE,
    GENRE_MENU,
)

# --- Kitob boshqaruvi ---
from handlers.book_manage import (
    ask_book_name, receive_book_name, toggle_select_genre, genres_done_then_parts,
    receive_book_part, finish_add_book, cancel_add_book,
    start_add_part, select_book_for_part_add, receive_part_url, cancel_add_part,
    start_delete_part, select_part_to_delete, confirm_delete_part, really_delete_part,
    admin_list_books, ask_confirm_book_delete, confirm_book_delete,
    ADD_BOOK_NAME, SELECT_BOOK_GENRES, ADD_BOOK_PARTS,
    ADD_PART_SELECT_BOOK, ADD_PART_URL,
    DELETE_PART_SELECT_BOOK, DELETE_PART_SELECT, CONFIRM_DELETE_PART
)

# --- Mavjud kitoblarga janr belgilash ---
from handlers.genre_assign import (
    start_assign_genres, pick_book_then_show_genres, toggle_book_genre, save_book_genres,
    SELECT_BOOK_FOR_ASSIGN, TOGGLE_GENRES_FOR_BOOK
)

# --- Kitob nomini tahrirlash (YANGI) ---
from handlers.book_edit import (
    start_rename_book, pick_book_then_ask_title, receive_new_title,
    RENAME_SELECT_BOOK, RENAME_ASK_TITLE
)


# ---------- Start va Asosiy menyu ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.first_name or "")

    keyboard = [
        [InlineKeyboardButton("📚 Kitoblar", callback_data='books')],
        [InlineKeyboardButton("🏷 Janrlar", callback_data='genres')],
        [InlineKeyboardButton("📊 Statistika", callback_data='stats')],
        [InlineKeyboardButton("💬 Fikr bildirish", callback_data='feedback')],
        [InlineKeyboardButton("👤 Admin bilan bog‘lanish", callback_data='admin_contact')],
    ]
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("🛠️ Admin panel", callback_data="admin_panel")])

    text = (f"<b>🖐Assalomu alaykum, {user.first_name}</b>!\n\n"
            "📖 Bu bot orqali audiokitoblarimizni qulay tarzda tinglashingiz mumkin.\n\n🔈<b>Sahifamiz:</b> @audiokitoblar_islom\n\n\n"
            "👇🏻 Quyidagi menyulardan birini tanlang:")

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def admin_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]]
    await query.edit_message_text("👤 Murojaat uchun: @huda_murojaat_bot\n",
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Sizda bu bo‘limga kirish huquqi yo‘q.")
        return
    await admin_panel(update, context)


def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))

    # ----- Feedback -----
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_feedback, pattern="^feedback$")],
        states={ASK_FEEDBACK: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_feedback),
            CallbackQueryHandler(cancel_feedback, pattern="^cancel_feedback$"),
            CallbackQueryHandler(start, pattern="^home$")
        ]},
        fallbacks=[
            CallbackQueryHandler(cancel_feedback, pattern="^cancel_feedback$"),
            CallbackQueryHandler(start, pattern="^home$"),
            MessageHandler(filters.COMMAND, cancel_feedback)
        ],
        per_chat=True, allow_reentry=True
    ))

    # ----- Add Book (with genres) -----
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_book_name, pattern="^admin_add_book$")],
        states={
            ADD_BOOK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_book_name)],
            SELECT_BOOK_GENRES: [
                CallbackQueryHandler(toggle_select_genre, pattern=r"^toggle_genre_"),
                CallbackQueryHandler(genres_done_then_parts, pattern=r"^genres_done$")
            ],
            ADD_BOOK_PARTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_book_part),
                CallbackQueryHandler(finish_add_book, pattern="^finish_add_book$"),
                CallbackQueryHandler(cancel_add_book, pattern="^cancel_add_book$")
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel_add_book, pattern="^cancel_add_book$")],
        per_chat=True, allow_reentry=True
    ))

    # ----- Add Part -----
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_part, pattern="^admin_add_part$")],
        states={
            ADD_PART_SELECT_BOOK: [CallbackQueryHandler(select_book_for_part_add, pattern=r"^addpart_")],
            ADD_PART_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_part_url),
                CallbackQueryHandler(cancel_add_part, pattern="^cancel_add_part$")
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_add_part, pattern="^cancel_add_part$")],
        per_chat=True, allow_reentry=True
    ))

    # ----- Delete Part -----
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_delete_part, pattern="^admin_delete_part$")],
        states={
            DELETE_PART_SELECT_BOOK: [CallbackQueryHandler(select_part_to_delete, pattern=r"^delpartbook_")],
            DELETE_PART_SELECT: [CallbackQueryHandler(confirm_delete_part, pattern=r"^delpart_")],
            CONFIRM_DELETE_PART: [CallbackQueryHandler(really_delete_part, pattern=r"^confirm_delete_part$")],
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern="^admin_panel$")],
        per_chat=True, allow_reentry=True
    ))

    # ----- Broadcast -----
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_broadcast_message, pattern="^admin_broadcast$")],
        states={
            ASK_BROADCAST_MESSAGE: [MessageHandler(filters.ALL, handle_broadcast)],
            CONFIRM_BROADCAST: [
                CallbackQueryHandler(confirm_broadcast, pattern="^confirm_broadcast$"),
                CallbackQueryHandler(cancel_broadcast, pattern="^cancel_broadcast$")
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_broadcast, pattern="^cancel_broadcast$")],
        per_chat=True, allow_reentry=True
    ))

    # ----- Adminlar -----
    app.add_handler(CallbackQueryHandler(admin_manage_admins, pattern="^admin_manage_admins$"))
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_admin_id, pattern="^admin_add_admin$")],
        states={ASK_NEW_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_id)]},
        fallbacks=[], per_chat=True, allow_reentry=True
    ))
    app.add_handler(CallbackQueryHandler(delete_admin_menu, pattern=r"^admin_delete_admin$"))
    app.add_handler(CallbackQueryHandler(remove_admin_confirm, pattern=r"^remove_admin_"))

    # ----- Janrlarni boshqarish -----
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_genre_menu, pattern="^admin_manage_genres$")],
        states={
            GENRE_MENU: [
                CallbackQueryHandler(ask_genre_name, pattern=r"^admin_add_genre$"),
                CallbackQueryHandler(delete_genre_menu, pattern=r"^admin_delete_genre$"),
                CallbackQueryHandler(admin_genre_menu, pattern=r"^admin_manage_genres$"),
            ],
            ASK_GENRE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_genre_name),
                CallbackQueryHandler(admin_genre_menu, pattern=r"^admin_manage_genres$")
            ],
            DELETE_GENRE_SELECT: [
                CallbackQueryHandler(confirm_delete_genre, pattern=r"^delgenre_"),
                CallbackQueryHandler(admin_genre_menu, pattern=r"^admin_manage_genres$")
            ],
            CONFIRM_DELETE_GENRE: [
                CallbackQueryHandler(really_delete_genre, pattern=r"^confirm_delete_genre$"),
                CallbackQueryHandler(admin_genre_menu, pattern=r"^admin_manage_genres$")
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_genre_menu, pattern="^admin_manage_genres$"),
            CallbackQueryHandler(admin_panel, pattern="^admin_panel$"),
            CallbackQueryHandler(start, pattern="^home$"),
        ],
        per_chat=True, allow_reentry=True
    ))

    # ----- Mavjud kitoblarga janr belgilash -----
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_assign_genres, pattern=r"^admin_assign_genres$")],
        states={
            SELECT_BOOK_FOR_ASSIGN: [
                CallbackQueryHandler(pick_book_then_show_genres, pattern=r"^assigngenres_")
            ],
            TOGGLE_GENRES_FOR_BOOK: [
                CallbackQueryHandler(toggle_book_genre, pattern=r"^toggle_book_genre_\d+$"),
                CallbackQueryHandler(save_book_genres, pattern=r"^save_book_genres$"),
                CallbackQueryHandler(start_assign_genres, pattern=r"^admin_assign_genres$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(start_assign_genres, pattern=r"^admin_assign_genres$"),
            CallbackQueryHandler(admin_panel, pattern=r"^admin_panel$"),
            CallbackQueryHandler(start, pattern=r"^home$"),
        ],
        per_chat=True, allow_reentry=True
    ))

    # ----- Kitob nomini tahrirlash (YANGI) -----
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_rename_book, pattern=r"^admin_rename_book$")],
        states={
            RENAME_SELECT_BOOK: [
                CallbackQueryHandler(pick_book_then_ask_title, pattern=r"^renamebook_")
            ],
            RENAME_ASK_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_title),
                CallbackQueryHandler(start_rename_book, pattern=r"^admin_rename_book$")
            ],
        },
        fallbacks=[
            CallbackQueryHandler(start_rename_book, pattern=r"^admin_rename_book$"),
            CallbackQueryHandler(admin_panel, pattern=r"^admin_panel$"),
            CallbackQueryHandler(start, pattern=r"^home$"),
        ],
        per_chat=True, allow_reentry=True
    ))

    # ----- Static handlers -----
    app.add_handler(CallbackQueryHandler(start, pattern="^home$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_contact, pattern="^admin_contact$"))

    app.add_handler(CallbackQueryHandler(send_audio_part, pattern=r"^part_"))
    app.add_handler(CallbackQueryHandler(show_book_parts, pattern=r"^book_"))
    app.add_handler(CallbackQueryHandler(show_books, pattern=r"^books$"))

    # Kitoblar ro‘yxati va o‘chirish
    app.add_handler(CallbackQueryHandler(admin_list_books, pattern=r"^admin_list_books$"))
    app.add_handler(CallbackQueryHandler(admin_list_books, pattern=r"^admin_delete_book$"))
    app.add_handler(CallbackQueryHandler(ask_confirm_book_delete, pattern=r"^deletebook_"))
    app.add_handler(CallbackQueryHandler(confirm_book_delete, pattern=r"^confirm_delete_book$"))

    app.add_handler(CallbackQueryHandler(show_user_count, pattern=r"^stat_users$"))
    app.add_handler(CallbackQueryHandler(show_book_stats, pattern=r"^stat_books$"))
    app.add_handler(CallbackQueryHandler(show_stats_menu, pattern=r"^stats$"))

    app.add_handler(CallbackQueryHandler(show_last_feedbacks, pattern=r"^admin_view_feedback$"))
    app.add_handler(CallbackQueryHandler(show_genres, pattern=r"^genres$"))
    app.add_handler(CallbackQueryHandler(show_books_in_genre, pattern=r"^genre_\d+$"))
    app.add_handler(CallbackQueryHandler(dedupe_feedback_handler, pattern="^admin_dedupe_feedback$"))

    print("✅ Bot ishga tushdi.")
    app.run_polling()


if __name__ == "__main__":
    main()
