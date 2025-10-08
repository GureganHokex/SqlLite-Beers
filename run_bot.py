#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота
"""

import os
import sys
from bot_config import BotConfig

def main():
    """Основная функция запуска бота"""
    print("TELEGRAM BOT ДЛЯ УПРАВЛЕНИЯ ПИВНЫМИ КРАНАМИ")
    print("=" * 50)
    
    # Загружаем конфигурацию из .env файла
    if not BotConfig.load_env_file():
        print("Файл .env не найден")
        print("Запустите: python3 setup_bot.py для настройки")
        return 1
    
    # Проверяем конфигурацию
    if not BotConfig.validate_config():
        print("Конфигурация неполная")
        print("Запустите: python3 setup_bot.py для настройки")
        return 1
    
    # Получаем токен из переменной окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Ошибка: Не установлен TELEGRAM_BOT_TOKEN")
        print("Запустите: python3 setup_bot.py для настройки")
        return 1
    
    # ID администраторов
    admin_ids = BotConfig.get_admin_ids()
    if not admin_ids:
        print("Ошибка: Не установлены ADMIN_IDS")
        print("Запустите: python3 setup_bot.py для настройки")
        return 1
    
    try:
        # Импортируем и запускаем бота
        from telegram_bot import BeerBot
        
        print("Конфигурация загружена успешно")
        print("Запуск бота...")
        
        bot = BeerBot(token, admin_ids)
        bot.run()
        
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
