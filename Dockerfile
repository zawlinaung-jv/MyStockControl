FROM python:3.10-slim

WORKDIR /app

# Dependency များ သွင်းခြင်း
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ကုဒ်များအားလုံးကို Container ထဲ ကူးထည့်ခြင်း
COPY . .

# Bot ကို စတင် Run စေမည့် Command
CMD ["python", "telegram_bot.py"]