#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример использования базы данных пивных кранов
"""

from beer_database import BeerDatabase

def example_usage():
    """Пример использования базы данных"""
    print("=== ПРИМЕР ИСПОЛЬЗОВАНИЯ БАЗЫ ДАННЫХ ПИВНЫХ КРАНОВ ===\n")
    
    # Создаем экземпляр базы данных
    db = BeerDatabase("example_beer_database.db")
    
    # Добавляем несколько пив в краны
    print("1. Добавляем пиво в краны...")
    db.add_beer(1, "Балтика", "Балтика №7", "Лагер", 120.50)
    db.add_beer(2, "Heineken", "Heineken", "Лагер", 180.00)
    db.add_beer(3, "Guinness", "Guinness Draught", "Стаут", 220.75)
    db.add_beer(5, "Sierra Nevada", "Pale Ale", "IPA", 250.00)
    
    print("\n2. Просматриваем все краны:")
    db.display_all_beers()
    
    print("\n3. Ищем пиво в кране 2:")
    beer = db.get_beer_by_tap(2)
    if beer:
        print(f"   Найдено: {beer[1]} - {beer[2]} ({beer[3]}) за {beer[4]} ₽/л")
    
    print("\n4. Обновляем цену в кране 1:")
    db.update_beer(1, price_per_liter=125.00)
    
    print("\n5. Обновляем информацию о пивоварне в кране 3:")
    db.update_beer(3, brewery="Guinness Ltd")
    
    print("\n6. Финальный просмотр всех кранов:")
    db.display_all_beers()
    
    print("\n=== ПРИМЕР ЗАВЕРШЕН ===")
    print("База данных сохранена в файле 'example_beer_database.db'")
    print("Вы можете использовать интерактивный режим, запустив: python3 beer_database.py")

if __name__ == "__main__":
    example_usage()

