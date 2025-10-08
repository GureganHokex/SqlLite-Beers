#!/usr/bin/env python3
"""
Telegram бот для управления пивными кранами
"""

import os
import logging
import requests
import re
from urllib.parse import quote
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from beer_database import BeerDatabase

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
ADDING_TAP, ADDING_BREWERY, SELECTING_BEER_VARIANT, ADDING_NAME, ADDING_STYLE, ADDING_PRICE, ADDING_COST_400ML, ADDING_COST_250ML, ADDING_DESCRIPTION = range(9)
EDITING_TAP, EDITING_FIELD, EDITING_VALUE = range(3)
DELETING_TAP = 0


def search_untappd_beers(brewery: str, beer_name: str = "", style: str = "") -> list:
    """Ищет варианты пива на Untappd с разными уровнями поиска
    
    Args:
        brewery: Название пивоварни
        beer_name: Название пива (опционально)
        style: Стиль пива (опционально)
        
    Returns:
        Список словарей с найденными вариантами [{name, url, slug}]
    """
    try:
        # Формируем поисковый запрос в зависимости от заполненных полей
        if beer_name:
            query = f"{brewery} {beer_name}"
        elif style:
            query = f"{brewery} {style}"
        else:
            query = brewery
            
        search_url = f"https://untappd.com/search?q={quote(query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(search_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            # Ищем все ссылки на пиво в результатах (до 5 штук)
            matches = re.findall(r'href="(/b/([^"]+)/(\d+))"', response.text)
            results = []
            
            for match in matches[:5]:
                beer_path = match[0]
                beer_slug = match[1]
                
                # Форматируем название из slug
                beer_display = beer_slug.replace('-', ' ').title()
                
                results.append({
                    'url': f"https://untappd.com{beer_path}",
                    'name': beer_display,
                    'slug': beer_slug
                })
            
            return results
        
        return []
        
    except Exception as e:
        print(f"Ошибка при поиске на Untappd: {e}")
        return []


