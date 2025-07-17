import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

FEEDBACK_FILE = "data/feedback.json"
ASK_FEEDBACK = 1


# 💬 Fikr olishni boshlash
async def ask_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_feedback"),
            InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home"),
        ]
    ]

    await query.edit_message_text(
        text=(
            "💬 Fikringizni yozib yuboring. Taklif, tanqid yoki minnatdorchilik bo‘lishi mumkin.\n\n"
            "✍️ Yozib bo‘lgach, yuboring.\n\n"
            "👇 Pastdagi tugmalar orqali bekor qilishingiz yoki menyuga qaytishingiz mumkin."
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return ASK_FEEDBACK


# ✅ Fikrni saqlash
async def save_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    feedback = {
        "id": user.id,
        "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
        "username": user.username or "Nomaʼlum",
        "text": text
    }

    all_feedback = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                all_feedback = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            all_feedback = []

    all_feedback.append(feedback)
    if len(all_feedback) > 100:
        all_feedback = all_feedback[-100:]

    try:
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(all_feedback, f, indent=4, ensure_ascii=False)
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")
        return ConversationHandler.END

    await update.message.reply_text("✅ Fikringiz uchun rahmat!")

    keyboard = [[InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]]
    await update.message.reply_text(
        "Yana nimadir qilishni istaysizmi?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return ConversationHandler.END


# 🚫 Bekor qilish
async def cancel_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")]]

    await query.edit_message_text(
        "❌ Fikr bildirish bekor qilindi.\n\nQuyidagi tugma orqali asosiy menyuga qaytishingiz mumkin:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END
