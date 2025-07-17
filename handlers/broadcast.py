import asyncio
import os
import json

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import ContextTypes, ConversationHandler

USERS_FILE = "data/users.json"

ASK_BROADCAST_MESSAGE = 100
CONFIRM_BROADCAST = 101


# 1. Xabar so‘rash
async def ask_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_broadcast")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]
    ]

    await query.edit_message_text(
        "✍️ Yubormoqchi bo‘lgan xabaringizni (matn yoki media) kiriting:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASK_BROADCAST_MESSAGE


# 2. Xabarni qabul qilish va tasdiqlash
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    context.user_data["broadcast_message"] = message

    keyboard = [
        [InlineKeyboardButton("✅ Ha, yubor", callback_data="confirm_broadcast")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_broadcast")]
    ]

    if message.text:
        await message.reply_text(
            f"📨 Siz yubormoqchi bo‘lgan matn:\n\n{message.text}\n\nTasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif message.photo:
        await message.reply_photo(
            photo=message.photo[-1].file_id,
            caption="📸 Xabarni yuborishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif message.document:
        await message.reply_document(
            document=message.document.file_id,
            caption="📄 Xabarni yuborishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif message.audio:
        await message.reply_audio(
            audio=message.audio.file_id,
            caption="🎵 Xabarni yuborishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif message.voice:
        await message.reply_voice(
            voice=message.voice.file_id,
            caption="🎙️ Xabarni yuborishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif message.video:
        await message.reply_video(
            video=message.video.file_id,
            caption="🎥 Xabarni yuborishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await message.reply_text("❌ Ushbu turdagi fayl qo‘llab-quvvatlanmaydi.")
        return ASK_BROADCAST_MESSAGE

    return CONFIRM_BROADCAST


# 3. Xabarni yuborish
# 3. Xabarni yuborish (YANGILANGAN)
async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    message = context.user_data.get("broadcast_message")
    if not message:
        await query.edit_message_text("❌ Xabar topilmadi.")
        return ConversationHandler.END

    # Foydalanuvchilarni o‘qish
    if not os.path.exists(USERS_FILE):
        await query.edit_message_text("❌ Foydalanuvchilar ro‘yxati topilmadi.")
        return ConversationHandler.END

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users_data = json.load(f)

    user_ids = [int(uid) for uid in users_data]

    success = 0
    fail = 0

    for uid in user_ids:
        try:
            if message.text:
                await context.bot.send_message(chat_id=uid, text=message.text)

            elif message.photo:
                await context.bot.send_photo(
                    chat_id=uid,
                    photo=message.photo[-1].file_id,
                    caption=message.caption or ""
                )

            elif message.document:
                await context.bot.send_document(
                    chat_id=uid,
                    document=message.document.file_id,
                    caption=message.caption or ""
                )

            elif message.audio:
                await context.bot.send_audio(
                    chat_id=uid,
                    audio=message.audio.file_id,
                    caption=message.caption or ""
                )

            elif message.voice:
                await context.bot.send_voice(
                    chat_id=uid,
                    voice=message.voice.file_id,
                    caption=message.caption or ""
                )

            elif message.video:
                await context.bot.send_video(
                    chat_id=uid,
                    video=message.video.file_id,
                    caption=message.caption or ""
                )

            success += 1
        except Exception as e:
            fail += 1
        await asyncio.sleep(0.05)

    context.user_data.pop("broadcast_message", None)

    keyboard = [[
        InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel"),
        InlineKeyboardButton("📨 Yana yuborish", callback_data="admin_broadcast")
    ]]

    response_text = (
        f"✅ Xabar yuborildi!\n\n"
        f"👥 Umumiy foydalanuvchilar: {len(user_ids)}\n"
        f"📬 Yuborilganlar: {success}\n"
        f"❌ Xatolik bo‘lganlar: {fail}"
    )

    # ⚠️ Agar xabarni edit qilib bo‘lmasa (media edi), yangisini yuboramiz
    try:
        await query.edit_message_text(response_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        await query.message.reply_text(response_text, reply_markup=InlineKeyboardMarkup(keyboard))

    return ConversationHandler.END


# 4. Bekor qilish
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data.pop("broadcast_message", None)

    keyboard = [[InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]]
    try:
        await query.edit_message_text(
            "❌ Xabar yuborish bekor qilindi.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except:
        await query.message.reply_text(
            "❌ Xabar yuborish bekor qilindi.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return ConversationHandler.END
