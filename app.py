import os
import threading
from flask import Flask
import subprocess

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_bot():
    # Запускаем бота через python3
    subprocess.run(["python3", "bot.py"])

# Запускаем бота в фоновом потоке
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    # Render сам передает порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
