#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрационный скрипт для показа возможностей Telegram бота
"""

from beer_database import BeerDatabase

def demo_bot_capabilities():
    """Демонстрация возможностей бота"""
    print("ДЕМОНСТРАЦИЯ ВОЗМОЖНОСТЕЙ TELEGRAM БОТА")
    print("="*60)
    
    # Создаем демо базу данных
    db = BeerDatabase("demo_beer_database.db")
    
    print("\n1. Заполняем базу данных примерами:")
    
    # Добавляем примеры пива
    demo_beers = [
        (1, "Балтика", "Балтика №7", "Лагер", 120.50),
        (2, "Heineken", "Heineken", "Лагер", 180.00),
        (3, "Guinness", "Guinness Draught", "Стаут", 220.75),
        (5, "Sierra Nevada", "Pale Ale", "IPA", 250.00),
        (8, "Carlsberg", "Carlsberg", "Лагер", 150.25)
    ]
    
    for tap, brewery, name, style, price in demo_beers:
        success = db.add_beer(tap, brewery, name, style, price)
        print(f"   Кран {tap}: {brewery} - {name}")
    
    print("\n2. Команды, которые будут доступны в Telegram боте:")
    
    print("\n   ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ:")
    print("   /start - приветствие и информация о правах")
    print("   /help - список всех команд")
    print("   /taps - показать все краны")
    print("   /find <номер> - найти пиво по номеру крана")
    
    print("\n   ДЛЯ АДМИНИСТРАТОРОВ:")
    print("   /admin - панель администратора с кнопками:")
    print("     Добавить пиво в кран")
    print("     Редактировать информацию о пиве")
    print("     Удалить пиво из крана")
    print("     Показать все краны")
    
    print("\n3. Текущие краны в базе данных:")
    db.display_all_beers()
    
    print("\n4. Примеры операций, доступных админам:")
    
    print("\n   Обновление цены в кране 1:")
    db.update_beer(1, price_per_liter=125.00)
    beer = db.get_beer_by_tap(1)
    if beer:
        print(f"     Новая цена: {beer[4]} ₽/л")
    
    print("\n   Обновление пивоварни в кране 3:")
    db.update_beer(3, brewery="Guinness Ltd")
    beer = db.get_beer_by_tap(3)
    if beer:
        print(f"     Новая пивоварня: {beer[1]}")
    
    print("\n5. Примеры сообщений в Telegram:")
    
    print("\n   Команда /taps покажет:")
    beers = db.get_all_beers()
    message = "**ТЕКУЩИЕ КРАНЫ:**\n\n"
    for beer in beers[:3]:  # Показываем первые 3
        tap_pos, brewery, name, style, price = beer
        message += f"**Кран {tap_pos}:**\n"
        message += f"Пивоварня: {brewery}\n"
        message += f"Название: {name}\n"
        message += f"Стиль: {style}\n"
        message += f"Цена: {price:.2f} руб/л\n\n"
    
    print(message)
    
    print("\n   Команда /find 2 покажет:")
    beer = db.get_beer_by_tap(2)
    if beer:
        tap_pos, brewery, name, style, price = beer
        find_message = f"**Кран {tap_pos}:**\n\n"
        find_message += f"**Пивоварня:** {brewery}\n"
        find_message += f"**Название:** {name}\n"
        find_message += f"**Стиль:** {style}\n"
        find_message += f"**Цена:** {price:.2f} руб/л"
        print(find_message)
    
    print("\n6. Для запуска бота:")
    print("   1. Получите токен у @BotFather")
    print("   2. Узнайте свой ID у @userinfobot")
    print("   3. Установите переменные окружения:")
    print("      export TELEGRAM_BOT_TOKEN='ваш_токен'")
    print("      export ADMIN_IDS='ваш_id'")
    print("   4. Запустите: python3 run_bot.py")
    
    print("\n7. Система прав:")
    print("   - Администраторы: полный доступ ко всем функциям")
    print("   - Пользователи: только просмотр информации")
    print("   - Автоматическое определение прав по ID пользователя")
    
    print("\n" + "="*60)
    print("Демонстрация завершена!")
    print("База данных сохранена в: demo_beer_database.db")
    print("Подробные инструкции: setup_instructions.md")
    
    # Очищаем демо базу данных
    import os
    if os.path.exists("demo_beer_database.db"):
        os.remove("demo_beer_database.db")

if __name__ == "__main__":
    demo_bot_capabilities()
