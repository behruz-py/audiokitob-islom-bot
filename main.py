import os
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from config import BOT_TOKEN, ADMINS

# Book manage import
from handlers.book_manage import (
    ask_book_name, receive_book_name, receive_book_part, finish_add_book, cancel_add_book,
    start_add_part, select_book_for_part_add, receive_part_url, cancel_add_part,
    start_delete_part, select_part_to_delete,
    confirm_book_delete,
    admin_list_books, confirm_delete_part, really_delete_part,
    ADD_BOOK_NAME, ADD_BOOK_PARTS, ADD_PART_SELECT_BOOK, ADD_PART_URL,
    DELETE_PART_SELECT_BOOK, DELETE_PART_SELECT, CONFIRM_DELETE_PART,
    ask_confirm_book_delete,

)

# Boshqa modullar
from handlers.broadcast import (
    ask_broadcast_message, handle_broadcast, confirm_broadcast, cancel_broadcast,
    ASK_BROADCAST_MESSAGE, CONFIRM_BROADCAST
)
from handlers.feedback import ask_feedback, save_feedback, cancel_feedback, ASK_FEEDBACK
from handlers.books import show_books, show_book_parts, send_audio_part
from handlers.feedback_admin import show_last_feedbacks
from handlers.stats import show_stats_menu, show_user_count, show_book_stats
from handlers.admin_panel import admin_panel
from handlers.admin_manage import (
    admin_manage_admins, ask_admin_id, receive_admin_id, delete_admin_menu,
    remove_admin_confirm, ASK_NEW_ADMIN_ID
)
from handlers.navigation import back_to_home


# ✅ Foydalanuvchini saqlash
def save_user(user_id: int, first_name: str):
    if not os.path.exists('data'):
        os.makedirs('data')
    try:
        with open('data/users.json', 'r', encoding="utf-8") as f:
            users = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        users = {}
    users[str(user_id)] = {"id": user_id, "name": first_name}
    with open('data/users.json', 'w', encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)


