#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram бот для управления пивными кранами
Админ может управлять кранами, пользователи могут только просматривать
"""

import logging
import os
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

class BeerBot:
    def __init__(self, token: str, admin_ids: list):
        """Инициализация бота"""
        self.token = token
        self.admin_ids = admin_ids  # Список ID администраторов
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
            welcome_text += "/admin - панель администратора\n"
            welcome_text += "/help - помощь"
        else:
            welcome_text += "Вы пользователь\n"
            welcome_text += "Доступные команды:\n"
            welcome_text += "/taps - показать все краны\n"
            welcome_text += "/find <номер> - найти пиво по номеру крана\n"
            welcome_text += "/help - помощь"
        
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        user_id = update.effective_user.id
        is_admin = self.is_admin(user_id)
        
        help_text = "Помощь по командам:\n\n"
        help_text += "Общие команды:\n"
        help_text += "/taps - показать все краны\n"
        help_text += "/find <номер> - найти пиво по номеру крана\n"
        help_text += "/cancel - отменить текущую операцию\n\n"
        
        if is_admin:
            help_text += "Команды администратора:\n"
            help_text += "/admin - панель администратора\n"
            help_text += "В панели админа доступны:\n"
            help_text += "• Добавление нового пива в кран\n"
            help_text += "• Редактирование информации о пиве\n"
            help_text += "• Удаление пива из крана\n"
        
        await update.message.reply_text(help_text)
    
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
        
        if not self.is_admin(user_id):
            await query.edit_message_text("У вас нет прав администратора")
            return
        
        data = query.data
        
        if data == "add_beer":
            await query.edit_message_text(
                "**ДОБАВЛЕНИЕ НОВОГО ПИВА**\n\n"
                "Введите номер крана (число):",
                parse_mode='Markdown'
            )
            return ADD_TAP
        
        elif data == "update_beer":
            await query.edit_message_text(
                "**РЕДАКТИРОВАНИЕ ПИВА**\n\n"
                "Введите номер крана для редактирования:",
                parse_mode='Markdown'
            )
            return UPDATE_TAP
        
        elif data == "delete_beer":
            await query.edit_message_text(
                "**УДАЛЕНИЕ ПИВА**\n\n"
                "Введите номер крана для удаления:",
                parse_mode='Markdown'
            )
            return DELETE_TAP
        
        elif data == "show_taps":
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
    
    # Методы для добавления пива
    async def add_tap_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение номера крана для добавления"""
        try:
            tap_number = int(update.message.text)
            context.user_data['add_tap'] = tap_number
            
            # Проверяем, не занят ли кран
            existing_beer = self.db.get_beer_by_tap(tap_number)
            if existing_beer:
                await update.message.reply_text(
                    f"Кран {tap_number} уже занят пивом:\n"
                    f"{existing_beer[2]} от {existing_beer[1]}\n\n"
                    "Введите другой номер крана:"
                )
                return ADD_TAP
            
            await update.message.reply_text(
                f"Кран {tap_number} свободен\n\n"
                "Введите название пивоварни:"
            )
            return ADD_BREWERY
            
        except ValueError:
            await update.message.reply_text("Неверный формат. Введите число:")
            return ADD_TAP
    
    async def add_brewery(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение названия пивоварни"""
        context.user_data['add_brewery'] = update.message.text
        
        await update.message.reply_text(
            f"Пивоварня: {update.message.text}\n\n"
            "Введите название пива:"
        )
        return ADD_NAME
    
    async def add_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение названия пива"""
        context.user_data['add_name'] = update.message.text
        
        await update.message.reply_text(
            f"Название пива: {update.message.text}\n\n"
            "Введите стиль пива:"
        )
        return ADD_STYLE
    
    async def add_style(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение стиля пива"""
        context.user_data['add_style'] = update.message.text
        
        await update.message.reply_text(
            f"Стиль пива: {update.message.text}\n\n"
            "Введите цену за литр (в рублях):"
        )
        return ADD_PRICE
    
    async def add_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение цены и сохранение пива"""
        try:
            price = float(update.message.text)
            
            # Сохраняем пиво в базу данных
            success = self.db.add_beer(
                context.user_data['add_tap'],
                context.user_data['add_brewery'],
                context.user_data['add_name'],
                context.user_data['add_style'],
                price
            )
            
            if success:
                await update.message.reply_text(
                    f"**ПИВО УСПЕШНО ДОБАВЛЕНО!**\n\n"
                    f"**Кран {context.user_data['add_tap']}:**\n"
                    f"Пивоварня: {context.user_data['add_brewery']}\n"
                    f"Название: {context.user_data['add_name']}\n"
                    f"Стиль: {context.user_data['add_style']}\n"
                    f"Цена: {price:.2f} руб/л",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("Ошибка при добавлении пива")
            
            # Очищаем временные данные
            context.user_data.clear()
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text("Неверный формат цены. Введите число:")
            return ADD_PRICE
    
    # Методы для обновления пива
    async def update_tap_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение номера крана для обновления"""
        try:
            tap_number = int(update.message.text)
            beer = self.db.get_beer_by_tap(tap_number)
            
            if not beer:
                await update.message.reply_text(f"Кран {tap_number} пуст или не существует")
                return ConversationHandler.END
            
            context.user_data['update_tap'] = tap_number
            
            # Показываем текущую информацию
            tap_pos, brewery, name, style, price = beer
            message = f"**Текущая информация о кране {tap_pos}:**\n\n"
            message += f"Пивоварня: {brewery}\n"
            message += f"Название: {name}\n"
            message += f"Стиль: {style}\n"
            message += f"Цена: {price:.2f} руб/л\n\n"
            message += "Что хотите изменить?"
            
            keyboard = [
                [InlineKeyboardButton("Пивоварня", callback_data="update_brewery")],
                [InlineKeyboardButton("Название", callback_data="update_name")],
                [InlineKeyboardButton("Стиль", callback_data="update_style")],
                [InlineKeyboardButton("Цена", callback_data="update_price")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            return UPDATE_FIELD
            
        except ValueError:
            await update.message.reply_text("Неверный формат. Введите число:")
            return UPDATE_TAP
    
    async def update_field_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора поля для обновления"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        field_names = {
            "update_brewery": "пивоварню",
            "update_name": "название пива",
            "update_style": "стиль пива",
            "update_price": "цену за литр"
        }
        
        context.user_data['update_field'] = data
        
        await query.edit_message_text(
            f"Введите новое значение для {field_names[data]}:",
            parse_mode='Markdown'
        )
        return UPDATE_VALUE
    
    async def update_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновление значения поля"""
        new_value = update.message.text
        tap_number = context.user_data['update_tap']
        field = context.user_data['update_field']
        
        # Подготавливаем параметры для обновления
        update_params = {}
        
        if field == "update_brewery":
            update_params['brewery'] = new_value
        elif field == "update_name":
            update_params['beer_name'] = new_value
        elif field == "update_style":
            update_params['beer_style'] = new_value
        elif field == "update_price":
            try:
                update_params['price_per_liter'] = float(new_value)
            except ValueError:
                await update.message.reply_text("Неверный формат цены. Введите число:")
                return UPDATE_VALUE
        
        # Обновляем в базе данных
        success = self.db.update_beer(tap_number, **update_params)
        
        if success:
            await update.message.reply_text(f"Поле успешно обновлено!")
        else:
            await update.message.reply_text("Ошибка при обновлении")
        
        # Очищаем временные данные
        context.user_data.clear()
        return ConversationHandler.END
    
    # Методы для удаления пива
    async def delete_tap_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаление пива из крана"""
        try:
            tap_number = int(update.message.text)
            beer = self.db.get_beer_by_tap(tap_number)
            
            if not beer:
                await update.message.reply_text(f"Кран {tap_number} пуст или не существует")
                context.user_data.clear()
                return ConversationHandler.END
            
            # Показываем информацию о пиве для подтверждения
            tap_pos, brewery, name, style, price = beer
            message = f"**УДАЛЕНИЕ ПИВА ИЗ КРАНА {tap_pos}:**\n\n"
            message += f"Пивоварня: {brewery}\n"
            message += f"Название: {name}\n"
            message += f"Стиль: {style}\n"
            message += f"Цена: {price:.2f} руб/л\n\n"
            message += "Вы уверены? Введите 'да' для подтверждения или 'нет' для отмены:"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            context.user_data['delete_tap'] = tap_number
            return DELETE_CONFIRM
            
        except ValueError:
            await update.message.reply_text("Неверный формат. Введите число:")
            return DELETE_TAP
    
    async def delete_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение удаления"""
        response = update.message.text.lower().strip()
        tap_number = context.user_data.get('delete_tap')
        
        if response in ['да', 'yes', 'y', 'да', 'удалить']:
            success = self.db.delete_beer(tap_number)
            if success:
                await update.message.reply_text(f"Пиво из крана {tap_number} успешно удалено!")
            else:
                await update.message.reply_text("Ошибка при удалении")
        else:
            await update.message.reply_text("Удаление отменено")
        
        context.user_data.clear()
        return ConversationHandler.END
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена текущей операции"""
        context.user_data.clear()
        await update.message.reply_text("Операция отменена")
        return ConversationHandler.END
    
    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик неизвестных команд"""
        await update.message.reply_text("Неизвестная команда. Используйте /help для списка команд.")
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск бота...")
        self.application.run_polling()

def main():
    """Основная функция"""
    # Получаем токен из переменной окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Ошибка: Не установлен TELEGRAM_BOT_TOKEN")
        print("Установите переменную окружения: export TELEGRAM_BOT_TOKEN='ваш_токен'")
        return
    
    # ID администраторов (замените на ваши)
    admin_ids = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    if not admin_ids:
        print("Ошибка: Не установлены ADMIN_IDS")
        print("Установите переменную окружения: export ADMIN_IDS='ваш_id,другой_id'")
        return
    
    # Создаем и запускаем бота
    bot = BeerBot(token, admin_ids)
    bot.run()

if __name__ == "__main__":
    main()
