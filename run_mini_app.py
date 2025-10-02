#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска Telegram Mini App
"""

import os
import sys
from config import Config

def main():
    """Основная функция запуска Mini App"""
    print("Запуск Telegram Mini App для управления пивными кранами...")
    
    # Проверяем конфигурацию
    if not Config.validate():
        print("\n" + "="*50)
        print("ОШИБКА КОНФИГУРАЦИИ")
        print("="*50)
        print("Установите переменные окружения:")
        print("export TELEGRAM_BOT_TOKEN='ваш_токен'")
        print("export ADMIN_IDS='ваш_id'")
        print("export FLASK_SECRET_KEY='секретный_ключ'")
        print("="*50)
        sys.exit(1)
    
    # Показываем конфигурацию
    Config.print_config()
    
    # Устанавливаем переменные для Flask
    os.environ['FLASK_APP'] = 'mini_app.py'
    os.environ['FLASK_DEBUG'] = 'True'
    
    try:
        # Импортируем и запускаем приложение
        from mini_app import app
        
        port = int(os.getenv('PORT', 5000))
        host = os.getenv('HOST', '0.0.0.0')
        debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
        
        print(f"\nMini App будет доступен по адресу:")
        print(f"http://localhost:{port}")
        print(f"http://{host}:{port}")
        print(f"\nОтладка: {debug}")
        print("\nДля остановки нажмите Ctrl+C")
        
        app.run(host=host, port=port, debug=debug)
        
    except KeyboardInterrupt:
        print("\nMini App остановлен пользователем")
    except Exception as e:
        print(f"\nОшибка при запуске Mini App: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
