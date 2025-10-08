#!/usr/bin/env python3
"""
Модуль для работы с базой данных пивных кранов
"""

import sqlite3
import os
from typing import List, Tuple, Optional

class BeerDatabase:
    """Класс для работы с базой данных пивных кранов"""
    
    def __init__(self, db_path: str = "beer_database.db"):
        """Инициализация подключения к базе данных
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу для пивных кранов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS beer_taps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tap_position INTEGER UNIQUE NOT NULL,
                brewery TEXT NOT NULL,
                name TEXT NOT NULL,
                style TEXT NOT NULL,
                price_per_liter REAL NOT NULL,
                description TEXT,
                cost_400ml REAL NOT NULL,
                cost_250ml REAL NOT NULL,
                untappd_url TEXT,
                abv REAL,
                ibu REAL
            )
        ''')
        
        # Создаем индекс для быстрого поиска по номеру крана
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tap_position 
            ON beer_taps(tap_position)
        ''')
        
        # Создаем таблицу истории пива для быстрого добавления
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS beer_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brewery TEXT NOT NULL,
                name TEXT NOT NULL,
                style TEXT NOT NULL,
                description TEXT,
                untappd_url TEXT,
                abv REAL,
                ibu REAL,
                added_count INTEGER DEFAULT 1,
                last_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем индекс для поиска по названию пива
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_beer_name 
            ON beer_history(name)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_beer(self, tap_position: int, brewery: str, name: str, 
                 style: str, price_per_liter: float, description: str = "", 
                 cost_400ml: float = 0.0, cost_250ml: float = 0.0, untappd_url: str = "",
                 abv: float = None, ibu: float = None) -> bool:
        """Добавляет новое пиво в кран
        
        Args:
            tap_position: Номер позиции крана
            brewery: Название пивоварни
            name: Название пива
            style: Сорт пива
            price_per_liter: Цена за литр
            description: Описание пива
            cost_400ml: Стоимость за 400 мл
            cost_250ml: Стоимость за 250 мл
            untappd_url: Ссылка на страницу пива в Untappd
            abv: Содержание алкоголя в процентах
            ibu: Горечь пива (International Bitterness Units)
            
        Returns:
            True если успешно добавлено, False если ошибка
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO beer_taps (tap_position, brewery, name, style, 
                                     price_per_liter, description, cost_400ml, cost_250ml, 
                                     untappd_url, abv, ibu)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (tap_position, brewery, name, style, price_per_liter, description, 
                  cost_400ml, cost_250ml, untappd_url, abv, ibu))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.IntegrityError:
            print(f"Ошибка: Кран {tap_position} уже существует")
            return False
        except Exception as e:
            print(f"Ошибка при добавлении пива: {e}")
            return False
    
    def get_beer_by_tap(self, tap_position: int) -> Optional[Tuple]:
        """Получает информацию о пиве по номеру крана
        
        Args:
            tap_position: Номер позиции крана
            
        Returns:
            Кортеж с данными о пиве или None если не найдено
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, tap_position, brewery, name, style, 
                       price_per_liter, description, cost_400ml, cost_250ml, untappd_url, abv, ibu
                FROM beer_taps WHERE tap_position = ?
            ''', (tap_position,))
            
            result = cursor.fetchone()
            conn.close()
            return result
            
        except Exception as e:
            print(f"Ошибка при получении пива: {e}")
            return None
    
    def get_all_beers(self) -> List[Tuple]:
        """Получает все пива из базы данных
        
        Returns:
            Список кортежей с данными о всех пивах
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, tap_position, brewery, name, style, 
                       price_per_liter, description, cost_400ml, cost_250ml, untappd_url, abv, ibu
                FROM beer_taps ORDER BY tap_position
            ''')
            
            results = cursor.fetchall()
            conn.close()
            return results
            
        except Exception as e:
            print(f"Ошибка при получении всех пив: {e}")
            return []
    
    def update_beer(self, tap_position: int, brewery: str = None, name: str = None,
                   style: str = None, price_per_liter: float = None, 
                   description: str = None, cost_400ml: float = None, cost_250ml: float = None) -> bool:
        """Обновляет информацию о пиве
        
        Args:
            tap_position: Номер позиции крана
            brewery: Название пивоварни
            name: Название пива
            style: Сорт пива
            price_per_liter: Цена за литр
            description: Описание пива
            cost_400ml: Стоимость за 400 мл
            cost_250ml: Стоимость за 250 мл
            
        Returns:
            True если успешно обновлено, False если ошибка
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Формируем запрос обновления только для переданных полей
            update_fields = []
            values = []
            
            if brewery is not None:
                update_fields.append("brewery = ?")
                values.append(brewery)
            if name is not None:
                update_fields.append("name = ?")
                values.append(name)
            if style is not None:
                update_fields.append("style = ?")
                values.append(style)
            if price_per_liter is not None:
                update_fields.append("price_per_liter = ?")
                values.append(price_per_liter)
            if description is not None:
                update_fields.append("description = ?")
                values.append(description)
            if cost_400ml is not None:
                update_fields.append("cost_400ml = ?")
                values.append(cost_400ml)
            if cost_250ml is not None:
                update_fields.append("cost_250ml = ?")
                values.append(cost_250ml)
            
            if not update_fields:
                print("Нет полей для обновления")
                return False
            
            values.append(tap_position)
            
            query = f"UPDATE beer_taps SET {', '.join(update_fields)} WHERE tap_position = ?"
            cursor.execute(query, values)
            
            if cursor.rowcount == 0:
                print(f"Кран {tap_position} не найден")
                return False
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Ошибка при обновлении пива: {e}")
            return False
    
    def update_beer_field(self, tap_position: int, field: str, value) -> bool:
        """Обновляет конкретное поле пива
        
        Args:
            tap_position: Номер позиции крана
            field: Название поля для обновления
            value: Новое значение
            
        Returns:
            True если успешно обновлено, False если ошибка
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Маппинг полей на названия колонок в БД
            field_mapping = {
                'brewery': 'brewery',
                'name': 'name', 
                'style': 'style',
                'price': 'price_per_liter',
                'cost_400ml': 'cost_400ml',
                'cost_250ml': 'cost_250ml',
                'description': 'description',
                'untappd_url': 'untappd_url',
                'abv': 'abv',
                'ibu': 'ibu'
            }
            
            if field not in field_mapping:
                print(f"Неверное поле: {field}")
                return False
            
            db_field = field_mapping[field]
            query = f"UPDATE beer_taps SET {db_field} = ? WHERE tap_position = ?"
            cursor.execute(query, (value, tap_position))
            
            if cursor.rowcount == 0:
                print(f"Кран {tap_position} не найден")
                return False
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Ошибка при обновлении поля {field}: {e}")
            return False
    
    def delete_beer(self, tap_position: int) -> bool:
        """Удаляет пиво из крана
        
        Args:
            tap_position: Номер позиции крана
            
        Returns:
            True если успешно удалено, False если ошибка
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM beer_taps WHERE tap_position = ?', (tap_position,))
            
            if cursor.rowcount == 0:
                print(f"Кран {tap_position} не найден")
                return False
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Ошибка при удалении пива: {e}")
            return False
    
    def get_tap_count(self) -> int:
        """Получает количество кранов в базе данных
        
        Returns:
            Количество кранов
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM beer_taps')
            count = cursor.fetchone()[0]
            conn.close()
            return count
            
        except Exception as e:
            print(f"Ошибка при подсчете кранов: {e}")
            return 0
    
    def save_to_history(self, brewery: str, name: str, style: str, 
                       description: str = "", untappd_url: str = "",
                       abv: float = None, ibu: float = None) -> bool:
        """Сохраняет пиво в историю или обновляет счетчик
        
        Args:
            brewery: Название пивоварни
            name: Название пива
            style: Стиль пива
            description: Описание
            untappd_url: Ссылка на Untappd
            abv: Процент алкоголя
            ibu: Горечь
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже такое пиво в истории
            cursor.execute('''
                SELECT id, added_count FROM beer_history 
                WHERE brewery = ? AND name = ?
            ''', (brewery, name))
            
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем счетчик и дату
                beer_id, count = existing
                cursor.execute('''
                    UPDATE beer_history 
                    SET added_count = ?, last_added = CURRENT_TIMESTAMP,
                        style = ?, description = ?, untappd_url = ?, abv = ?, ibu = ?
                    WHERE id = ?
                ''', (count + 1, style, description, untappd_url, abv, ibu, beer_id))
            else:
                # Добавляем новое пиво в историю
                cursor.execute('''
                    INSERT INTO beer_history 
                    (brewery, name, style, description, untappd_url, abv, ibu)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (brewery, name, style, description, untappd_url, abv, ibu))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Ошибка при сохранении в историю: {e}")
            return False
    
    def get_beer_history(self, limit: int = 20) -> List[Tuple]:
        """Получает историю пива, отсортированную по частоте использования
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список кортежей с данными из истории
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, brewery, name, style, description, 
                       untappd_url, abv, ibu, added_count, last_added
                FROM beer_history 
                ORDER BY added_count DESC, last_added DESC
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            return results
            
        except Exception as e:
            print(f"Ошибка при получении истории: {e}")
            return []
    
    def search_beer_history(self, search_term: str, limit: int = 10) -> List[Tuple]:
        """Поиск пива в истории по названию или пивоварне
        
        Args:
            search_term: Строка для поиска
            limit: Максимальное количество результатов
            
        Returns:
            Список кортежей с найденными пивами
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            search_pattern = f"%{search_term}%"
            cursor.execute('''
                SELECT id, brewery, name, style, description, 
                       untappd_url, abv, ibu, added_count, last_added
                FROM beer_history 
                WHERE name LIKE ? OR brewery LIKE ?
                ORDER BY added_count DESC, last_added DESC
                LIMIT ?
            ''', (search_pattern, search_pattern, limit))
            
            results = cursor.fetchall()
            conn.close()
            return results
            
        except Exception as e:
            print(f"Ошибка при поиске в истории: {e}")
            return []
    
    def get_beer_from_history(self, history_id: int) -> Optional[Tuple]:
        """Получает конкретное пиво из истории по ID
        
        Args:
            history_id: ID записи в истории
            
        Returns:
            Кортеж с данными или None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, brewery, name, style, description, 
                       untappd_url, abv, ibu, added_count, last_added
                FROM beer_history 
                WHERE id = ?
            ''', (history_id,))
            
            result = cursor.fetchone()
            conn.close()
            return result
            
        except Exception as e:
            print(f"Ошибка при получении пива из истории: {e}")
            return None
    
    def delete_from_history(self, history_id: int) -> bool:
        """Удаляет запись из истории пива
        
        Args:
            history_id: ID записи в истории
            
        Returns:
            True если успешно удалено, False если ошибка
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM beer_history WHERE id = ?', (history_id,))
            
            if cursor.rowcount == 0:
                print(f"Запись {history_id} не найдена в истории")
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Ошибка при удалении из истории: {e}")
            return False
    
    def clear_all_history(self) -> bool:
        """Очищает всю историю пива
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM beer_history')
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Ошибка при очистке истории: {e}")
            return False
