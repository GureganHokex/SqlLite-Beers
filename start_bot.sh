#!/bin/bash

# Скрипт для запуска Telegram бота управления пивными кранами

export TELEGRAM_BOT_TOKEN="8202411460:AAGGDZmBFVKfZMAjVmXs1Ywl9dhYL4D7wpg"
export ADMIN_IDS="721327256,372800870"

echo "Запуск бота с настроенными переменными окружения..."
python3 run_bot.py