def get_beer_details(beer_url: str) -> dict:
    """Получает детальную информацию о пиве со страницы Untappd
    
    Args:
        beer_url: URL страницы пива на Untappd
        
    Returns:
        Словарь с данными {abv, ibu, description, style, name}
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(beer_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            html = response.text
            details = {}
            
            # Парсим ABV (алкоголь)
            abv_match = re.search(r'(\d+\.?\d*)\s*%\s*ABV', html, re.IGNORECASE)
            if abv_match:
                details['abv'] = float(abv_match.group(1))
            
            # Парсим IBU (горечь)
            ibu_match = re.search(r'(\d+\.?\d*)\s*IBU', html, re.IGNORECASE)
            if ibu_match:
                details['ibu'] = float(ibu_match.group(1))
            
            # Парсим описание
            desc_match = re.search(r'<div class="beer-descrption-read-less">([^<]+)</div>', html)
            if not desc_match:
                desc_match = re.search(r'<div class="beer-desc">([^<]+)</div>', html)
            if desc_match:
                description = desc_match.group(1).strip()
                # Очищаем от лишних пробелов
                description = re.sub(r'\s+', ' ', description)
                details['description'] = description
            
            # Парсим стиль
            style_match = re.search(r'<p class="style">([^<]+)</p>', html)
            if style_match:
                details['style'] = style_match.group(1).strip()
            
            # Парсим название пива
            name_match = re.search(r'<h1>([^<]+)</h1>', html)
            if name_match:
                details['name'] = name_match.group(1).strip()
            
            return details
        
        return {}
        
    except Exception as e:
        print(f"Ошибка при получении деталей пива: {e}")
        return {}


class BeerBot:
    """Класс Telegram бота для управления пивными кранами"""
    
    def __init__(self, token: str, admin_ids: list):
        """Инициализация бота
        
        Args:
            token: Токен Telegram бота
            admin_ids: Список ID администраторов
        """
        self.token = token
        self.admin_ids = admin_ids
        self.db = BeerDatabase()
        
        # Создаем приложение
        self.application = Application.builder().token(token).build()
        
        # Настраиваем обработчики
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("taps", self.show_taps_command))
        self.application.add_handler(CommandHandler("find", self.find_beer_command))
        
        # Админские команды
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        # Админские команды убраны - используйте интерфейс с кнопками
        # self.application.add_handler(CommandHandler("add", self.add_beer_command))
        # self.application.add_handler(CommandHandler("update", self.update_beer_command))
        # self.application.add_handler(CommandHandler("delete", self.delete_beer_command))
        
        # ConversationHandler для добавления пива (ДОЛЖЕН БЫТЬ ВЫШЕ общих обработчиков)
        add_beer_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_adding_beer, pattern="^select_tap_")],
            states={
                ADDING_BREWERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.adding_brewery)],
                SELECTING_BEER_VARIANT: [CallbackQueryHandler(self.beer_variant_selected)],
                ADDING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.adding_name)],
                ADDING_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.adding_style)],
                ADDING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.adding_price)],
                ADDING_COST_400ML: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.adding_cost_400ml)],
                ADDING_COST_250ML: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.adding_cost_250ml)],
                ADDING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.adding_description)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_operation)],
            per_message=False,
        )
        
        # ConversationHandler для редактирования пива (ДОЛЖЕН БЫТЬ ВЫШЕ общих обработчиков)
        edit_beer_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.button_callback, pattern="^edit_field_")],
            states={
                EDITING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.editing_value)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_operation)],
        )
        
        self.application.add_handler(add_beer_handler)
        self.application.add_handler(edit_beer_handler)
        
        # Обработчик кнопок (ДОЛЖЕН БЫТЬ НИЖЕ ConversationHandler)
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработчик текстовых сообщений от кнопок клавиатуры (ДОЛЖЕН БЫТЬ НИЖЕ ConversationHandler)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        
        # Обработчик неизвестных команд
        self.application.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если пользователь администратор
        """
        return user_id in self.admin_ids
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        is_admin = self.is_admin(user_id)
        
        # Создаем начальную клавиатуру только с "Пивные краны"
        keyboard = [
            [KeyboardButton("Пивные краны")]
        ]
        
        welcome_text = "ПИВНЫЕ КРАНЫ\n\n"
        welcome_text += "Добро пожаловать!\n"
        welcome_text += "Нажмите кнопку ниже для просмотра кранов:"
        
        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=False,
            input_field_placeholder="Выберите действие..."
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений от кнопок клавиатуры"""
        text = update.message.text
        user_id = update.effective_user.id
        is_admin = self.is_admin(user_id)
        
        # Кнопки меню всегда работают, независимо от состояния разговора
        menu_buttons = ["Краны", "Поиск", "Добавить", "Редактировать", "Удалить", "История"]
        
        # Обрабатываем кнопку "Пивные краны" отдельно
        if text == "Пивные краны":
            # Показываем краны
            await self.show_taps_command(update, context)
            
            # Меняем клавиатуру на полное меню для администраторов
            if is_admin:
                full_keyboard = [
                    [
                        KeyboardButton("Краны"),
                        KeyboardButton("Поиск")
                    ],
                    [
                        KeyboardButton("Добавить"),
                        KeyboardButton("Редактировать")
                    ],
                    [
                        KeyboardButton("Удалить"),
                        KeyboardButton("История")
                    ]
                ]
                reply_markup = ReplyKeyboardMarkup(full_keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    "Меню активировано!",
                    reply_markup=reply_markup
                )
            else:
                # Для обычных пользователей показываем только основные кнопки
                user_keyboard = [
                    [
                        KeyboardButton("Краны"),
                        KeyboardButton("Поиск")
                    ]
                ]
                reply_markup = ReplyKeyboardMarkup(user_keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    "Меню активировано!",
                    reply_markup=reply_markup
                )
            return
        
        if text in menu_buttons:
            # Обрабатываем кнопки меню
            if text == "Краны":
                await self.show_taps_command(update, context)
            elif text == "Поиск":
                await update.message.reply_text(
                    "Введите номер крана для поиска:\n"
                    "Например: 1, 2, 3..."
                )
                context.user_data['waiting_for_search'] = True
            elif text == "Добавить" and is_admin:
                await self.show_add_beer_menu(update, context)
            elif text == "Редактировать" and is_admin:
                await self.show_edit_beer_menu(update, context)
            elif text == "Удалить" and is_admin:
                await self.show_delete_beer_menu(update, context)
            elif text == "История" and is_admin:
                await self.history_command(update, context)
            return
        
        # Проверяем, не находимся ли мы в процессе ConversationHandler
        if context.user_data.get('conversation_state'):
            # Если находимся в процессе добавления/редактирования, не обрабатываем здесь
            return
        
        if context.user_data.get('waiting_for_search'):
            # Обработка поиска
            try:
                tap_position = int(text)
                beer = self.db.get_beer_by_tap(tap_position)
                
                if beer:
                    id_val, tap_pos, brewery, name, style, price, description, cost_400ml, cost_250ml, untappd_url, abv, ibu = beer
                    message = f"Кран {tap_pos}:\n"
                    message += f"Пивоварня: {brewery}\n"
                    message += f"Название: {name}\n"
                    message += f"Стиль: {style}\n"
                    
                    # Показываем ABV и IBU если есть
                    if abv:
                        message += f"Алкоголь: {abv}%\n"
                    if ibu:
                        message += f"Горечь: {ibu} IBU\n"
                    
                    # Ссылка на Untappd отдельной строкой
                    if untappd_url:
                        message += f"Untappd: {untappd_url}\n"
                    
                    # Показываем цену за литр только админам
                    if is_admin:
                        message += f"Цена: {price:.2f} руб/л\n"
                    
                    # Стоимость показываем всем
                    message += f"Стоимость 400мл: {cost_400ml:.2f} руб\n"
                    message += f"Стоимость 250мл: {cost_250ml:.2f} руб\n"
                    
                    if description:
                        message += f"Описание: {description}"
                    
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"Кран {tap_position} не найден")
                
                context.user_data['waiting_for_search'] = False
            except ValueError:
                await update.message.reply_text("Ошибка: Введите корректный номер крана")
        else:
            # Только если это не команда меню и не поиск
            if not any(text == cmd for cmd in ["Краны", "Поиск", "Добавить", "Редактировать", "Удалить", "История"]):
                await update.message.reply_text("Неизвестная команда. Используйте кнопки меню.")
    
    async def show_add_beer_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню добавления пива"""
        # Создаем кнопки для выбора крана
        keyboard = []
        for i in range(1, 22):  # Максимум 21 кран
            existing_beer = self.db.get_beer_by_tap(i)
            if not existing_beer:
                keyboard.append([InlineKeyboardButton(f"Кран {i}", callback_data=f"select_tap_{i}")])
        
        if not keyboard:
            await update.message.reply_text("Все краны заняты!")
            return
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "ДОБАВЛЕНИЕ ПИВА\n\n"
            "Выберите свободный кран:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_edit_beer_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню редактирования пива"""
        beers = self.db.get_all_beers()
        
        if not beers:
            await update.message.reply_text("Нет пива для редактирования!")
            return
        
        keyboard = []
        for beer in beers:
            id_val, tap_pos, brewery, name, style, price, description, cost_400ml, cost_250ml, untappd_url, abv, ibu = beer
            keyboard.append([InlineKeyboardButton(f"Кран {tap_pos}: {name}", callback_data=f"edit_tap_{tap_pos}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "РЕДАКТИРОВАНИЕ ПИВА\n\n"
            "Выберите кран для редактирования:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_delete_beer_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню удаления пива"""
        beers = self.db.get_all_beers()
        
        if not beers:
            await update.message.reply_text("Нет пива для удаления!")
            return
        
        keyboard = []
        for beer in beers:
            id_val, tap_pos, brewery, name, style, price, description, cost_400ml, cost_250ml, untappd_url, abv, ibu = beer
            keyboard.append([InlineKeyboardButton(f"Кран {tap_pos}: {name}", callback_data=f"delete_tap_{tap_pos}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "УДАЛЕНИЕ ПИВА\n\n"
            "Выберите кран для удаления:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        user_id = update.effective_user.id
        is_admin = self.is_admin(user_id)
        
        help_text = "Помощь по командам\n\n"
        help_text += "Общие команды:\n"
        help_text += "/taps - показать все краны\n"
        help_text += "/find <номер> - найти пиво по номеру крана\n\n"
        
        if is_admin:
            help_text += "Команды администратора:\n"
            help_text += "/admin - панель администратора\n\n"
            help_text += "В панели админа доступны:\n"
            help_text += "- Добавление нового пива в кран\n"
            help_text += "- Редактирование информации о пиве\n"
            help_text += "- Удаление пива из крана\n"
            help_text += "- Просмотр всех кранов\n"
        else:
            help_text += "Для получения прав администратора\n"
            help_text += "обратитесь к владельцу бота."
        
        await update.message.reply_text(help_text)
    
    async def show_taps_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все краны"""
        user_id = update.effective_user.id
        is_admin = self.is_admin(user_id)
        
        beers = self.db.get_all_beers()
        
        if not beers:
            await update.message.reply_text("Краны пусты")
            return
        
        message = "ТЕКУЩИЕ КРАНЫ:\n\n"
        
        for beer in beers:
            id_val, tap_pos, brewery, name, style, price, description, cost_400ml, cost_250ml, untappd_url, abv, ibu = beer
            message += f"Кран {tap_pos}:\n"
            message += f"Пивоварня: {brewery}\n"
            message += f"Название: {name}\n"
            message += f"Стиль: {style}\n"
            
            # Показываем ABV и IBU если есть
            if abv:
                message += f"Алкоголь: {abv}%\n"
            if ibu:
                message += f"Горечь: {ibu} IBU\n"
            
            # Ссылка на Untappd отдельной строкой
            if untappd_url:
                message += f"Untappd: {untappd_url}\n"
            
            # Показываем цену за литр только админам
            if is_admin:
                message += f"Цена: {price:.2f} руб/л\n"
            
            # Стоимость показываем всем
            message += f"Стоимость 400мл: {cost_400ml:.2f} руб\n"
            message += f"Стоимость 250мл: {cost_250ml:.2f} руб\n"
            
            if description:
                message += f"Описание: {description}\n"
            message += "\n"
        
        # Разбиваем длинные сообщения
        if len(message) > 4000:
            chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(message)
    
    async def find_beer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Найти пиво по номеру крана"""
        if not context.args:
            await update.message.reply_text("Использование: /find <номер_крана>")
            return
        
        try:
            tap_position = int(context.args[0])
            beer = self.db.get_beer_by_tap(tap_position)
            
            if beer:
                id_val, tap_pos, brewery, name, style, price, description, cost_400ml, cost_250ml, untappd_url, abv, ibu = beer
                user_id = update.effective_user.id
                is_admin = self.is_admin(user_id)
                
                message = f"Кран {tap_pos}:\n"
                message += f"Пивоварня: {brewery}\n"
                message += f"Название: {name}\n"
                message += f"Сорт: {style}\n"
                
                # Показываем ABV и IBU если есть
                if abv:
                    message += f"Алкоголь: {abv}%\n"
                if ibu:
                    message += f"Горечь: {ibu} IBU\n"
                
                # Ссылка на Untappd отдельной строкой
                if untappd_url:
                    message += f"Untappd: {untappd_url}\n"
                
                # Показываем цену за литр только админам
                if is_admin:
                    message += f"Цена: {price:.2f} руб/л\n"
                
                # Стоимость показываем всем
                message += f"Стоимость 400мл: {cost_400ml:.2f} руб\n"
                message += f"Стоимость 250мл: {cost_250ml:.2f} руб\n"
                
                if description:
                    message += f"Описание: {description}"
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"Кран {tap_position} не найден")
                
        except ValueError:
            await update.message.reply_text("Ошибка: Введите корректный номер крана")
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Панель администратора"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("У вас нет прав администратора")
            return
        
        # Админская панель
        keyboard = [
            [
                InlineKeyboardButton("Краны", callback_data="show_taps"),
                InlineKeyboardButton("Поиск", callback_data="search_beer")
            ],
            [
                InlineKeyboardButton("Добавить", callback_data="add_beer"),
                InlineKeyboardButton("Редактировать", callback_data="update_beer")
            ],
            [
                InlineKeyboardButton("Удалить", callback_data="delete_beer"),
                InlineKeyboardButton("История", callback_data="show_history")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "ПАНЕЛЬ АДМИНИСТРАТОРА\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Управление историей пива (только для администраторов)"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("У вас нет прав администратора")
            return
        
        # Получаем историю
        history = self.db.get_beer_history(50)
        
        if not history:
            await update.message.reply_text("История пуста")
            return
        
        # Создаем кнопки с историей
        keyboard = []
        for beer in history:
            beer_id, brewery, name, style, description, untappd_url, abv, ibu, added_count, last_added = beer
            button_text = f"{brewery} - {name} (×{added_count})"
            if len(button_text) > 60:
                button_text = button_text[:57] + "..."
            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"history_info_{beer_id}"
                )
            ])
        
        # Кнопка очистки всей истории
        keyboard.append([
            InlineKeyboardButton("🗑 Очистить всю историю", callback_data="clear_all_history")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "ИСТОРИЯ ПИВА\n\n"
            "Нажмите на пиво для просмотра или удаления:",
            reply_markup=reply_markup
        )
    
    async def add_beer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавление нового пива"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("У вас нет прав администратора")
            return
        
        if len(context.args) < 6:
            await update.message.reply_text(
                "Использование: /add <номер_крана> <пивоварня> <название> <сорт> <цена> <стоимость> [описание]\n\n"
                "Пример:\n"
                "/add 4 \"Новая пивоварня\" \"Экспериментальное IPA\" IPA 300 250 \"Хмельное пиво\""
            )
            return
        
        try:
            # Парсим аргументы с учетом кавычек
            import shlex
            full_text = update.message.text
            command_parts = full_text.split(' ', 1)
            if len(command_parts) < 2:
                raise ValueError("Недостаточно аргументов")
            
            args = shlex.split(command_parts[1])
            
            if len(args) < 7:
                raise ValueError("Недостаточно аргументов")
            
            tap_position = int(args[0])
            brewery = args[1]
            name = args[2]
            style = args[3]
            price = float(args[4])
            cost_400ml = float(args[5])
            cost_250ml = float(args[6])
            description = args[7] if len(args) > 7 else ""
            
            # Проверяем, не занят ли кран
            existing_beer = self.db.get_beer_by_tap(tap_position)
            if existing_beer:
                await update.message.reply_text(f"Кран {tap_position} уже занят пивом \"{existing_beer[3]}\"")
                return
            
            # Добавляем пиво
            success = self.db.add_beer(tap_position, brewery, name, style, price, description, cost_400ml, cost_250ml)
            
            if success:
                user_id = update.effective_user.id
                is_admin = self.is_admin(user_id)
                
                message = f"Пиво успешно добавлено!\n\n"
                message += f"Кран: {tap_position}\n"
                message += f"Пивоварня: {brewery}\n"
                message += f"Название: {name}\n"
                message += f"Сорт: {style}\n"
                
                # Показываем цену за литр только админам
                if is_admin:
                    message += f"Цена: {price:.2f} руб/л\n"
                
                # Стоимость показываем всем
                message += f"Стоимость 400мл: {cost_400ml:.2f} руб\n"
                message += f"Стоимость 250мл: {cost_250ml:.2f} руб\n"
                
                message += f"Описание: {description if description else 'Нет'}"
                
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("Ошибка при добавлении пива")
                
        except ValueError as e:
            await update.message.reply_text(f"Ошибка в данных: {e}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при добавлении: {e}")
    
    async def update_beer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Редактирование пива"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("У вас нет прав администратора")
            return
        
        if len(context.args) < 3:
            await update.message.reply_text(
                "Использование: /update <номер_крана> <поле> <новое_значение>\n\n"
                "Доступные поля: brewery, name, style, price, cost, description\n\n"
                "Примеры:\n"
                "/update 1 price 200\n"
                "/update 2 brewery \"Новая пивоварня\"\n"
                "/update 3 description \"Обновленное описание\""
            )
            return
        
        try:
            # Парсим аргументы с учетом кавычек
            import shlex
            full_text = update.message.text
            command_parts = full_text.split(' ', 1)
            if len(command_parts) < 2:
                raise ValueError("Недостаточно аргументов")
            
            args = shlex.split(command_parts[1])
            
            if len(args) < 3:
                raise ValueError("Недостаточно аргументов")
            
            tap_position = int(args[0])
            field = args[1].lower()
            new_value = args[2]
            
            # Проверяем существование пива
            existing_beer = self.db.get_beer_by_tap(tap_position)
            if not existing_beer:
                await update.message.reply_text(f"Кран {tap_position} не найден")
                return
            
            # Валидируем поле
            valid_fields = ['brewery', 'name', 'style', 'price', 'cost', 'description']
            if field not in valid_fields:
                await update.message.reply_text(f"Неверное поле. Доступные: {', '.join(valid_fields)}")
                return
            
            # Конвертируем числовые поля
            if field in ['price', 'cost']:
                try:
                    new_value = float(new_value)
                except ValueError:
                    await update.message.reply_text(f"Поле {field} должно быть числом")
                    return
            
            # Обновляем пиво
            success = self.db.update_beer_field(tap_position, field, new_value)
            
            if success:
                await update.message.reply_text(
                    f"Пиво в кране {tap_position} успешно обновлено!\n"
                    f"Поле '{field}' изменено на: {new_value}"
                )
            else:
                await update.message.reply_text("Ошибка при обновлении пива")
                
        except ValueError as e:
            await update.message.reply_text(f"Ошибка в данных: {e}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при обновлении: {e}")
    
    async def delete_beer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаление пива"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("У вас нет прав администратора")
            return
        
        if not context.args:
            await update.message.reply_text(
                "Использование: /delete <номер_крана>\n\n"
                "Пример:\n"
                "/delete 1"
            )
            return
        
        try:
            tap_position = int(context.args[0])
            
            # Проверяем существование пива
            existing_beer = self.db.get_beer_by_tap(tap_position)
            if not existing_beer:
                await update.message.reply_text(f"Кран {tap_position} не найден")
                return
            
            # Удаляем пиво
            success = self.db.delete_beer(tap_position)
            
            if success:
                await update.message.reply_text(f"Пиво из крана {tap_position} успешно удалено!")
            else:
                await update.message.reply_text("Ошибка при удалении пива")
                
        except ValueError as e:
            await update.message.reply_text(f"Ошибка в данных: {e}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при удалении: {e}")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        is_admin = self.is_admin(user_id)
        
        if not is_admin:
            await query.edit_message_text("У вас нет прав администратора")
            return
        
        data = query.data
        
        if data == "add_beer":
            # Показываем доступные краны
            beers = self.db.get_all_beers()
            occupied_taps = [beer[1] for beer in beers]  # tap_position
            
            available_taps = []
            for i in range(1, 22):  # Максимум 21 кран
                if i not in occupied_taps:
                    available_taps.append(str(i))
            
            if not available_taps:
                keyboard = [
                    [InlineKeyboardButton("Назад", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "ДОБАВЛЕНИЕ ПИВА\n\n"
                    "Все краны заняты!",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            # Создаем кнопки для выбора крана
            keyboard = []
            for i in range(0, len(available_taps), 3):
                row = []
                for j in range(3):
                    if i + j < len(available_taps):
                        tap_num = available_taps[i + j]
                        row.append(InlineKeyboardButton(f"Кран {tap_num}", callback_data=f"select_tap_{tap_num}"))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_main")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Проверяем наличие истории
            history = self.db.get_beer_history(1)
            history_text = ""
            if history:
                history_text = "\n\nМожно выбрать из ранее добавленных пив"
            
            await query.edit_message_text(
                f"ДОБАВЛЕНИЕ НОВОГО ПИВА{history_text}\n\n"
                "Выберите номер крана:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif data == "update_beer":
            # Показываем существующие краны
            beers = self.db.get_all_beers()
            
            if not beers:
                keyboard = [
                    [InlineKeyboardButton("Назад", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "РЕДАКТИРОВАНИЕ ПИВА\n\n"
                    "Краны пусты!",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            # Создаем кнопки для выбора крана
            keyboard = []
            for i in range(0, len(beers), 2):
                row = []
                for j in range(2):
                    if i + j < len(beers):
                        beer = beers[i + j]
                        id_val, tap_pos, brewery, name, style, price, description, cost_400ml, cost_250ml, untappd_url, abv, ibu = beer
                        row.append(InlineKeyboardButton(f"Кран {tap_pos}: {name}", callback_data=f"edit_tap_{tap_pos}"))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_main")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "РЕДАКТИРОВАНИЕ ПИВА\n\n"
                "Выберите кран для редактирования:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif data == "delete_beer":
            # Показываем существующие краны
            beers = self.db.get_all_beers()
            
            if not beers:
                keyboard = [
                    [InlineKeyboardButton("Назад", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "УДАЛЕНИЕ ПИВА\n\n"
                    "Краны пусты!",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            # Создаем кнопки для выбора крана
            keyboard = []
            for i in range(0, len(beers), 2):
                row = []
                for j in range(2):
                    if i + j < len(beers):
                        beer = beers[i + j]
                        id_val, tap_pos, brewery, name, style, price, description, cost_400ml, cost_250ml, untappd_url, abv, ibu = beer
                        row.append(InlineKeyboardButton(f"Кран {tap_pos}: {name}", callback_data=f"delete_tap_{tap_pos}"))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_main")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "УДАЛЕНИЕ ПИВА\n\n"
                "Выберите кран для удаления:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif data == "show_taps":
            user_id = query.from_user.id
            is_admin = self.is_admin(user_id)
            
            beers = self.db.get_all_beers()
            
            if not beers:
                keyboard = [
                    [InlineKeyboardButton("Назад", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "КРАНЫ\n\n"
                    "Краны пусты",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            # Отображение кранов
            message = "ТЕКУЩИЕ КРАНЫ\n\n"
            
            for beer in beers:
                id_val, tap_pos, brewery, name, style, price, description, cost_400ml, cost_250ml, untappd_url, abv, ibu = beer
                message += f"Кран {tap_pos}\n"
                message += f"Пивоварня: {brewery}\n"
                message += f"Название: {name}\n"
                message += f"Сорт: {style}\n"
                
                # Показываем цену за литр только админам
                if is_admin:
                    message += f"Цена: {price:.2f} руб/л\n"
                
                # Стоимость показываем всем
                message += f"Стоимость 400мл: {cost_400ml:.2f} руб\n"
                message += f"Стоимость 250мл: {cost_250ml:.2f} руб\n"
                
                if description:
                    message += f"Описание: {description}\n"
                message += "\n"
            
            keyboard = [
                [InlineKeyboardButton("Назад", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Обработчики для выбора кранов
        elif data.startswith("edit_tap_"):
            tap_num = data.split("_")[2]
            beer = self.db.get_beer_by_tap(int(tap_num))
            
            if not beer:
                await query.edit_message_text(f"Кран {tap_num} не найден!")
                return
            
            context.user_data['conversation_state'] = 'editing_beer'
            
            id_val, tap_pos, brewery, name, style, price, description, cost_400ml, cost_250ml, untappd_url, abv, ibu = beer
            
            # Создаем кнопки для выбора поля
            keyboard = [
                [InlineKeyboardButton("Пивоварня", callback_data=f"edit_field_{tap_num}_brewery")],
                [InlineKeyboardButton("Название", callback_data=f"edit_field_{tap_num}_name")],
                [InlineKeyboardButton("Сорт", callback_data=f"edit_field_{tap_num}_style")],
                [InlineKeyboardButton("Цена", callback_data=f"edit_field_{tap_num}_price")],
                [InlineKeyboardButton("Стоимость 400мл", callback_data=f"edit_field_{tap_num}_cost_400ml")],
                [InlineKeyboardButton("Стоимость 250мл", callback_data=f"edit_field_{tap_num}_cost_250ml")],
                [InlineKeyboardButton("Описание", callback_data=f"edit_field_{tap_num}_description")],
                [InlineKeyboardButton("Отмена", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = f"РЕДАКТИРОВАНИЕ КРАНА {tap_num}\n\n"
            message += f"Пивоварня: {brewery}\n"
            message += f"Название: {name}\n"
            message += f"Сорт: {style}\n"
            
            # Показываем цену за литр только админам
            if is_admin:
                message += f"Цена: {price:.2f} руб/л\n"
            
            # Стоимость показываем всем
            message += f"Стоимость 400мл: {cost_400ml:.2f} руб\n"
            message += f"Стоимость 250мл: {cost_250ml:.2f} руб\n"
            
            message += f"Описание: {description if description else 'Нет'}\n\n"
            message += "Выберите поле для редактирования:"
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif data == "show_history":
            # Показываем историю пива
            history = self.db.get_beer_history(50)
            
            if not history:
                keyboard = [
                    [InlineKeyboardButton("Назад", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "ИСТОРИЯ ПИВА\n\n"
                    "История пуста",
                    reply_markup=reply_markup
                )
                return
            
            # Создаем кнопки с историей
            keyboard = []
            for beer in history:
                beer_id, brewery, name, style, description, untappd_url, abv, ibu, added_count, last_added = beer
                button_text = f"{brewery} - {name} (×{added_count})"
                if len(button_text) > 60:
                    button_text = button_text[:57] + "..."
                keyboard.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"history_info_{beer_id}"
                    )
                ])
            
            # Кнопка очистки всей истории
            keyboard.append([
                InlineKeyboardButton("Очистить всю историю", callback_data="clear_all_history")
            ])
            keyboard.append([
                InlineKeyboardButton("Назад", callback_data="back_to_main")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "ИСТОРИЯ ПИВА\n\n"
                "Нажмите на пиво для просмотра или удаления:",
                reply_markup=reply_markup
            )
        
        elif data.startswith("history_info_"):
            # Показываем информацию о пиве из истории
            history_id = int(data.split("_")[2])
            beer = self.db.get_beer_from_history(history_id)
            
            if not beer:
                await query.edit_message_text("Пиво не найдено в истории!")
                return
            
            beer_id, brewery, name, style, description, untappd_url, abv, ibu, added_count, last_added = beer
            
            message = f"ИНФОРМАЦИЯ О ПИВЕ\n\n"
            message += f"Пивоварня: {brewery}\n"
            message += f"Название: {name}\n"
            message += f"Стиль: {style}\n"
            if abv:
                message += f"Алкоголь: {abv}%\n"
            if ibu:
                message += f"Горечь: {ibu} IBU\n"
            if untappd_url:
                message += f"Untappd: {untappd_url}\n"
            if description:
                message += f"Описание: {description}\n"
            message += f"\nДобавлялось: {added_count} раз(а)"
            
            keyboard = [
                [InlineKeyboardButton("Удалить из истории", callback_data=f"delete_history_{history_id}")],
                [InlineKeyboardButton("Назад", callback_data="back_to_history")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup)
        
        elif data.startswith("delete_history_"):
            # Удаление из истории
            history_id = int(data.split("_")[2])
            success = self.db.delete_from_history(history_id)
            
            if success:
                await query.answer("Удалено из истории")
                # Возвращаемся к списку истории
                history = self.db.get_beer_history(50)
                
                if not history:
                    await query.edit_message_text("История теперь пуста")
                    return
                
                keyboard = []
                for beer in history:
                    beer_id, brewery, name, style, description, untappd_url, abv, ibu, added_count, last_added = beer
                    button_text = f"{brewery} - {name} (×{added_count})"
                    if len(button_text) > 60:
                        button_text = button_text[:57] + "..."
                    keyboard.append([
                        InlineKeyboardButton(
                            button_text,
                            callback_data=f"history_info_{beer_id}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton("Очистить всю историю", callback_data="clear_all_history")
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "ИСТОРИЯ ПИВА\n\n"
                    "Нажмите на пиво для просмотра или удаления:",
                    reply_markup=reply_markup
                )
            else:
                await query.answer("Ошибка при удалении")
        
        elif data == "clear_all_history":
            # Подтверждение очистки всей истории
            keyboard = [
                [InlineKeyboardButton("Да, очистить", callback_data="confirm_clear_history")],
                [InlineKeyboardButton("Отмена", callback_data="back_to_history")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "ПОДТВЕРЖДЕНИЕ\n\n"
                "Вы уверены, что хотите очистить всю историю пива?\n"
                "Это действие нельзя отменить!",
                reply_markup=reply_markup
            )
        
        elif data == "confirm_clear_history":
            # Очистка всей истории
            success = self.db.clear_all_history()
            
            if success:
                await query.answer("История очищена")
                await query.edit_message_text("История пива полностью очищена")
            else:
                await query.answer("Ошибка при очистке")
        
        elif data == "back_to_history":
            # Возврат к списку истории
            history = self.db.get_beer_history(50)
            
            if not history:
                await query.edit_message_text("История пуста")
                return
            
            keyboard = []
            for beer in history:
                beer_id, brewery, name, style, description, untappd_url, abv, ibu, added_count, last_added = beer
                button_text = f"{brewery} - {name} (×{added_count})"
                if len(button_text) > 60:
                    button_text = button_text[:57] + "..."
                keyboard.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"history_info_{beer_id}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("Очистить всю историю", callback_data="clear_all_history")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "ИСТОРИЯ ПИВА\n\n"
                "Нажмите на пиво для просмотра или удаления:",
                reply_markup=reply_markup
            )
        
        elif data.startswith("delete_tap_"):
            tap_num = data.split("_")[2]
            beer = self.db.get_beer_by_tap(int(tap_num))
            
            if not beer:
                await query.edit_message_text(f"Кран {tap_num} не найден!")
                return
            
            context.user_data['conversation_state'] = 'deleting_beer'
            
            id_val, tap_pos, brewery, name, style, price, description, cost_400ml, cost_250ml, untappd_url, abv, ibu = beer
            
            # Кнопки подтверждения
            keyboard = [
                [InlineKeyboardButton("Да, удалить", callback_data=f"confirm_delete_{tap_num}")],
                [InlineKeyboardButton("Отмена", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = f"ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ\n\n"
            message += f"Кран {tap_num}: {name} от {brewery}\n"
            message += f"Сорт: {style}\n"
            
            # Показываем цену за литр только админам
            if is_admin:
                message += f"Цена: {price:.2f} руб/л\n"
            
            # Стоимость показываем всем
            message += f"Стоимость 400мл: {cost_400ml:.2f} руб\n"
            message += f"Стоимость 250мл: {cost_250ml:.2f} руб\n\n"
            
            message += "Вы уверены, что хотите удалить это пиво?"
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif data.startswith("confirm_delete_"):
            tap_num = data.split("_")[2]
            success = self.db.delete_beer(int(tap_num))
            
            if success:
                await query.edit_message_text(f"Пиво из крана {tap_num} успешно удалено!")
            else:
                await query.edit_message_text("Ошибка при удалении пива!")
        
        elif data.startswith("edit_field_"):
            # Формат: edit_field_<tap_num>_<field>
            # Поле может содержать подчеркивания (например cost_400ml)
            parts = data.split("_", 3)  # Разбиваем максимум на 4 части
            tap_num = parts[2]
            field = parts[3] if len(parts) > 3 else ""
            
            print(f"DEBUG: Редактирование - data={data}, tap_num={tap_num}, field={field}")
            
            context.user_data['editing_tap'] = int(tap_num)
            context.user_data['editing_field'] = field
            context.user_data['conversation_state'] = 'editing_field'
            
            field_names = {
                'brewery': 'пивоварню',
                'name': 'название',
                'style': 'сорт',
                'price': 'цену за литр',
                'cost_400ml': 'стоимость 400мл',
                'cost_250ml': 'стоимость 250мл',
                'description': 'описание'
            }
            
            await query.edit_message_text(
                f"РЕДАКТИРОВАНИЕ КРАНА {tap_num}\n\n"
                f"Введите новое значение для {field_names.get(field, field)}:"
            )
            return EDITING_VALUE
        
        elif data == "cancel":
            await query.edit_message_text("Операция отменена")
            context.user_data.clear()
        
        elif data == "back_to_main":
            # Возврат к главному меню
            user_id = query.from_user.id
            is_admin = self.is_admin(user_id)
            
            if is_admin:
                keyboard = [
                    [
                        InlineKeyboardButton("Краны", callback_data="show_taps"),
                        InlineKeyboardButton("Поиск", callback_data="search_beer")
                    ],
                    [
                        InlineKeyboardButton("Добавить", callback_data="add_beer"),
                        InlineKeyboardButton("Редактировать", callback_data="update_beer")
                    ],
                    [
                        InlineKeyboardButton("Удалить", callback_data="delete_beer")
                    ]
                ]
                message = "ПАНЕЛЬ АДМИНИСТРАТОРА\n\nВыберите действие:"
            else:
                keyboard = [
                    [
                        InlineKeyboardButton("Все краны", callback_data="show_taps"),
                        InlineKeyboardButton("Поиск", callback_data="search_beer")
                    ],
                    [
                        InlineKeyboardButton("Помощь", callback_data="help_info")
                    ]
                ]
                message = "ПИВНЫЕ КРАНЫ\n\nВыберите действие:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик неизвестных команд"""
        await update.message.reply_text("Неизвестная команда. Используйте /help для получения списка команд.")
    
    # Обработчики для многошаговых операций
    async def start_adding_beer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса добавления пива"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        tap_num = data.split("_")[2]
        context.user_data['adding_tap'] = int(tap_num)
        context.user_data['conversation_state'] = 'adding_beer'
        
        # Проверяем наличие истории пива
        history = self.db.get_beer_history(10)
        
        if history:
            # Показываем кнопки выбора: из истории или новое пиво
            keyboard = [
                [InlineKeyboardButton("📋 Из истории", callback_data=f"from_history_{tap_num}")],
                [InlineKeyboardButton("➕ Новое пиво", callback_data=f"new_beer_{tap_num}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"ДОБАВЛЕНИЕ ПИВА В КРАН {tap_num}\n\n"
                "Выберите вариант:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return SELECTING_BEER_VARIANT
        else:
            # Нет истории - сразу просим ввести пивоварню и название
            await query.edit_message_text(
                f"ДОБАВЛЕНИЕ ПИВА В КРАН {tap_num}\n\n"
                "Введите пивоварню и название пива через запятую:\n"
                "Например: Балтика, Балтика 9",
                parse_mode='Markdown'
            )
            return ADDING_BREWERY
    
    async def adding_brewery(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода пивоварни и названия"""
        user_input = update.message.text
        print(f"DEBUG: Получен ввод: {user_input}")
        
        # Проверяем, есть ли запятая (пивоварня, название)
        if ',' in user_input:
            parts = user_input.split(',', 1)
            brewery = parts[0].strip()
            beer_name = parts[1].strip()
            search_query = f"{brewery} {beer_name}"
            print(f"DEBUG: Пивоварня: {brewery}, Название: {beer_name}")
        else:
            # Если нет запятой, считаем что это только пивоварня
            brewery = user_input.strip()
            beer_name = ""
            search_query = brewery
            print(f"DEBUG: Только пивоварня: {brewery}")
        
        context.user_data['adding_brewery'] = brewery
        context.user_data['conversation_state'] = 'adding_beer'
        
        # Ищем варианты на Untappd
        await update.message.reply_text("Ищу на Untappd...")
        search_results = search_untappd_beers(search_query)
        
        if search_results:
            # Сохраняем варианты в context
            context.user_data['untappd_variants'] = search_results
            
            # Создаем кнопки с вариантами
            keyboard = []
            for idx, result in enumerate(search_results):
                keyboard.append([
                    InlineKeyboardButton(
                        f"{result['name']}", 
                        callback_data=f"select_beer_{idx}"
                    )
                ])
            
            # Добавляем кнопку "Ввести вручную"
            keyboard.append([
                InlineKeyboardButton(
                    "Не нашел, ввести название вручную", 
                    callback_data="manual_input_name"
                )
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Найдено {len(search_results)} вариантов:\n\n"
                "Выберите пиво или введите название вручную:",
                reply_markup=reply_markup
            )
            
            return SELECTING_BEER_VARIANT
        else:
            # Не нашли - сразу просим ввести название
            await update.message.reply_text(
                "Не найдено на Untappd\n\n"
                "Введите название пива:"
            )
            return ADDING_NAME
    
    async def beer_variant_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора варианта пива из найденных на Untappd или из истории"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Обработка выбора "из истории"
        if data.startswith("from_history_"):
            tap_num = data.split("_")[2]
            context.user_data['adding_tap'] = int(tap_num)
            
            # Получаем историю пива
            history = self.db.get_beer_history(20)
            
            if not history:
                await query.edit_message_text(
                    "История пуста\n\n"
                    "Введите пивоварню и название пива через запятую:\n"
                    "Например: Балтика, Балтика 9"
                )
                return ADDING_BREWERY
            
            # Создаем кнопки с историей
            keyboard = []
            for beer in history:
                beer_id, brewery, name, style, description, untappd_url, abv, ibu, added_count, last_added = beer
                # Показываем пивоварню и название
                button_text = f"{brewery} - {name}"
                if len(button_text) > 60:
                    button_text = button_text[:57] + "..."
                keyboard.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"history_beer_{beer_id}"
                    )
                ])
            
            # Кнопка "Назад к новому пиву"
            keyboard.append([
                InlineKeyboardButton("⬅️ Назад", callback_data=f"new_beer_{tap_num}")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"ВЫБОР ПИВА ИЗ ИСТОРИИ\n\n"
                "Выберите пиво:",
                reply_markup=reply_markup
            )
            return SELECTING_BEER_VARIANT
        
        # Обработка выбора "новое пиво"
        elif data.startswith("new_beer_"):
            tap_num = data.split("_")[2]
            context.user_data['adding_tap'] = int(tap_num)
            
            await query.edit_message_text(
                f"ДОБАВЛЕНИЕ НОВОГО ПИВА В КРАН {tap_num}\n\n"
                "Введите пивоварню и название пива через запятую:\n"
                "Например: Балтика, Балтика 9"
            )
            return ADDING_BREWERY
        
        # Обработка выбора пива из истории
        elif data.startswith("history_beer_"):
            beer_id = int(data.split("_")[2])
            beer = self.db.get_beer_from_history(beer_id)
            
            if not beer:
                await query.edit_message_text("Ошибка: пиво не найдено в истории")
                return ConversationHandler.END
            
            # Распаковываем данные из истории
            _, brewery, name, style, description, untappd_url, abv, ibu, _, _ = beer
            
            # Сохраняем данные в context
            context.user_data['adding_brewery'] = brewery
            context.user_data['adding_name'] = name
            context.user_data['adding_style'] = style
            context.user_data['beer_description'] = description or ""
            context.user_data['untappd_url'] = untappd_url or ""
            context.user_data['beer_abv'] = abv
            context.user_data['beer_ibu'] = ibu
            
            # Показываем информацию и просим ввести цену
            info_message = f"Выбрано из истории:\n\n"
            info_message += f"Пивоварня: {brewery}\n"
            info_message += f"Название: {name}\n"
            info_message += f"Стиль: {style}\n"
            if abv:
                info_message += f"Алкоголь: {abv}%\n"
            if ibu:
                info_message += f"Горечь: {ibu} IBU\n"
            info_message += f"\nВведите цену за литр (в рублях):"
            
            await query.edit_message_text(info_message)
            return ADDING_PRICE
        
        # Обработка ручного ввода названия
        if data == "manual_input_name":
            # Пользователь хочет ввести название вручную
            await query.edit_message_text("Введите название пива:")
            return ADDING_NAME
        
        elif data.startswith("select_beer_"):
            # Пользователь выбрал один из вариантов
            idx = int(data.split("_")[2])
            selected_beer = context.user_data['untappd_variants'][idx]
            
            await query.edit_message_text(
                f"Выбрано: {selected_beer['name']}\n\n"
                "Получаю детали с Untappd..."
            )
            
            # Получаем полную информацию о пиве
            beer_details = get_beer_details(selected_beer['url'])
            
            if beer_details:
                # Сохраняем все данные
                context.user_data['adding_name'] = beer_details.get('name', selected_beer['name'])
                context.user_data['adding_style'] = beer_details.get('style', '')
                context.user_data['beer_abv'] = beer_details.get('abv')
                context.user_data['beer_ibu'] = beer_details.get('ibu')
                context.user_data['untappd_url'] = selected_beer['url']
                
                # Формируем сообщение о найденных данных
                info_parts = []
                if beer_details.get('abv'):
                    info_parts.append(f"Алкоголь: {beer_details['abv']}%")
                if beer_details.get('ibu'):
                    info_parts.append(f"Горечь: {beer_details['ibu']} IBU")
                if beer_details.get('style'):
                    info_parts.append(f"Стиль: {beer_details['style']}")
                
                info_message = "Данные получены:\n" + "\n".join(info_parts) if info_parts else "Данные получены"
                await query.message.reply_text(info_message)
                
                # Спрашиваем стиль только если не получили с Untappd
                if not context.user_data.get('adding_style'):
                    await query.message.reply_text("Введите стиль пива:")
                    return ADDING_STYLE
                else:
                    # Переходим сразу к вводу цены
                    await query.message.reply_text("Введите цену за литр (в рублях):")
                    return ADDING_PRICE
            else:
                # Не смогли получить детали - сохраняем базовую информацию
                context.user_data['adding_name'] = selected_beer['name']
                context.user_data['untappd_url'] = selected_beer['url']
                
                await query.message.reply_text(
                    "Не удалось получить детали\n\n"
                    "Введите стиль пива:"
                )
                return ADDING_STYLE
        
        return ADDING_NAME
    
    async def adding_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода названия пива"""
        name = update.message.text
        context.user_data['adding_name'] = name
        
        await update.message.reply_text("Введите сорт пива:")
        return ADDING_STYLE
    
    async def adding_style(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода сорта пива"""
        style = update.message.text
        context.user_data['adding_style'] = style
        
        await update.message.reply_text("Введите цену за литр (в рублях):")
        return ADDING_PRICE
    
    async def adding_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода цены"""
        try:
            price = float(update.message.text)
            context.user_data['adding_price'] = price
            
            await update.message.reply_text("Введите стоимость за 400мл (в рублях):")
            return ADDING_COST_400ML
        except ValueError:
            await update.message.reply_text("Ошибка: введите корректную цену (число)")
            return ADDING_PRICE
    
    async def adding_cost_400ml(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода стоимости за 400мл"""
        try:
            cost_400ml = float(update.message.text)
            context.user_data['adding_cost_400ml'] = cost_400ml
            
            await update.message.reply_text("Введите стоимость за 250мл (в рублях):")
            return ADDING_COST_250ML
        except ValueError:
            await update.message.reply_text("Ошибка: введите корректную стоимость (число)")
            return ADDING_COST_400ML
    
    async def adding_cost_250ml(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода стоимости за 250мл"""
        try:
            cost_250ml = float(update.message.text)
            context.user_data['adding_cost_250ml'] = cost_250ml
            
            await update.message.reply_text("Введите описание пива (или отправьте '-' для пропуска):")
            return ADDING_DESCRIPTION
        except ValueError:
            await update.message.reply_text("Ошибка: введите корректную стоимость (число)")
            return ADDING_COST_250ML
    
    async def adding_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода описания и завершение добавления"""
        user_description = update.message.text
        if user_description == '-':
            user_description = ""
        
        # Получаем все данные
        tap_position = context.user_data['adding_tap']
        brewery = context.user_data['adding_brewery']
        name = context.user_data['adding_name']
        style = context.user_data['adding_style']
        price = context.user_data['adding_price']
        cost_400ml = context.user_data['adding_cost_400ml']
        cost_250ml = context.user_data['adding_cost_250ml']
        
        # Получаем данные с Untappd если они были найдены ранее
        untappd_url = context.user_data.get('untappd_url', '')
        abv = context.user_data.get('beer_abv')
        ibu = context.user_data.get('beer_ibu')
        
        # Используем описание, введенное пользователем
        description = user_description
        
        # Добавляем пиво в базу данных
        print(f"DEBUG: Добавляем пиво - кран: {tap_position}, пивоварня: {brewery}, название: {name}")
        success = self.db.add_beer(tap_position, brewery, name, style, price, description, 
                                   cost_400ml, cost_250ml, untappd_url, abv, ibu)
        print(f"DEBUG: Результат добавления: {success}")
        
        # Сохраняем в историю для быстрого доступа в будущем
        if success:
            self.db.save_to_history(brewery, name, style, description, untappd_url, abv, ibu)
        
        if success:
            user_id = update.effective_user.id
            is_admin = self.is_admin(user_id)
            
            message = f"Пиво успешно добавлено в кран {tap_position}!\n\n"
            message += f"Пивоварня: {brewery}\n"
            message += f"Название: {name}\n"
            message += f"Сорт: {style}\n"
            
            # Показываем цену за литр только админам
            if is_admin:
                message += f"Цена: {price:.2f} руб/л\n"
            
            # Стоимость показываем всем
            message += f"Стоимость 400мл: {cost_400ml:.2f} руб\n"
            message += f"Стоимость 250мл: {cost_250ml:.2f} руб\n"
            
            message += f"Описание: {description if description else 'Нет'}"
        else:
            message = "Ошибка при добавлении пива"
        
        await update.message.reply_text(message)
        
        # Очищаем данные
        context.user_data.clear()
        return ConversationHandler.END
    
    async def editing_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода нового значения для редактирования"""
        new_value = update.message.text
        tap_position = context.user_data.get('editing_tap')
        field = context.user_data.get('editing_field')
        
        print(f"DEBUG: tap_position={tap_position}, field={field}, new_value={new_value}")
        
        if not tap_position or not field:
            await update.message.reply_text("Ошибка: данные редактирования не найдены")
            context.user_data.clear()
            return ConversationHandler.END
        
        # Конвертируем числовые поля
        if field in ['price', 'cost_400ml', 'cost_250ml']:
            try:
                new_value = float(new_value)
            except ValueError:
                await update.message.reply_text("Ошибка: введите корректное число")
                return EDITING_VALUE
        
        # Обновляем пиво
        print(f"DEBUG: Вызов update_beer_field({tap_position}, {field}, {new_value})")
        success = self.db.update_beer_field(tap_position, field, new_value)
        print(f"DEBUG: Результат обновления: {success}")
        
        if success:
            message = f"Пиво в кране {tap_position} успешно обновлено!"
        else:
            message = "Ошибка при обновлении пива"
        
        await update.message.reply_text(message)
        
        # Очищаем данные
        context.user_data.clear()
        return ConversationHandler.END
    
    async def cancel_operation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик отмены операции"""
        await update.message.reply_text("Операция отменена")
        context.user_data.clear()
        return ConversationHandler.END
    
    async def register_commands(self):
        """Регистрирует команды в Telegram"""
        from telegram import BotCommand
        
        # Только основные команды для всех пользователей
        commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("help", "Показать справку"),
            BotCommand("taps", "Показать все краны"),
            BotCommand("find", "Найти пиво по номеру крана")
        ]
        
        try:
            await self.application.bot.set_my_commands(commands)
            logger.info("Команды зарегистрированы в Telegram")
        except Exception as e:
            logger.error(f"Ошибка при регистрации команд: {e}")
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск бота...")
        
        # Регистрируем команды при запуске
        async def post_init(application):
            await self.register_commands()
        
        self.application.post_init = post_init
        self.application.run_polling()


def main():
    """Основная функция"""
    print("Запуск Telegram бота для управления пивными кранами...")
    
    # Получаем токен из переменной окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Ошибка: Не установлен TELEGRAM_BOT_TOKEN")
        print("Создайте файл .env с переменной TELEGRAM_BOT_TOKEN")
        return 1
    
    # ID администраторов
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    if not admin_ids_str:
        print("Ошибка: Не установлены ADMIN_IDS")
        print("Создайте файл .env с переменной ADMIN_IDS")
        return 1
    
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
    
    try:
        # Создаем и запускаем бота
        bot = BeerBot(token, admin_ids)
        
        print("Конфигурация загружена успешно")
        print("Запуск бота...")
        
        bot.run()
        
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        return 1


if __name__ == "__main__":
    main()
