#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурационный файл для Telegram бота управления пивными кранами
"""

import os
from typing import List

class Config:
    """Класс конфигурации бота"""
    
    # Токен Telegram бота (получите у @BotFather)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # ID администраторов (можно узнать у @userinfobot)
    # Разделите ID запятыми, например: "123456789,987654321"
    ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '721327256, 372800870')
    ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(',') if x.strip()]
    
    # Путь к базе данных
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'beer_database.db')
    
    # Настройки логирования
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'beer_bot.log')
    
    @classmethod
    def validate(cls) -> bool:
        """Проверка корректности конфигурации"""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN не установлен")
        
        if not cls.ADMIN_IDS:
            errors.append("ADMIN_IDS не установлен или пуст")
        
        if errors:
            print("Ошибки конфигурации:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Вывод текущей конфигурации"""
        print("Конфигурация бота:")
        print(f"  Токен бота: {'OK' if cls.TELEGRAM_BOT_TOKEN else 'НЕ УСТАНОВЛЕН'}")
        print(f"  Админы: {len(cls.ADMIN_IDS)} пользователей")
        print(f"  База данных: {cls.DATABASE_PATH}")
        print(f"  Логирование: {cls.LOG_LEVEL}")

# Пример настройки переменных окружения
ENVIRONMENT_SETUP = """
# Настройка переменных окружения для запуска бота

# 1. Получите токен у @BotFather в Telegram
export TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

# 2. Узнайте свой ID у @userinfobot в Telegram
# Добавьте ID всех администраторов через запятую
export ADMIN_IDS="123456789,987654321"

# 3. (Опционально) Настройте путь к базе данных
export DATABASE_PATH="beer_database.db"

# 4. (Опционально) Настройте логирование
export LOG_LEVEL="INFO"
export LOG_FILE="beer_bot.log"

# Для постоянного сохранения переменных добавьте их в ~/.bashrc или ~/.zshrc
"""
