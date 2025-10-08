#!/usr/bin/env python3
"""
Скрипт для проверки статуса проекта
"""

import os
import sys
from beer_database import BeerDatabase
from bot_config import BotConfig

def check_project_status():
    """Проверяет статус всех компонентов проекта"""
    print("ПРОВЕРКА СТАТУСА ПРОЕКТА")
    print("=" * 40)
    
    # Проверка базы данных
    print("1. База данных:")
    try:
        db = BeerDatabase()
        beers = db.get_all_beers()
        print(f"   ✅ База данных работает")
        print(f"   📊 Найдено кранов: {len(beers)}")
        
        if beers:
            print("   📋 Краны:")
            for beer in beers:
                id_val, tap_pos, brewery, name, style, price, description, cost = beer
                print(f"      Кран {tap_pos}: {name} от {brewery} - {price:.0f}₽/л")
    except Exception as e:
        print(f"   ❌ Ошибка базы данных: {e}")
    
    print()
    
    # Проверка конфигурации бота
    print("2. Конфигурация Telegram бота:")
    try:
        if BotConfig.load_env_file():
            if BotConfig.validate_config():
                print("   ✅ Конфигурация корректна")
                admin_ids = BotConfig.get_admin_ids()
                print(f"   👥 Администраторы: {admin_ids}")
            else:
                print("   ❌ Конфигурация неполная")
                print("   💡 Запустите: python3 setup_bot.py")
        else:
            print("   ❌ Файл .env не найден")
            print("   💡 Запустите: python3 setup_bot.py")
    except Exception as e:
        print(f"   ❌ Ошибка конфигурации: {e}")
    
    print()
    
    # Проверка зависимостей
    print("3. Зависимости:")
    try:
        import telegram
        print(f"   ✅ python-telegram-bot: {telegram.__version__}")
    except ImportError:
        print("   ❌ python-telegram-bot не установлен")
        print("   💡 Запустите: pip install -r requirements.txt")
    
    try:
        import sqlite3
        print(f"   ✅ sqlite3: встроенная библиотека")
    except ImportError:
        print("   ❌ sqlite3 недоступен")
    
    print()
    
    # Инструкции по запуску
    print("4. Инструкции по запуску:")
    print("   📱 Консольное приложение:")
    print("      python3 main.py")
    print()
    print("   🤖 Telegram бот:")
    print("      python3 run_bot.py")
    print()
    print("   ⚙️ Настройка бота:")
    print("      python3 setup_bot.py")
    
    print()
    print("=" * 40)
    print("Проверка завершена!")

if __name__ == "__main__":
    check_project_status()
