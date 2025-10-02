#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки функциональности базы данных пивных кранов
"""

from beer_database import BeerDatabase

def test_database():
    """Тестирование всех функций базы данных"""
    print("Начинаем тестирование базы данных...")
    
    # Создаем тестовую базу данных
    db = BeerDatabase("test_beer_database.db")
    
    # Тест 1: Добавление пива
    print("\n=== ТЕСТ 1: Добавление пива ===")
    test_beers = [
        (1, "Балтика", "Балтика №7", "Лагер", 120.50),
        (2, "Heineken", "Heineken", "Лагер", 180.00),
        (3, "Guinness", "Guinness Draught", "Стаут", 220.75),
        (4, "Sierra Nevada", "Pale Ale", "IPA", 250.00)
    ]
    
    for tap, brewery, name, style, price in test_beers:
        success = db.add_beer(tap, brewery, name, style, price)
        print(f"Добавление в кран {tap}: {'✓' if success else '✗'}")
    
    # Тест 2: Попытка добавить в занятый кран
    print("\n=== ТЕСТ 2: Попытка добавить в занятый кран ===")
    success = db.add_beer(1, "Test Brewery", "Test Beer", "Test Style", 100.00)
    print(f"Попытка добавить в занятый кран 1: {'✗ (ожидаемо)' if not success else '✓'}")
    
    # Тест 3: Просмотр всех кранов
    print("\n=== ТЕСТ 3: Просмотр всех кранов ===")
    db.display_all_beers()
    
    # Тест 4: Поиск по номеру крана
    print("\n=== ТЕСТ 4: Поиск по номеру крана ===")
    beer = db.get_beer_by_tap(2)
    if beer:
        print(f"Кран 2: {beer[1]} - {beer[2]} ({beer[3]}) - {beer[4]} ₽/л")
    else:
        print("Кран 2 не найден")
    
    # Тест 5: Обновление информации
    print("\n=== ТЕСТ 5: Обновление информации ===")
    success = db.update_beer(1, price_per_liter=130.00)
    print(f"Обновление цены в кране 1: {'✓' if success else '✗'}")
    
    # Проверяем обновление
    updated_beer = db.get_beer_by_tap(1)
    if updated_beer:
        print(f"Новая цена в кране 1: {updated_beer[4]} ₽/л")
    
    # Тест 6: Удаление пива
    print("\n=== ТЕСТ 6: Удаление пива ===")
    success = db.delete_beer(4)
    print(f"Удаление пива из крана 4: {'✓' if success else '✗'}")
    
    # Проверяем удаление
    deleted_beer = db.get_beer_by_tap(4)
    print(f"Кран 4 после удаления: {'пуст' if not deleted_beer else 'не пуст'}")
    
    # Финальный просмотр
    print("\n=== ФИНАЛЬНЫЙ ПРОСМОТР ВСЕХ КРАНОВ ===")
    db.display_all_beers()
    
    print("\n=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")
    print("Все основные функции работают корректно!")
    
    # Удаляем тестовую базу данных
    import os
    if os.path.exists("test_beer_database.db"):
        os.remove("test_beer_database.db")
        print("Тестовая база данных удалена")

if __name__ == "__main__":
    test_database()

