#!/usr/bin/env python3
"""
Основное приложение для управления пивными кранами
"""

from beer_database import BeerDatabase
import sys

def print_menu():
    """Выводит меню приложения"""
    print("\n" + "="*50)
    print("УПРАВЛЕНИЕ ПИВНЫМИ КРАНАМИ")
    print("="*50)
    print("1. Показать все краны")
    print("2. Найти пиво по номеру крана")
    print("3. Добавить новое пиво")
    print("4. Обновить информацию о пиве")
    print("5. Удалить пиво из крана")
    print("6. Показать статистику")
    print("0. Выход")
    print("="*50)

def show_all_taps(db: BeerDatabase):
    """Показывает все краны"""
    beers = db.get_all_beers()
    
    if not beers:
        print("Краны пусты")
        return
    
    print(f"\nНайдено кранов: {len(beers)}")
    print("-" * 80)
    
    for beer in beers:
        id_val, tap_pos, brewery, name, style, price, description, cost = beer
        print(f"Кран {tap_pos}: {name} от {brewery}")
        print(f"  Сорт: {style}")
        print(f"  Цена: {price:.2f} руб/л")
        print(f"  Стоимость: {cost:.2f} руб")
        if description:
            print(f"  Описание: {description}")
        print("-" * 80)

def find_beer_by_tap(db: BeerDatabase):
    """Находит пиво по номеру крана"""
    try:
        tap_position = int(input("Введите номер крана: "))
        beer = db.get_beer_by_tap(tap_position)
        
        if beer:
            id_val, tap_pos, brewery, name, style, price, description, cost = beer
            print(f"\nКран {tap_pos}: {name} от {brewery}")
            print(f"Сорт: {style}")
            print(f"Цена: {price:.2f} руб/л")
            print(f"Стоимость: {cost:.2f} руб")
            if description:
                print(f"Описание: {description}")
        else:
            print(f"Кран {tap_position} не найден")
            
    except ValueError:
        print("Ошибка: Введите корректный номер крана")

def add_new_beer(db: BeerDatabase):
    """Добавляет новое пиво"""
    try:
        tap_position = int(input("Номер крана: "))
        brewery = input("Пивоварня: ")
        name = input("Название пива: ")
        style = input("Сорт пива: ")
        price_per_liter = float(input("Цена за литр: "))
        description = input("Описание (необязательно): ")
        cost = float(input("Стоимость: "))
        
        if db.add_beer(tap_position, brewery, name, style, price_per_liter, description, cost):
            print("Пиво успешно добавлено!")
        else:
            print("Ошибка при добавлении пива")
            
    except ValueError:
        print("Ошибка: Введите корректные данные")
    except Exception as e:
        print(f"Ошибка: {e}")

def update_beer(db: BeerDatabase):
    """Обновляет информацию о пиве"""
    try:
        tap_position = int(input("Номер крана для обновления: "))
        
        # Проверяем, существует ли кран
        beer = db.get_beer_by_tap(tap_position)
        if not beer:
            print(f"Кран {tap_position} не найден")
            return
        
        print(f"\nТекущая информация о кране {tap_position}:")
        id_val, tap_pos, brewery, name, style, price, description, cost = beer
        print(f"Пивоварня: {brewery}")
        print(f"Название: {name}")
        print(f"Сорт: {style}")
        print(f"Цена: {price:.2f} руб/л")
        print(f"Описание: {description}")
        print(f"Стоимость: {cost:.2f} руб")
        
        print("\nВведите новые данные (оставьте пустым для сохранения текущего значения):")
        
        new_brewery = input(f"Пивоварня [{brewery}]: ").strip()
        new_name = input(f"Название [{name}]: ").strip()
        new_style = input(f"Сорт [{style}]: ").strip()
        new_price_input = input(f"Цена за литр [{price:.2f}]: ").strip()
        new_description = input(f"Описание [{description}]: ").strip()
        new_cost_input = input(f"Стоимость [{cost:.2f}]: ").strip()
        
        # Обрабатываем введенные данные
        update_data = {}
        
        if new_brewery:
            update_data['brewery'] = new_brewery
        if new_name:
            update_data['name'] = new_name
        if new_style:
            update_data['style'] = new_style
        if new_price_input:
            update_data['price_per_liter'] = float(new_price_input)
        if new_description:
            update_data['description'] = new_description
        if new_cost_input:
            update_data['cost'] = float(new_cost_input)
        
        if db.update_beer(tap_position, **update_data):
            print("Информация о пиве успешно обновлена!")
        else:
            print("Ошибка при обновлении пива")
            
    except ValueError:
        print("Ошибка: Введите корректные данные")
    except Exception as e:
        print(f"Ошибка: {e}")

