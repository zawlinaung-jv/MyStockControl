import os
import telebot
import schedule
import time
import threading
from inventory_skill import process_message, get_stock_report

# CRITICAL FOR RAILWAY: Token များကို Environment Variables မှ တိုက်ရိုက်ဖတ်စေခြင်း
# telegram_bot.py ထဲက အဟောင်းကို ဖျက်ပြီး ဒါနဲ့ အစားထိုးပါ-
BOT_TOKEN = "8977520767:AAGpWu7fIX8eeDFElKeb_v4XFpwR3auYqQk"
REPORT_CHAT_ID = "5313885539"  # ဥပမာ -100xxx သို့မဟုတ် အမှန်တကယ် ID

bot = telebot.TeleBot(BOT_TOKEN)

print("🚀 Railway Anti-Overflow Bot Engine Running...")

@bot.message_handler(func=lambda message: True)
def handle_telegram_message(message):
    user_text = message.text.strip()
    reply_output = process_message(user_text)
    
    if reply_output:
        if isinstance(reply_output, dict) and reply_output.get("type") == "MULTI_MSG":
            bot.send_message(message.chat.id, "👥 [ALL REGISTERED CUSTOMERS MASTERS REPORT]\nStreaming records...")
            for text_segment in reply_output["data"]:
                bot.send_message(message.chat.id, text_segment)
                time.sleep(0.5)
        else:
            bot.reply_to(message, reply_output)
    else:
        help_text = (
            "💡 Available Action Syntaxes -\n"
            "1️⃣ Register Customer: `/addcustomer [Customer_Name]`\n"
            "2️⃣ Balance Ledger Lookup: `/customer [Customer_Name]`\n"
            "3️⃣ All Customer Profiles: Send `all customer`\n"
            "4️⃣ Inbound Stock Entry: `/buy [Product] [Qty] [Cost] [Retail]`\n"
            "5️⃣ Record Sale: `[Customer_Name] [Product] [Qty] [Remark]`\n"
            "6️⃣ Report: Send `summary` or `report`"
        )
        bot.reply_to(message, help_text)

def send_automated_report():
    try: 
        if REPORT_CHAT_ID:
            bot.send_message(REPORT_CHAT_ID, get_stock_report())
    except Exception as e: 
        print(f"CRITICAL: Failed to broadcast report: {e}")

def run_schedule():
    schedule.every().day.at("01:30").do(send_automated_report)
    while True:
        schedule.run_pending()
        time.sleep(1)

if BOT_TOKEN:
    threading.Thread(target=run_schedule, daemon=True).start()
    bot.infinity_polling()
else:
    print("❌ ERROR: BOT_TOKEN variable is missing in Railway Settings!")