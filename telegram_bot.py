import os
import telebot
import schedule
import time
import threading
from inventory_skill import process_message, get_stock_report

# Railway Config Environment Variables (ရှာမတွေ့ပါက ပေးထားသော Token ကို Default သုံးမည်)
env_token = os.getenv("BOT_TOKEN")
BOT_TOKEN = env_token if env_token and env_token.strip() else "8977520767:AAGpWu7fIX8eeDFElKeb_v4XFpwR3auYqQk"

env_chat_id = os.getenv("REPORT_CHAT_ID")
REPORT_CHAT_ID = env_chat_id if env_chat_id and env_chat_id.strip() else "5313885539"

bot = telebot.TeleBot(BOT_TOKEN)

print(f"🚀 Railway Bot Engine Running Server-Side Mode...")

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
            f"💡 [AVAILABLE ACTION SYNTAXES]\n"
            f"----------------------------------\n"
            f"1️⃣ Register Customer: `/addcustomer [Customer_Name]`\n"
            f"2️⃣ Balance Ledger Lookup: `/customer [Customer_Name]`\n"
            f"3️⃣ All Customer Profiles: Send `all customer`\n"
            f"4️⃣ Inbound Stock Entry: `/buy [Product] [Qty] [Cost] [Retail]`\n"
            f"5️⃣ Record Sale: `[Customer_Name] [Product] [Qty] [Remark]`\n"
            f"6️⃣ Report Summary: Send `summary` or `report`\n"
            f"7️⃣ Update Stock Level: `/update_stock [Product] [NewQty]`\n"
            f"8️⃣ Delete Product: `/delete_product [Product]`\n"
            f"9️⃣ Change Bill Status: `/update_status [Customer_Name] | [Timestamp] | [PAID/UNPAID]`\n"
            f"🔟 Single Customer Wipe: `/clear_customer [Customer_Name]`\n"
            f"⚠️ Master Wiping: `clear all` | `clear stock` | `clear customer`"
        )
        bot.reply_to(message, help_text)

def send_automated_report():
    try: 
        if REPORT_CHAT_ID:
            bot.send_message(REPORT_CHAT_ID, get_stock_report())
    except Exception as e: 
        print(f"CRITICAL: Failed to broadcast report: {e}")

def run_schedule():
    # UTC 01:30 is Myanmar Standard Time (MMT) 08:00 AM
    schedule.every().day.at("01:30").do(send_automated_report)
    while True:
        schedule.run_pending()
        time.sleep(1)

if BOT_TOKEN:
    threading.Thread(target=run_schedule, daemon=True).start()
    bot.infinity_polling()
else:
    print("❌ ERROR: BOT_TOKEN variable is missing entirely!")