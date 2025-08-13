import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from storage import get_users

ASK_BROADCAST_MESSAGE = 100
CONFIRM_BROADCAST = 101


async def ask_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_broadcast")],
        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]
    ]
    await query.edit_message_text("✍️ Yubormoqchi bo‘lgan xabaringizni (matn yoki media) kiriting:",
                                  reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_BROADCAST_MESSAGE


async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    context.user_data["broadcast_message"] = message
    keyboard = [
        [InlineKeyboardButton("✅ Ha, yubor", callback_data="confirm_broadcast")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_broadcast")]
    ]
    if message.text:
        await message.reply_text(f"📨 Matn yuborilsinmi?\n\n{message.text}",
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    elif message.photo:
        await message.reply_photo(photo=message.photo[-1].file_id,
                                  caption="📸 Xabarni yuborishni tasdiqlaysizmi?",
                                  reply_markup=InlineKeyboardMarkup(keyboard))
    elif message.document:
        await message.reply_document(document=message.document.file_id,
                                     caption="📄 Xabarni yuborishni tasdiqlaysizmi?",
                                     reply_markup=InlineKeyboardMarkup(keyboard))
    elif message.audio:
        await message.reply_audio(audio=message.audio.file_id,
                                  caption="🎵 Xabarni yuborishni tasdiqlaysizmi?",
                                  reply_markup=InlineKeyboardMarkup(keyboard))
    elif message.voice:
        await message.reply_voice(voice=message.voice.file_id,
                                  caption="🎙️ Xabarni yuborishni tasdiqlaysizmi?",
                                  reply_markup=InlineKeyboardMarkup(keyboard))
    elif message.video:
        await message.reply_video(video=message.video.file_id,
                                  caption="🎥 Xabarni yuborishni tasdiqlaysizmi?",
                                  reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await message.reply_text("❌ Ushbu turdagi fayl qo‘llab-quvvatlanmaydi.")
        return ASK_BROADCAST_MESSAGE
    return CONFIRM_BROADCAST


async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    message = context.user_data.get("broadcast_message")
    if not message:
        await query.edit_message_text("❌ Xabar topilmadi.")
        return ConversationHandler.END

    user_ids = [u["id"] for u in get_users()]
    success = 0;
    fail = 0

    for uid in user_ids:
        try:
            if message.text:
                await context.bot.send_message(chat_id=uid, text=message.text)
            elif message.photo:
                await context.bot.send_photo(chat_id=uid, photo=message.photo[-1].file_id,
                                             caption=message.caption or "")
            elif message.document:
                await context.bot.send_document(chat_id=uid, document=message.document.file_id,
                                                caption=message.caption or "")
            elif message.audio:
                await context.bot.send_audio(chat_id=uid, audio=message.audio.file_id, caption=message.caption or "")
            elif message.voice:
                await context.bot.send_voice(chat_id=uid, voice=message.voice.file_id, caption=message.caption or "")
            elif message.video:
                await context.bot.send_video(chat_id=uid, video=message.video.file_id, caption=message.caption or "")
            success += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)

    context.user_data.pop("broadcast_message", None)
    keyboard = [[
        InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel"),
        InlineKeyboardButton("📨 Yana yuborish", callback_data="admin_broadcast")
    ]]
    response_text = f"✅ Xabar yuborildi!\n\n👥 Umumiy foydalanuvchilar: {len(user_ids)}\n📬 Yuborilganlar: {success}\n❌ Xatoliklar: {fail}"
    try:
        await query.edit_message_text(response_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        await query.message.reply_text(response_text, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("broadcast_message", None)
    keyboard = [[InlineKeyboardButton("🏠 Asosiy menyu", callback_data="admin_panel")]]
    try:
        await query.edit_message_text("❌ Xabar yuborish bekor qilindi.", reply_markup=InlineKeyboardMarkup(keyboard))
    except:
        await query.message.reply_text("❌ Xabar yuborish bekor qilindi.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END