def delete_beer(db: BeerDatabase):
    """Удаляет пиво из крана"""
    try:
        tap_position = int(input("Номер крана для удаления: "))
        
        # Показываем информацию о кране перед удалением
        beer = db.get_beer_by_tap(tap_position)
        if beer:
            id_val, tap_pos, brewery, name, style, price, description, cost = beer
            print(f"\nИнформация о кране {tap_position}:")
            print(f"Пивоварня: {brewery}")
            print(f"Название: {name}")
            print(f"Сорт: {style}")
            print(f"Цена: {price:.2f} руб/л")
            
            confirm = input("\nВы уверены, что хотите удалить это пиво? (да/нет): ").lower()
            if confirm in ['да', 'yes', 'y']:
                if db.delete_beer(tap_position):
                    print("Пиво успешно удалено!")
                else:
                    print("Ошибка при удалении пива")
            else:
                print("Удаление отменено")
        else:
            print(f"Кран {tap_position} не найден")
            
    except ValueError:
        print("Ошибка: Введите корректный номер крана")
    except Exception as e:
        print(f"Ошибка: {e}")

def show_statistics(db: BeerDatabase):
    """Показывает статистику"""
    beers = db.get_all_beers()
    
    if not beers:
        print("Краны пусты")
        return
    
    print(f"\nСТАТИСТИКА")
    print("-" * 30)
    print(f"Общее количество кранов: {len(beers)}")
    
    # Статистика по сортам
    styles = {}
    breweries = {}
    total_price = 0
    total_cost = 0
    
    for beer in beers:
        id_val, tap_pos, brewery, name, style, price, description, cost = beer
        
        # Подсчет сортов
        if style in styles:
            styles[style] += 1
        else:
            styles[style] = 1
        
        # Подсчет пивоварен
        if brewery in breweries:
            breweries[brewery] += 1
        else:
            breweries[brewery] = 1
        
        total_price += price
        total_cost += cost
    
    print(f"Средняя цена за литр: {total_price / len(beers):.2f} руб")
    print(f"Средняя стоимость: {total_cost / len(beers):.2f} руб")
    
    print(f"\nСорта пива:")
    for style, count in sorted(styles.items()):
        print(f"  {style}: {count} кранов")
    
    print(f"\nПивоварни:")
    for brewery, count in sorted(breweries.items()):
        print(f"  {brewery}: {count} кранов")

def main():
    """Основная функция приложения"""
    print("Запуск приложения управления пивными кранами...")
    
    # Инициализация базы данных
    db = BeerDatabase()
    
    while True:
        print_menu()
        
        try:
            choice = input("Выберите действие: ").strip()
            
            if choice == "0":
                print("До свидания!")
                break
            elif choice == "1":
                show_all_taps(db)
            elif choice == "2":
                find_beer_by_tap(db)
            elif choice == "3":
                add_new_beer(db)
            elif choice == "4":
                update_beer(db)
            elif choice == "5":
                delete_beer(db)
            elif choice == "6":
                show_statistics(db)
            else:
                print("Неверный выбор. Попробуйте снова.")
                
        except KeyboardInterrupt:
            print("\n\nПрограмма прервана пользователем")
            break
        except Exception as e:
            print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main()
