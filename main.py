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
        
        # Создаем конфигурацию для сохранения
        config_data = {
            'rabbitmq': rabbitmq_config
        }
        
        # Сохранение настроек в файл config.yml
        try:
            with open('config.yml', 'w', encoding='utf-8') as config_file:
                yaml.dump(config_data, config_file, default_flow_style=False, allow_unicode=True)
                
            flash('Настройки успешно сохранены', 'success')
        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации: {str(e)}")
            flash(f'Ошибка при сохранении настроек: {str(e)}', 'danger')
            
        return redirect(url_for('settings'))
    
    # Загрузка текущих настроек
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
    
    # Пытаемся загрузить настройки из файла
    try:
        if os.path.exists('config.yml'):
            with open('config.yml', 'r', encoding='utf-8') as config_file:
                file_config = yaml.safe_load(config_file)
                if file_config and isinstance(file_config, dict):
                    # Обновляем значения по умолчанию 
                    if 'rabbitmq' in file_config and isinstance(file_config['rabbitmq'], dict):
                        config['rabbitmq'].update(file_config['rabbitmq'])
    except Exception as e:
        logger.error(f"Ошибка при загрузке конфигурации: {str(e)}")
        flash(f'Ошибка при загрузке настроек: {str(e)}', 'warning')
    
    return render_template('settings.html', config=config)

@app.route('/windows_logs')
def windows_logs_page():
    """Страница для отображения системных логов Windows"""
    return render_template('windows_logs.html')

@app.route('/api/connect-rabbitmq', methods=['POST'])
def connect_rabbitmq():
    """API для подключения к RabbitMQ"""
    try:
        # Загрузка настроек
        rabbitmq_settings = {
            'host': '192.168.239.181',
            'port': 5672,
            'vhost': '/win_logs',
            'username': 'win_agent',
            'password': '12345678',
            'exchange': 'windows_logs',
            'routing_key': 'system.logs'
        }
        
        # Пытаемся загрузить настройки из файла
        try:
            if os.path.exists('config.yml'):
                with open('config.yml', 'r', encoding='utf-8') as config_file:
                    config = yaml.safe_load(config_file)
                    if config and isinstance(config, dict) and 'rabbitmq' in config:
                        rabbitmq_settings.update(config['rabbitmq'])
        except Exception as e:
            logger.warning(f"Не удалось загрузить настройки из файла: {str(e)}")
        
        # Подключение к RabbitMQ
        result = rabbitmq_client.connect(
            host=rabbitmq_settings.get('host'),
            port=rabbitmq_settings.get('port'),
            virtual_host=rabbitmq_settings.get('vhost'),
            username=rabbitmq_settings.get('username'),
            password=rabbitmq_settings.get('password'),
            exchange=rabbitmq_settings.get('exchange'),
            routing_key=rabbitmq_settings.get('routing_key')
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
        'rabbitmq_connected': False,
        'system_info': get_system_info(),
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Проверяем статус подключения RabbitMQ
    if hasattr(rabbitmq_client, 'is_connected'):
        status['rabbitmq_connected'] = rabbitmq_client.is_connected
        
    return jsonify(status)

@app.route('/api/fetch-windows-logs', methods=['POST'])
def fetch_windows_logs():
    """API для получения системных логов Windows"""
    try:
        data = request.json or {}
        log_type = data.get('log_type')
        
        # Здесь будет реализован реальный сбор логов из Windows
        # В данном случае для демонстрации возвращаем тестовые данные
        
        # Журналы Windows
        log_types = ['System', 'Application', 'Security']
        if log_type and log_type not in log_types and log_type != 'all':
            log_types = [log_type]
        
        # Создаем пример лога
        logs = [{
            'id': 12345,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'LogCollector',
            'level': 1,
            'level_name': 'Информация',
            'log_type': log_types[0] if log_types else 'System',
            'message': 'Здесь будут отображаться реальные логи Windows'
        }]
        
        logger.info(f"Запрошены логи для типа: {log_type if log_type else 'все'}, получено {len(logs)} записей")
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        logger.error(f"Ошибка при получении логов Windows: {str(e)}")
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/api/start-streaming', methods=['POST'])
def start_streaming():
    """API для начала передачи логов в RabbitMQ"""
    try:
        data = request.json or {}
        log_type = data.get('log_type')
        
        # Отметка в логе, что начата передача логов
        logger.info(f"Начата передача логов в RabbitMQ, фильтр по типу: {log_type if log_type else 'все'}")
        
        # Здесь будет реальная логика начала передачи логов в RabbitMQ
        
        return jsonify({'success': True, 'message': 'Передача логов в RabbitMQ начата'})
    except Exception as e:
        logger.error(f"Ошибка при начале передачи логов: {str(e)}")
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/api/stop-streaming', methods=['POST'])
def stop_streaming():
    """API для остановки передачи логов в RabbitMQ"""
    try:
        # Отметка в логе, что передача логов остановлена
        logger.info("Остановлена передача логов в RabbitMQ")
        
        # Здесь будет реальная логика остановки передачи логов в RabbitMQ
        
        return jsonify({'success': True, 'message': 'Передача логов в RabbitMQ остановлена'})
    except Exception as e:
        logger.error(f"Ошибка при остановке передачи логов: {str(e)}")
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

if __name__ == "__main__":
    # Для локальной разработки
    app.run(host='0.0.0.0', port=5000, debug=True)
