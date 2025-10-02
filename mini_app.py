#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Mini App для управления пивными кранами
Flask веб-приложение с интеграцией Telegram WebApp
"""

import os
import json
import hmac
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from beer_database import BeerDatabase

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Инициализация базы данных
db = BeerDatabase()

# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def verify_telegram_auth(auth_data):
    """Проверка подлинности данных от Telegram WebApp"""
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    # Извлекаем hash из данных
    received_hash = auth_data.get('hash', '')
    auth_data_copy = auth_data.copy()
    del auth_data_copy['hash']
    
    # Создаем строку для проверки
    data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(auth_data_copy.items())])
    
    # Создаем секретный ключ
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    
    # Вычисляем hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(received_hash, calculated_hash)

def is_admin(user_id):
    """Проверка, является ли пользователь администратором"""
    admin_ids = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '721327256,372800870').split(',') if x.strip()]
    return user_id in admin_ids

@app.route('/')
def index():
    """Главная страница Mini App"""
    return render_template('index.html')

@app.route('/api/auth', methods=['POST'])
def authenticate():
    """Аутентификация пользователя через Telegram WebApp"""
    try:
        auth_data = request.get_json()
        
        if not verify_telegram_auth(auth_data):
            return jsonify({'error': 'Invalid authentication data'}), 401
        
        user_id = int(auth_data.get('user', {}).get('id', 0))
        user_info = {
            'id': user_id,
            'username': auth_data.get('user', {}).get('username', ''),
            'first_name': auth_data.get('user', {}).get('first_name', ''),
            'last_name': auth_data.get('user', {}).get('last_name', ''),
            'is_admin': is_admin(user_id)
        }
        
        return jsonify({
            'success': True,
            'user': user_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/taps')
def get_taps():
    """Получить список всех кранов"""
    try:
        beers = db.get_all_beers()
        taps_data = []
        
        for beer in beers:
            tap_pos, brewery, name, style, price = beer
            taps_data.append({
                'tap_position': tap_pos,
                'brewery': brewery,
                'beer_name': name,
                'beer_style': style,
                'price_per_liter': price
            })
        
        return jsonify({
            'success': True,
            'taps': taps_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tap/<int:tap_position>')
def get_tap(tap_position):
    """Получить информацию о конкретном кране"""
    try:
        beer = db.get_beer_by_tap(tap_position)
        
        if not beer:
            return jsonify({'error': 'Tap not found'}), 404
        
        tap_pos, brewery, name, style, price = beer
        return jsonify({
            'success': True,
            'tap': {
                'tap_position': tap_pos,
                'brewery': brewery,
                'beer_name': name,
                'beer_style': style,
                'price_per_liter': price
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tap', methods=['POST'])
def add_tap():
    """Добавить пиво в кран (только для админов)"""
    try:
        data = request.get_json()
        
        # Проверяем права администратора
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization required'}), 401
        
        # В реальном приложении здесь должна быть проверка JWT токена
        # Для упрощения используем базовую проверку
        user_id = int(data.get('user_id', 0))
        if not is_admin(user_id):
            return jsonify({'error': 'Admin access required'}), 403
        
        # Добавляем пиво
        success = db.add_beer(
            tap_position=data['tap_position'],
            brewery=data['brewery'],
            beer_name=data['beer_name'],
            beer_style=data['beer_style'],
            price_per_liter=float(data['price_per_liter'])
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Пиво успешно добавлено'})
        else:
            return jsonify({'error': 'Кран уже занят'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tap/<int:tap_position>', methods=['PUT'])
def update_tap(tap_position):
    """Обновить информацию о кране (только для админов)"""
    try:
        data = request.get_json()
        
        # Проверяем права администратора
        user_id = int(data.get('user_id', 0))
        if not is_admin(user_id):
            return jsonify({'error': 'Admin access required'}), 403
        
        # Обновляем данные
        update_data = {}
        if 'brewery' in data:
            update_data['brewery'] = data['brewery']
        if 'beer_name' in data:
            update_data['beer_name'] = data['beer_name']
        if 'beer_style' in data:
            update_data['beer_style'] = data['beer_style']
        if 'price_per_liter' in data:
            update_data['price_per_liter'] = float(data['price_per_liter'])
        
        success = db.update_beer(tap_position, **update_data)
        
        if success:
            return jsonify({'success': True, 'message': 'Информация обновлена'})
        else:
            return jsonify({'error': 'Кран не найден'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tap/<int:tap_position>', methods=['DELETE'])
def delete_tap(tap_position):
    """Удалить пиво из крана (только для админов)"""
    try:
        data = request.get_json()
        
        # Проверяем права администратора
        user_id = int(data.get('user_id', 0))
        if not is_admin(user_id):
            return jsonify({'error': 'Admin access required'}), 403
        
        # Удаляем пиво
        success = db.delete_beer(tap_position)
        
        if success:
            return jsonify({'success': True, 'message': 'Пиво удалено'})
        else:
            return jsonify({'error': 'Кран не найден'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Запуск Mini App на порту {port}")
    print(f"Отладка: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
