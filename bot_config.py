#!/usr/bin/env python3
"""
Модуль для работы с конфигурацией бота
"""

import os
from typing import List

class BotConfig:
    """Класс для управления конфигурацией бота"""
    
    @staticmethod
    def load_env_file(env_path: str = ".env") -> bool:
        """Загружает переменные окружения из .env файла
        
        Args:
            env_path: Путь к .env файлу
            
        Returns:
            True если файл загружен успешно
        """
        if not os.path.exists(env_path):
            return False
        
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            return True
        except Exception as e:
            print(f"Ошибка при загрузке .env файла: {e}")
            return False
    
    @staticmethod
    def save_env_file(env_path: str = ".env", **kwargs) -> bool:
        """Сохраняет переменные окружения в .env файл
        
        Args:
            env_path: Путь к .env файлу
            **kwargs: Переменные для сохранения
            
        Returns:
            True если файл сохранен успешно
        """
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                for key, value in kwargs.items():
                    f.write(f"{key}={value}\n")
            return True
        except Exception as e:
            print(f"Ошибка при сохранении .env файла: {e}")
            return False
    
    @staticmethod
    def validate_config() -> bool:
        """Проверяет корректность конфигурации
        
        Returns:
            True если конфигурация корректна
        """
        required_vars = ['TELEGRAM_BOT_TOKEN', 'ADMIN_IDS']
        
        for var in required_vars:
            if not os.getenv(var):
                print(f"Отсутствует переменная: {var}")
                return False
        
        # Проверяем формат ADMIN_IDS
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        try:
            admin_ids = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
            if not admin_ids:
                print("ADMIN_IDS не содержит корректных ID")
                return False
        except ValueError:
            print("ADMIN_IDS содержит некорректные значения")
            return False
        
        return True
    
    @staticmethod
    def get_admin_ids() -> List[int]:
        """Получает список ID администраторов
        
        Returns:
            Список ID администраторов
        """
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        return [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
    
    @staticmethod
    def print_config_status():
        """Выводит статус конфигурации"""
        print("СТАТУС КОНФИГУРАЦИИ")
        print("-" * 30)
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if token:
            print(f"TELEGRAM_BOT_TOKEN: {'*' * 10}...{token[-4:]}")
        else:
            print("TELEGRAM_BOT_TOKEN: НЕ УСТАНОВЛЕН")
        
        admin_ids = BotConfig.get_admin_ids()
        if admin_ids:
            print(f"ADMIN_IDS: {admin_ids}")
        else:
            print("ADMIN_IDS: НЕ УСТАНОВЛЕНЫ")
        
        print("-" * 30)
