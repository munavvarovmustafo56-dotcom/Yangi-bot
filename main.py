import os
import logging
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from flask import Flask, render_template, request, jsonify
import threading
import json

# ===== SOZLAMALAR =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "8528746370:AAH7K_PYqQWKMbLzRAjiWmkCjOOWNKMSdvk")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAT0tZOZgoIr4fKN7eSH0FpJvSguKpuwLs")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app
flask_app = Flask(__name__)

# Foydalanuvchi suhbat tarixi
user_histories = {}

SYSTEM_PROMPT = """Sen "Olov AI" - kuchli, aqlli va do'stona sun'iy intellektsiyasan. 
Sen o'zbek tilida ham, rus tilida ham, ingliz tilida ham bemalol gaplasha olasan.
Har doim aniq, foydali va tushunarli javoblar ber.
Emoji ishlatishni yaxshi ko'rasan va suhbatni qiziqarli qilasan! 🔥"""

# ===== GEMINI AI FUNKSIYASI =====
async def ask_gemini(user_id: int, message: str) -> str:
    """Gemini AI ga savol yuborish"""
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    user_histories[user_id].append({
        "role": "user",
        "parts": [{"text": message}]
    })
    
    # Oxirgi 20 ta xabarni saqlash (token tejash)
    if len(user_histories[user_id]) > 20:
        user_histories[user_id] = user_histories[user_id][-20:]
    
    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": user_histories[user_id],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 2048,
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GEMINI_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    answer = data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # Bot javobini tarixga qo'shish
                    user_histories[user_id].append({
                        "role": "model",
                        "parts": [{"text": answer}]
                    })
                    return answer
                else:
                    error_text = await resp.text()
                    logger.error(f"Gemini xato: {resp.status} - {error_text}")
                    return "⚠️ AI bilan bog'lanishda xato yuz berdi. Keyinroq urinib ko'ring."
    except asyncio.TimeoutError:
        return "⏱️ So'rov vaqti tugadi. Iltimos qayta urinib ko'ring."
    except Exception as e:
        logger.error(f"Gemini xatosi: {e}")
        return "❌ Xato yuz berdi. Iltimos keyinroq urinib ko'ring."

# ===== BOT HANDLERLAR =====
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🔥 Suhbatni boshlash", callback_data="start_chat")],
        [InlineKeyboardButton("❓ Yordam", callback_data="help"),
         InlineKeyboardButton("🗑️ Tozalash", callback_data="clear")],
        [InlineKeyboardButton("🌐 Web sayt", url="https://your-app.onrender.com")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🔥 *Salom, {user.first_name}!*

Men *Olov AI* — sizning aqlli yordamchingizman!

🧠 Nima qila olaman:
• Har qanday savolga javob beraman
• Kod yozaman va tushuntiraman  
• Tarjima qilaman
• Ijodiy matnlar yozaman
• Matematik masalalar yechaman
• Va boshqa ko'p narsalar!

📝 *Qanday ishlatish:*
Shunchaki menga xabar yuboring!

_Powered by Google Gemini 1.5 Flash_ ⚡
    """
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    help_text = """
🆘 *YORDAM*

*Komandalar:*
/start — Boshlanish sahifasi
/help — Yordam
/clear — Suhbat tarixini tozalash
/about — Bot haqida

*Qanday ishlaydi:*
Menga istalgan xabar yuboring — men darhol javob beraman!

*Misol savollar:*
• "Python da list nima?"
• "Bu gapni inglizchaga tarjima qil: Salom dunyo"
• "5 ta qiziqarli fakt ayt"
• "Keksa odamga sovg'a tavsiya qil"

🔥 *Bot qobiliyatlari:*
✅ Ko'p tilli (O'zbek, Rus, Ingliz)
✅ Suhbat tarixi (20 ta xabar)
✅ Tez javob (Gemini Flash)
✅ 24/7 ishlaydi
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suhbat tarixini tozalash"""
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text(
        "🗑️ *Suhbat tarixi tozalandi!*\nYangi suhbat boshlashingiz mumkin.",
        parse_mode="Markdown"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot haqida"""
    about_text = """
🤖 *OLOV AI BOT*

🔥 *Versiya:* 1.0.0
⚡ *AI Motor:* Google Gemini 1.5 Flash
🌐 *Platforma:* Render.com
💻 *Kod:* Python + python-telegram-bot

*Yaratuvchi:* @your_username
*GitHub:* github.com/your/repo

_Bepul va cheksiz foydalaning!_ 🚀
    """
    await update.message.reply_text(about_text, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline tugmalar uchun"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_chat":
        await query.message.reply_text(
            "✅ Suhbat boshlandi! Menga istalgan savol yuboring 🔥"
        )
    elif query.data == "help":
        await help_command(query, context)
    elif query.data == "clear":
        user_id = query.from_user.id
        user_histories[user_id] = []
        await query.message.reply_text("🗑️ Tarix tozalandi!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha xabarlarni qabul qilish"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Yozilmoqda... ko'rsatish
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # Gemini dan javob olish
    response = await ask_gemini(user_id, user_message)
    
    # Javobni yuborish (4096 belgidan uzun bo'lsa bo'lib yuborish)
    if len(response) > 4096:
        for i in range(0, len(response), 4096):
            await update.message.reply_text(response[i:i+4096])
    else:
        await update.message.reply_text(response)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Xatolarni ushlash"""
    logger.error(f"Xato: {context.error}")

# ===== FLASK WEB APP =====
@flask_app.route('/')
def index():
    return render_template('index.html')

@flask_app.route('/api/chat', methods=['POST'])
def web_chat():
    """Web app uchun chat API"""
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id', 'web_user')
    
    # Sinxron tarzda Gemini ga so'rov
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response = loop.run_until_complete(ask_gemini(session_id, message))
    loop.close()
    
    return jsonify({'response': response})

@flask_app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Olov AI is running! 🔥'})

def run_flask():
    """Flask ni alohida thread da ishlatish"""
    port = int(os.getenv("PORT", 5000))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# ===== ASOSIY FUNKSIYA =====
async def main():
    """Botni ishga tushirish"""
    # Flask ni background da ishlatish
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server ishga tushdi! 🌐")
    
    # Telegram botni ishga tushirish
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlarni qo'shish
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    logger.info("Olov AI Bot ishga tushdi! 🔥")
    
    # Botni polling rejimida ishga tushirish
    await app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    asyncio.run(main())
