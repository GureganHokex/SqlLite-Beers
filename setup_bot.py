#!/usr/bin/env python3
"""
Скрипт для быстрой настройки Telegram бота
"""

import os
from bot_config import BotConfig

def setup_bot():
    """Интерактивная настройка бота"""
    print("НАСТРОЙКА TELEGRAM БОТА")
    print("=" * 40)
    
    # Проверяем существующий .env файл
    if os.path.exists('.env'):
        print("Найден существующий .env файл")
        overwrite = input("Перезаписать? (да/нет): ").lower()
        if overwrite not in ['да', 'yes', 'y']:
            print("Настройка отменена")
            return
    
    print("\nДля получения токена бота:")
    print("1. Найдите @BotFather в Telegram")
    print("2. Отправьте команду /newbot")
    print("3. Следуйте инструкциям")
    print("4. Скопируйте полученный токен")
    
    token = input("\nВведите токен бота: ").strip()
    if not token:
        print("Токен не может быть пустым")
        return
    
    print("\nДля получения вашего Telegram ID:")
    print("1. Найдите @userinfobot в Telegram")
    print("2. Отправьте любое сообщение")
    print("3. Скопируйте ваш ID")
    
    admin_id = input("\nВведите ваш Telegram ID: ").strip()
    if not admin_id:
        print("ID не может быть пустым")
        return
    
    try:
        admin_id_int = int(admin_id)
    except ValueError:
        print("ID должен быть числом")
        return
    
    # Сохраняем конфигурацию
    if BotConfig.save_env_file(
        TELEGRAM_BOT_TOKEN=token,
        ADMIN_IDS=str(admin_id_int)
    ):
        print("\nКонфигурация сохранена успешно!")
        print("Файл .env создан")
        
        # Проверяем конфигурацию
        if BotConfig.load_env_file() and BotConfig.validate_config():
            print("Конфигурация корректна")
            BotConfig.print_config_status()
        else:
            print("Ошибка в конфигурации")
    else:
        print("Ошибка при сохранении конфигурации")

if __name__ == "__main__":
    setup_bot()
