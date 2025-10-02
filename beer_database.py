#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
База данных для пивных кранов
Содержит информацию о пиве: краны, пивоварня, название, стиль, цена за литр
"""

import sqlite3
import os
from typing import List, Tuple, Optional

class BeerDatabase:
    def __init__(self, db_path: str = "beer_database.db"):
        """Инициализация базы данных"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Создание таблицы если её нет"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS beer_taps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tap_position INTEGER UNIQUE NOT NULL,
                brewery TEXT NOT NULL,
                beer_name TEXT NOT NULL,
                beer_style TEXT NOT NULL,
                price_per_liter REAL NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        print("База данных инициализирована успешно!")
    
    def add_beer(self, tap_position: int, brewery: str, beer_name: str, beer_style: str, price_per_liter: float) -> bool:
        """Добавить новое пиво в кран"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO beer_taps (tap_position, brewery, beer_name, beer_style, price_per_liter)
                VALUES (?, ?, ?, ?, ?)
            ''', (tap_position, brewery, beer_name, beer_style, price_per_liter))
            
            conn.commit()
            conn.close()
            print(f"Пиво '{beer_name}' от пивоварни '{brewery}' добавлено в кран {tap_position}")
            return True
        except sqlite3.IntegrityError:
            print(f"Ошибка: Кран {tap_position} уже занят!")
            return False
        except Exception as e:
            print(f"Ошибка при добавлении пива: {e}")
            return False
    
    def get_all_beers(self) -> List[Tuple]:
        """Получить все записи о пиве"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tap_position, brewery, beer_name, beer_style, price_per_liter
            FROM beer_taps
            ORDER BY tap_position
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_beer_by_tap(self, tap_position: int) -> Optional[Tuple]:
        """Получить информацию о пиве по номеру крана"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tap_position, brewery, beer_name, beer_style, price_per_liter
            FROM beer_taps
            WHERE tap_position = ?
        ''', (tap_position,))
        
        result = cursor.fetchone()
        conn.close()
        return result
    
    def update_beer(self, tap_position: int, brewery: str = None, beer_name: str = None, 
                   beer_style: str = None, price_per_liter: float = None) -> bool:
        """Обновить информацию о пиве в кране"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Строим динамический запрос обновления
            update_fields = []
            values = []
            
            if brewery is not None:
                update_fields.append("brewery = ?")
                values.append(brewery)
            if beer_name is not None:
                update_fields.append("beer_name = ?")
                values.append(beer_name)
            if beer_style is not None:
                update_fields.append("beer_style = ?")
                values.append(beer_style)
            if price_per_liter is not None:
                update_fields.append("price_per_liter = ?")
                values.append(price_per_liter)
            
            if not update_fields:
                print("Нет данных для обновления")
                return False
            
            values.append(tap_position)
            
            query = f"UPDATE beer_taps SET {', '.join(update_fields)} WHERE tap_position = ?"
            cursor.execute(query, values)
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                print(f"Информация о кране {tap_position} обновлена")
                return True
            else:
                conn.close()
                print(f"Кран {tap_position} не найден")
                return False
                
        except Exception as e:
            print(f"Ошибка при обновлении: {e}")
            return False
    
    def delete_beer(self, tap_position: int) -> bool:
        """Удалить пиво из крана"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM beer_taps WHERE tap_position = ?', (tap_position,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                print(f"Пиво из крана {tap_position} удалено")
                return True
            else:
                conn.close()
                print(f"Кран {tap_position} не найден")
                return False
                
        except Exception as e:
            print(f"Ошибка при удалении: {e}")
            return False
    
    def display_all_beers(self):
        """Отобразить все краны в удобном формате"""
        beers = self.get_all_beers()
        
        if not beers:
            print("Краны пусты")
            return
        
        print("\n" + "="*80)
        print(f"{'Кран':<5} {'Пивоварня':<20} {'Название пива':<25} {'Стиль':<15} {'Цена/л':<10}")
        print("="*80)
        
        for beer in beers:
            tap_pos, brewery, name, style, price = beer
            print(f"{tap_pos:<5} {brewery:<20} {name:<25} {style:<15} {price:<10.2f} ₽")
        
        print("="*80)

def main():
    """Основная функция для интерактивной работы с базой данных"""
    db = BeerDatabase()
    
    while True:
        print("\n" + "="*50)
        print("УПРАВЛЕНИЕ ПИВНЫМИ КРАНАМИ")
        print("="*50)
        print("1. Показать все краны")
        print("2. Добавить пиво в кран")
        print("3. Обновить информацию о пиве")
        print("4. Удалить пиво из крана")
        print("5. Найти пиво по номеру крана")
        print("0. Выход")
        print("="*50)
        
        choice = input("Выберите действие (0-5): ").strip()
        
        if choice == "0":
            print("До свидания!")
            break
        elif choice == "1":
            db.display_all_beers()
        elif choice == "2":
            try:
                tap = int(input("Номер крана: "))
                brewery = input("Пивоварня: ")
                name = input("Название пива: ")
                style = input("Стиль пива: ")
                price = float(input("Цена за литр (₽): "))
                db.add_beer(tap, brewery, name, style, price)
            except ValueError:
                print("Ошибка: Неверный формат данных")
        elif choice == "3":
            try:
                tap = int(input("Номер крана для обновления: "))
                
                print("Введите новые данные (оставьте пустым для сохранения текущих):")
                brewery = input("Пивоварня: ").strip() or None
                name = input("Название пива: ").strip() or None
                style = input("Стиль пива: ").strip() or None
                price_input = input("Цена за литр (₽): ").strip()
                price = float(price_input) if price_input else None
                
                db.update_beer(tap, brewery, name, style, price)
            except ValueError:
                print("Ошибка: Неверный формат данных")
        elif choice == "4":
            try:
                tap = int(input("Номер крана для удаления: "))
                confirm = input(f"Вы уверены, что хотите удалить пиво из крана {tap}? (да/нет): ")
                if confirm.lower() in ['да', 'yes', 'y']:
                    db.delete_beer(tap)
            except ValueError:
                print("Ошибка: Неверный формат номера крана")
        elif choice == "5":
            try:
                tap = int(input("Номер крана: "))
                beer = db.get_beer_by_tap(tap)
                if beer:
                    print(f"\nКран {beer[0]}:")
                    print(f"  Пивоварня: {beer[1]}")
                    print(f"  Название: {beer[2]}")
                    print(f"  Стиль: {beer[3]}")
                    print(f"  Цена за литр: {beer[4]} ₽")
                else:
                    print(f"Кран {tap} пуст или не существует")
            except ValueError:
                print("Ошибка: Неверный формат номера крана")
        else:
            print("Неверный выбор, попробуйте снова")

if __name__ == "__main__":
    main()

