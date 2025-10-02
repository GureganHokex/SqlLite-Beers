#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram бот с интеграцией Mini App
Объединяет функции обычного бота и Mini App
"""

import logging
import os
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from beer_database import BeerDatabase

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы для состояний диалога
(ADD_TAP, ADD_BREWERY, ADD_NAME, ADD_STYLE, ADD_PRICE,
 UPDATE_TAP, UPDATE_FIELD, UPDATE_VALUE,
 DELETE_TAP, DELETE_CONFIRM) = range(10)

class BeerBotWithWebApp:
    def __init__(self, token: str, admin_ids: list, webapp_url: str = None):
        """Инициализация бота с поддержкой Mini App"""
        self.token = token
        self.admin_ids = admin_ids
        self.webapp_url = webapp_url or os.getenv('WEBAPP_URL', 'http://localhost:8080')
        self.db = BeerDatabase()
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return user_id in self.admin_ids
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("taps", self.show_taps_command))
        self.application.add_handler(CommandHandler("find", self.find_beer_command))
        self.application.add_handler(CommandHandler("app", self.open_app_command))
        
        # Админские команды
        admin_handler = ConversationHandler(
            entry_points=[CommandHandler("admin", self.admin_command)],
            states={
                ADD_TAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_tap_number)],
                ADD_BREWERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_brewery)],
                ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_name)],
                ADD_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_style)],
                ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_price)],
                UPDATE_TAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.update_tap_number)],
                UPDATE_FIELD: [CallbackQueryHandler(self.update_field_callback)],
                UPDATE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.update_value)],
                DELETE_TAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.delete_tap_number)],
                DELETE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.delete_confirmation)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)],
        )
        
        self.application.add_handler(admin_handler)
        
        # Обработчик кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработчик неизвестных команд
        self.application.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        is_admin = self.is_admin(user_id)
        
        welcome_text = f"Добро пожаловать в бот управления пивными кранами!\n\n"
        
        if is_admin:
            welcome_text += "Вы администратор\n"
            welcome_text += "Доступные команды:\n"
            welcome_text += "/taps - показать все краны\n"
            welcome_text += "/find <номер> - найти пиво по номеру крана\n"
            welcome_text += "/app - открыть веб-приложение\n"
            welcome_text += "/admin - панель администратора\n"
            welcome_text += "/help - помощь"
        else:
            welcome_text += "Вы пользователь\n"
            welcome_text += "Доступные команды:\n"
            welcome_text += "/taps - показать все краны\n"
            welcome_text += "/find <номер> - найти пиво по номеру крана\n"
            welcome_text += "/app - открыть веб-приложение\n"
            welcome_text += "/help - помощь"
        
        # Создаем кнопки
        keyboard = []
        
        # Кнопка для открытия веб-приложения
        if self.webapp_url:
            webapp_button = InlineKeyboardButton(
                "Открыть приложение",
                web_app=WebAppInfo(url=self.webapp_url)
            )
            keyboard.append([webapp_button])
        
        # Кнопка для просмотра кранов
        taps_button = InlineKeyboardButton("Показать краны", callback_data="show_taps")
        keyboard.append([taps_button])
        
        # Кнопка помощи
        help_button = InlineKeyboardButton("Помощь", callback_data="help")
        keyboard.append([help_button])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        user_id = update.effective_user.id
        is_admin = self.is_admin(user_id)
        
        help_text = "Помощь по командам:\n\n"
        help_text += "Общие команды:\n"
        help_text += "/taps - показать все краны\n"
        help_text += "/find <номер> - найти пиво по номеру крана\n"
        help_text += "/app - открыть веб-приложение\n"
        help_text += "/cancel - отменить текущую операцию\n\n"
        
        if is_admin:
            help_text += "Команды администратора:\n"
            help_text += "/admin - панель администратора\n"
            help_text += "В панели админа доступны:\n"
            help_text += "• Добавление нового пива в кран\n"
            help_text += "• Редактирование информации о пиве\n"
            help_text += "• Удаление пива из крана\n"
        
        await update.message.reply_text(help_text)
    
    async def open_app_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для открытия веб-приложения"""
        if not self.webapp_url:
            await update.message.reply_text("Веб-приложение не настроено")
            return
        
        webapp_button = InlineKeyboardButton(
            "Открыть веб-приложение",
            web_app=WebAppInfo(url=self.webapp_url)
        )
        
        keyboard = [[webapp_button]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Нажмите кнопку ниже, чтобы открыть веб-приложение для управления пивными кранами:",
            reply_markup=reply_markup
        )
    
    async def show_taps_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все краны"""
        beers = self.db.get_all_beers()
        
        if not beers:
            await update.message.reply_text("Краны пусты")
            return
        
        message = "**ТЕКУЩИЕ КРАНЫ:**\n\n"
        
        for beer in beers:
            tap_pos, brewery, name, style, price = beer
            message += f"**Кран {tap_pos}:**\n"
            message += f"Пивоварня: {brewery}\n"
            message += f"Название: {name}\n"
            message += f"Стиль: {style}\n"
            message += f"Цена: {price:.2f} руб/л\n\n"
        
        # Разбиваем длинные сообщения
        if len(message) > 4000:
            chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, parse_mode='Markdown')
    
    async def find_beer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Найти пиво по номеру крана"""
        if not context.args:
            await update.message.reply_text("Использование: /find <номер_крана>\nПример: /find 1")
            return
        
        try:
            tap_number = int(context.args[0])
            beer = self.db.get_beer_by_tap(tap_number)
            
            if beer:
                tap_pos, brewery, name, style, price = beer
                message = f"**Кран {tap_pos}:**\n\n"
                message += f"**Пивоварня:** {brewery}\n"
                message += f"**Название:** {name}\n"
                message += f"**Стиль:** {style}\n"
                message += f"**Цена:** {price:.2f} руб/л"
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"Кран {tap_number} пуст или не существует")
                
        except ValueError:
            await update.message.reply_text("Неверный формат номера крана. Используйте число.")
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Панель администратора"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("У вас нет прав администратора")
            return
        
        keyboard = [
            [InlineKeyboardButton("Добавить пиво", callback_data="add_beer")],
            [InlineKeyboardButton("Редактировать пиво", callback_data="update_beer")],
            [InlineKeyboardButton("Удалить пиво", callback_data="delete_beer")],
            [InlineKeyboardButton("Показать все краны", callback_data="show_taps")]
        ]
        
        # Добавляем кнопку для веб-приложения
        if self.webapp_url:
            webapp_button = InlineKeyboardButton(
                "Открыть веб-приложение",
                web_app=WebAppInfo(url=self.webapp_url)
            )
            keyboard.append([webapp_button])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "**ПАНЕЛЬ АДМИНИСТРАТОРА**\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data == "show_taps":
            beers = self.db.get_all_beers()
            
            if not beers:
                await query.edit_message_text("Краны пусты")
                return
            
            message = "**ТЕКУЩИЕ КРАНЫ:**\n\n"
            
            for beer in beers:
                tap_pos, brewery, name, style, price = beer
                message += f"**Кран {tap_pos}:**\n"
                message += f"Пивоварня: {brewery}\n"
                message += f"Название: {name}\n"
                message += f"Стиль: {style}\n"
                message += f"Цена: {price:.2f} руб/л\n\n"
            
            await query.edit_message_text(message, parse_mode='Markdown')
        
        elif data == "help":
            await query.edit_message_text(
                "**Помощь по командам:**\n\n"
                "/taps - показать все краны\n"
                "/find <номер> - найти пиво по номеру крана\n"
                "/app - открыть веб-приложение\n"
                "/admin - панель администратора (только для админов)\n"
                "/help - эта справка",
                parse_mode='Markdown'
            )
        
        # Остальные обработчики кнопок из оригинального бота
        elif data == "add_beer":
            if not self.is_admin(user_id):
                await query.edit_message_text("У вас нет прав администратора")
                return
            
            await query.edit_message_text(
                "**ДОБАВЛЕНИЕ НОВОГО ПИВА**\n\n"
                "Введите номер крана (число):",
                parse_mode='Markdown'
            )
            return ADD_TAP
        
        # Добавьте остальные обработчики из оригинального кода...
    
    # Добавьте остальные методы из оригинального telegram_bot.py
    # (add_tap_number, add_brewery, add_name, add_style, add_price,
    # update_tap_number, update_field_callback, update_value,
    # delete_tap_number, delete_confirmation, cancel_command, unknown_command)
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск бота с поддержкой Mini App...")
        logger.info(f"URL веб-приложения: {self.webapp_url}")
        self.application.run_polling()

def main():
    """Основная функция"""
    # Получаем токен из переменной окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Ошибка: Не установлен TELEGRAM_BOT_TOKEN")
        print("Установите переменную окружения: export TELEGRAM_BOT_TOKEN='ваш_токен'")
        return
    
    # ID администраторов
    admin_ids = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    if not admin_ids:
        print("Ошибка: Не установлены ADMIN_IDS")
        print("Установите переменную окружения: export ADMIN_IDS='ваш_id,другой_id'")
        return
    
    # URL веб-приложения
    webapp_url = os.getenv('WEBAPP_URL', 'http://localhost:8080')
    
    # Создаем и запускаем бота
    bot = BeerBotWithWebApp(token, admin_ids, webapp_url)
    bot.run()

if __name__ == "__main__":
    main()
