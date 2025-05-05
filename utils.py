# -*- coding: utf-8 -*-
"""
Вспомогательные функции для агента сбора логов
"""

import os
import sys
import configparser
import datetime
import platform

def create_default_config(config_path):
    """
    Создание конфигурационного файла с настройками по умолчанию
    
    Args:
        config_path (str): Путь к файлу конфигурации
    """
    config = configparser.ConfigParser()
    
    # Добавляем раздел RabbitMQ
    config['RabbitMQ'] = {
        'host': 'localhost',
        'port': '5672',
        'vhost': '/',
        'username': 'guest',
        'password': 'guest',
        'exchange': 'windows_logs',
        'routing_key': 'system.logs',
        'autoconnect': 'false'
    }
    
    # Добавляем раздел Logging
    config['Logging'] = {
        'directory': 'logs'
    }
    
    # Добавляем раздел Logs
    config['Logs'] = {
        'system': 'true',
        'application': 'true',
        'security': 'false',
        'setup': 'false',
        'dns': 'false',
        'active_directory': 'false',
        'hours_back': '1',
        'level_filter': '0',
        'send_to_rabbitmq': 'false'
    }
    
    # Записываем конфигурацию в файл
    with open(config_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

def get_system_info():
    """
    Получение информации о системе
    
    Returns:
        dict: Словарь с информацией о системе
    """
    info = {
        'platform': platform.platform(),
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'architecture': platform.architecture(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'hostname': platform.node()
    }
    
    return info

def format_size(size_bytes):
    """
    Форматирование размера в байтах в человекочитаемый формат
    
    Args:
        size_bytes (int): Размер в байтах
        
    Returns:
        str: Форматированный размер
    """
    if size_bytes == 0:
        return "0 Б"
        
    # Список суффиксов
    size_names = ["Б", "КБ", "МБ", "ГБ", "ТБ", "ПБ", "ЭБ", "ЗБ", "ЙБ"]
    
    # Определяем индекс суффикса
    i = 0
    power = 1024
    
    while size_bytes >= power:
        size_bytes /= power
        i += 1
        
    return f"{size_bytes:.2f} {size_names[i]}"

def parse_windows_timestamp(timestamp):
    """
    Преобразование временной метки Windows в объект datetime
    
    Args:
        timestamp (int): Временная метка Windows (100-наносекундные интервалы с 1 января 1601 года)
        
    Returns:
        datetime: Объект datetime
    """
    # Константа для преобразования в Unix-время (разница в секундах между 1601-01-01 и 1970-01-01)
    WINDOWS_EPOCH_DELTA = 11644473600
    
    # Преобразуем в секунды с начала эпохи Unix
    unix_timestamp = (timestamp / 10000000) - WINDOWS_EPOCH_DELTA
    
    # Преобразуем в datetime
    dt = datetime.datetime.fromtimestamp(unix_timestamp)
    
    return dt