# ✅ /start va asosiy menyu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.first_name)

    keyboard = [
        [InlineKeyboardButton("📚 Kitoblar", callback_data='books')],
        [InlineKeyboardButton("📊 Statistika", callback_data='stats')],
        [InlineKeyboardButton("💬 Fikr bildirish", callback_data='feedback')],
        [InlineKeyboardButton("👤 Admin bilan bog‘lanish", callback_data='admin_contact')],
    ]

    if user.id in ADMINS:
        keyboard.append([InlineKeyboardButton("🛠️ Admin panel", callback_data="admin_panel")])

    text = (
        f"Assalomu alaykum, {user.first_name}!\n\n"
        "📖 Bu bot orqali siz audiokitoblarimizni qulay tarzda tinglashingiz mumkin.\n\n"
        "🔈Sahifamiz: @audiokitoblar_islom\n\n"
        "👇🏻Pastdagi menyudan birini tanlang:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return ConversationHandler.END


# ✅ Admin bilan bog‘lanish
async def admin_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]]
    await query.edit_message_text("👤 Murojaat uchun: @huda_murojaat_bot\n\n👩🏻‍💻Texnik yordam uchun: @uygun_oglu",
                                  reply_markup=InlineKeyboardMarkup(keyboard))


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # ===== Feedback Conversation =====
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_feedback, pattern="^feedback$")],
        states={
            ASK_FEEDBACK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_feedback),
                CallbackQueryHandler(cancel_feedback, pattern="^cancel_feedback$"),
                CallbackQueryHandler(start, pattern="^home$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_feedback, pattern="^cancel_feedback$"),
            CallbackQueryHandler(start, pattern="^home$"),
            MessageHandler(filters.COMMAND, cancel_feedback)
        ],
        per_chat=True,
        allow_reentry=True,

    ))

    # ===== Add Book Conversation =====
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_book_name, pattern="^admin_add_book$")],
        states={
            ADD_BOOK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_book_name)],
            ADD_BOOK_PARTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_book_part),
                CallbackQueryHandler(finish_add_book, pattern="^finish_add_book$"),
                CallbackQueryHandler(cancel_add_book, pattern="^cancel_add_book$")
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel_add_book, pattern="^cancel_add_book$")],
        per_chat=True,
        allow_reentry=True,
    ))

    # ===== Add Part Conversation =====
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_part, pattern="^admin_add_part$")],
        states={
            ADD_PART_SELECT_BOOK: [CallbackQueryHandler(select_book_for_part_add, pattern="^addpart_")],
            ADD_PART_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_part_url),
                CallbackQueryHandler(cancel_add_part, pattern="^cancel_add_part$")
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel_add_part, pattern="^cancel_add_part$")],
        per_chat=True,
        allow_reentry=True
    ))

    # ===== Delete Part Conversation =====
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_delete_part, pattern="^admin_delete_part$")],
        states={
            DELETE_PART_SELECT_BOOK: [CallbackQueryHandler(select_part_to_delete, pattern="^delpartbook_")],
            DELETE_PART_SELECT: [CallbackQueryHandler(confirm_delete_part, pattern="^delpart_")],
            CONFIRM_DELETE_PART: [CallbackQueryHandler(really_delete_part, pattern="^confirm_delete_part$")]
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern="^admin_panel$")],
        per_chat=True,
        allow_reentry=True  # ✅ Buni qo‘shish kerak
    ))

    # ===== Broadcast Conversation =====
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_broadcast_message, pattern="^admin_broadcast$")],
        states={
            ASK_BROADCAST_MESSAGE: [
                MessageHandler(
                    filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.AUDIO |
                    filters.VOICE | filters.VIDEO,
                    handle_broadcast
                )
            ],
            CONFIRM_BROADCAST: [
                CallbackQueryHandler(confirm_broadcast, pattern="^confirm_broadcast$"),
                CallbackQueryHandler(cancel_broadcast, pattern="^cancel_broadcast$")
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel_broadcast, pattern="^cancel_broadcast$")],
        per_chat=True,
        allow_reentry=True,

    ))

    # ===== Adminlar boshqaruvi =====
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(ask_admin_id, pattern="^admin_add_admin$")],
        states={
            ASK_NEW_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_id)]
        },
        fallbacks=[],
        per_chat=True,
        allow_reentry=True  # ✅ Qo‘shildi
    ))

    # ===== Boshqa static handlerlar =====
    app.add_handler(CallbackQueryHandler(start, pattern="^home$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_contact, pattern="^admin_contact$"))

    app.add_handler(CallbackQueryHandler(send_audio_part, pattern=r'^part_'))
    app.add_handler(CallbackQueryHandler(show_book_parts, pattern=r'^book_'))
    app.add_handler(CallbackQueryHandler(show_books, pattern='^books$'))

    app.add_handler(CallbackQueryHandler(show_user_count, pattern='^stat_users$'))
    app.add_handler(CallbackQueryHandler(show_book_stats, pattern='^stat_books$'))
    app.add_handler(CallbackQueryHandler(show_stats_menu, pattern='^stats$'))

    app.add_handler(CallbackQueryHandler(admin_list_books, pattern="^admin_delete_book$"))
    app.add_handler(CallbackQueryHandler(ask_confirm_book_delete, pattern="^delete_"))
    app.add_handler(CallbackQueryHandler(confirm_book_delete, pattern="^confirm_delete_"))

    app.add_handler(CallbackQueryHandler(admin_list_books, pattern="^admin_list_books$"))
    app.add_handler(CallbackQueryHandler(show_last_feedbacks, pattern="^admin_view_feedback$"))
    app.add_handler(CallbackQueryHandler(admin_manage_admins, pattern="^admin_manage_admins$"))
    app.add_handler(CallbackQueryHandler(delete_admin_menu, pattern="^admin_delete_admin$"))
    app.add_handler(CallbackQueryHandler(remove_admin_confirm, pattern="^remove_admin_"))

    print("✅ Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
