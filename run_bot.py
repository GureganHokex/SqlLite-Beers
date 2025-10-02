#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска Telegram бота управления пивными кранами
"""

import sys
import os
from config import Config, ENVIRONMENT_SETUP
from telegram_bot import BeerBot

def setup_environment():
    """Показ инструкций по настройке окружения"""
    print("НАСТРОЙКА TELEGRAM БОТА")
    print("="*50)
    print(ENVIRONMENT_SETUP)
    print("="*50)
    print("\nПосле настройки переменных окружения запустите:")
    print("python3 run_bot.py")
    print("\nИли установите переменные прямо в командной строке:")
    print('export TELEGRAM_BOT_TOKEN="ваш_токен"')
    print('export ADMIN_IDS="ваш_id"')
    print("python3 run_bot.py")

def main():
    """Основная функция запуска бота"""
    print("Запуск бота управления пивными кранами...")
    
    # Проверяем конфигурацию
    if not Config.validate():
        print("\n" + "="*50)
        setup_environment()
        sys.exit(1)
    
    # Показываем конфигурацию
    Config.print_config()
    
    try:
        # Создаем и запускаем бота
        bot = BeerBot(Config.TELEGRAM_BOT_TOKEN, Config.ADMIN_IDS)
        print("\nБот запущен! Нажмите Ctrl+C для остановки.")
        bot.run()
        
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"\nОшибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
