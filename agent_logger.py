# -*- coding: utf-8 -*-
"""
Модуль для журналирования действий агента
"""

import os
import logging
import logging.handlers
import datetime
import time
from singleton import Singleton

class AgentLogger(metaclass=Singleton):
    """
    Класс для журналирования действий агента
    Реализован как Singleton для обеспечения единственного экземпляра
    """
    
    def __init__(self, log_dir='logs'):
        """
        Инициализация системы журналирования
        
        Args:
            log_dir (str): Директория для хранения журналов
        """
        self.log_dir = log_dir
        self.loggers = {}
        
        # Создаем директорию для логов, если она не существует
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Имя файла журнала с текущей датой
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.log_file = os.path.join(log_dir, f'agent_{current_date}.log')
        
        # Настраиваем корневой логгер
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """Настройка корневого логгера"""
        # Создаем форматтер для логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Обработчик для записи в файл
        file_handler = logging.handlers.TimedRotatingFileHandler(
            self.log_file,
            when='midnight',
            backupCount=30,  # Храним логи за 30 дней
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # Обработчик для вывода в консоль
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # Настраиваем корневой логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Удаляем существующие обработчики, чтобы избежать дублирования
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    def get_logger(self, name):
        """
        Получение логгера с указанным именем
        
        Args:
            name (str): Имя логгера
            
        Returns:
            logging.Logger: Настроенный логгер
        """
        if name in self.loggers:
            return self.loggers[name]
            
        # Создаем новый логгер
        logger = logging.getLogger(name)
        self.loggers[name] = logger
        
        return logger
        
    def get_log_file_path(self):
        """
        Получение пути к текущему файлу журнала
        
        Returns:
            str: Путь к файлу журнала
        """
        return self.log_file
        
    def get_log_entries(self, max_entries=1000, level=None):
        """
        Получение записей журнала
        
        Args:
            max_entries (int): Максимальное количество записей
            level (str, optional): Уровень логирования для фильтрации
            
        Returns:
            list: Список записей журнала
        """
        entries = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # Фильтрация по уровню, если указан
                    if level and f" - {level} - " not in line:
                        continue
                        
                    entries.append(line.strip())
                    
                    if len(entries) >= max_entries:
                        break
                        
        except Exception as e:
            print(f"Ошибка при чтении журнала: {str(e)}")
            
        # Возвращаем записи в обратном порядке (новые сверху)
        return entries[::-1]
