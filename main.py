# -*- coding: utf-8 -*-
"""
Главный модуль веб-приложения для сбора системных логов Windows 10
с возможностью подключения к RabbitMQ
"""

import os
import sys
import logging
import yaml
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from agent_logger import AgentLogger
from rabbitmq_client import RabbitMQClient
from utils import get_system_info

# Инициализация логгера
logger = AgentLogger(log_dir='logs').get_logger('web')
logging.basicConfig(level=logging.DEBUG)

# Инициализация приложения Flask
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Загрузка конфигурации RabbitMQ
config_path = 'config.ini'
rabbitmq_client = RabbitMQClient()

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html', system_info=get_system_info())

@app.route('/logs')
def logs_page():
    """Страница просмотра логов"""
    log_entries = AgentLogger().get_log_entries(max_entries=1000)
    return render_template('logs.html', log_entries=log_entries)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Страница настроек"""
    if request.method == 'POST':
        # Обновление настроек RabbitMQ
        rabbitmq_config = {
            'host': request.form.get('rabbitmq_host'),
            'port': int(request.form.get('rabbitmq_port')),
            'vhost': request.form.get('rabbitmq_vhost'),
            'username': request.form.get('rabbitmq_username'),
            'password': request.form.get('rabbitmq_password'),
            'exchange': request.form.get('rabbitmq_exchange'),
            'routing_key': request.form.get('rabbitmq_routing_key'),
            'use_ssl': bool(request.form.get('rabbitmq_ssl', False))
        }
        
        # Сохранение настроек в файл config.yml
        with open('config.yml', 'w') as config_file:
            yaml.dump({'rabbitmq': rabbitmq_config}, config_file, default_flow_style=False)
            
        flash('Настройки успешно сохранены', 'success')
        return redirect(url_for('settings'))
    
    # Загрузка текущих настроек
    config = {}
    try:
        with open('config.yml', 'r') as config_file:
            config = yaml.safe_load(config_file) or {}
    except FileNotFoundError:
        # Если файл не найден, используем настройки по умолчанию
        config = {
            'rabbitmq': {
                'host': '192.168.239.181',
                'port': 5672,
                'vhost': '/win_logs',
                'username': 'win_agent',
                'password': '12345678',
                'exchange': 'windows_logs',
                'routing_key': 'system.logs',
                'use_ssl': False
            }
        }
    
    return render_template('settings.html', config=config)

@app.route('/api/connect-rabbitmq', methods=['POST'])
def connect_rabbitmq():
    """API для подключения к RabbitMQ"""
    try:
        # Загрузка настроек
        with open('config.yml', 'r') as config_file:
            config = yaml.safe_load(config_file) or {}
        
        rabbitmq_settings = config.get('rabbitmq', {})
        
        # Подключение к RabbitMQ
        result = rabbitmq_client.connect(
            host=rabbitmq_settings.get('host', '192.168.239.181'),
            port=rabbitmq_settings.get('port', 5672),
            virtual_host=rabbitmq_settings.get('vhost', '/win_logs'),
            username=rabbitmq_settings.get('username', 'win_agent'),
            password=rabbitmq_settings.get('password', '12345678'),
            exchange=rabbitmq_settings.get('exchange', 'windows_logs'),
            routing_key=rabbitmq_settings.get('routing_key', 'system.logs')
        )
        
        if result:
            logger.info(f"Успешное подключение к RabbitMQ: {rabbitmq_settings.get('host')}")
            return jsonify({'success': True, 'message': 'Успешное подключение к RabbitMQ'})
        else:
            logger.error(f"Ошибка подключения к RabbitMQ: {rabbitmq_settings.get('host')}")
            return jsonify({'success': False, 'message': 'Ошибка подключения к RabbitMQ'})
    except Exception as e:
        logger.error(f"Ошибка при подключении к RabbitMQ: {str(e)}")
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/api/disconnect-rabbitmq', methods=['POST'])
def disconnect_rabbitmq():
    """API для отключения от RabbitMQ"""
    try:
        rabbitmq_client.disconnect()
        logger.info("Отключение от RabbitMQ")
        return jsonify({'success': True, 'message': 'Отключено от RabbitMQ'})
    except Exception as e:
        logger.error(f"Ошибка при отключении от RabbitMQ: {str(e)}")
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/api/publish-log', methods=['POST'])
def publish_log():
    """API для публикации лога в RabbitMQ"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'Нет данных для отправки'})
            
        # Публикация лога в RabbitMQ
        result = rabbitmq_client.publish_log(data)
        
        if result:
            logger.info(f"Лог успешно опубликован в RabbitMQ: {data.get('id')}")
            return jsonify({'success': True, 'message': 'Лог успешно опубликован'})
        else:
            logger.error(f"Ошибка публикации лога в RabbitMQ: {data.get('id')}")
            return jsonify({'success': False, 'message': 'Ошибка публикации лога'})
    except Exception as e:
        logger.error(f"Ошибка при публикации лога в RabbitMQ: {str(e)}")
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/api/agent-logs')
def get_agent_logs():
    """API для получения логов агента"""
    try:
        level = request.args.get('level')
        max_entries = int(request.args.get('max_entries', 1000))
        
        log_entries = AgentLogger().get_log_entries(max_entries=max_entries, level=level)
        return jsonify({'success': True, 'logs': log_entries})
    except Exception as e:
        logger.error(f"Ошибка при получении логов агента: {str(e)}")
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/api/status')
def get_status():
    """API для получения статуса подключения к RabbitMQ"""
    status = {
        'rabbitmq_connected': rabbitmq_client.is_connected() if hasattr(rabbitmq_client, 'is_connected') else False,
        'system_info': get_system_info(),
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    return jsonify(status)

if __name__ == "__main__":
    # Для локальной разработки
    app.run(host='0.0.0.0', port=5000, debug=True)
