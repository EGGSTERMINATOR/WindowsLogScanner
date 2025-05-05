# -*- coding: utf-8 -*-
"""
Модуль сбора системных логов Windows 10
"""

import os
import json
import logging
import datetime
import threading
import time
from agent_logger import AgentLogger

# Инициализируем логгер
logger = AgentLogger().get_logger('log_collector')

class LogCollector:
    """Класс для сбора системных логов Windows"""
    
    # Соответствие русских и английских названий журналов
    LOG_TYPES = {
        'Система': 'System',
        'Приложение': 'Application',
        'Безопасность': 'Security',
        'Настройка': 'Setup',
        'Перенаправление DNS-сервера': 'DNS Server',
        'Active Directory': 'Directory Service'
    }
    
    # Типы событий
    EVENT_LEVELS = {
        1: 'Информация',  # EVENTLOG_SUCCESS | EVENTLOG_INFORMATION_TYPE
        2: 'Предупреждение',  # EVENTLOG_WARNING_TYPE
        3: 'Ошибка',  # EVENTLOG_ERROR_TYPE
        4: 'Успешный аудит',  # EVENTLOG_AUDIT_SUCCESS
        5: 'Неудачный аудит'  # EVENTLOG_AUDIT_FAILURE
    }
    
    def __init__(self):
        """Инициализация коллектора логов"""
        self.offsets = {}
        self.offsets_file = 'offsets.json'
        self.is_collecting = False
        self.collect_thread = None
        
        # Загрузка последних смещений
        self._load_offsets()
        
    def _load_offsets(self):
        """Загрузка смещений для журналов из файла"""
        try:
            if os.path.exists(self.offsets_file):
                with open(self.offsets_file, 'r', encoding='utf-8') as f:
                    self.offsets = json.load(f)
                logger.info(f"Смещения загружены из {self.offsets_file}")
            else:
                logger.info(f"Файл смещений {self.offsets_file} не найден, будет создан новый")
        except Exception as e:
            logger.error(f"Ошибка при загрузке смещений: {str(e)}")
            self.offsets = {}
            
    def _save_offsets(self):
        """Сохранение смещений в файл"""
        try:
            with open(self.offsets_file, 'w', encoding='utf-8') as f:
                json.dump(self.offsets, f, ensure_ascii=False, indent=2)
            logger.debug(f"Смещения сохранены в {self.offsets_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении смещений: {str(e)}")
    
    def start_collecting(self, log_types, hours_back=1, callback=None):
        """
        Запуск сбора логов в отдельном потоке
        
        Args:
            log_types (list): Список типов логов для сбора на русском языке
            hours_back (int): Количество часов назад для сбора логов
            callback (function): Функция обратного вызова для передачи собранных логов
        """
        if self.is_collecting:
            logger.warning("Сбор логов уже запущен")
            return
            
        # Преобразуем русские названия в английские
        eng_log_types = [self.LOG_TYPES.get(lt, lt) for lt in log_types]
        
        # Запускаем поток сбора логов
        self.is_collecting = True
        self.collect_thread = threading.Thread(
            target=self._collect_logs_thread,
            args=(eng_log_types, hours_back, callback)
        )
        self.collect_thread.daemon = True
        self.collect_thread.start()
        
        logger.info(f"Запущен сбор логов: {', '.join(log_types)} за {hours_back} ч.")
        
    def stop_collecting(self):
        """Остановка сбора логов"""
        if not self.is_collecting:
            return
            
        self.is_collecting = False
        if self.collect_thread and self.collect_thread.is_alive():
            self.collect_thread.join(timeout=2.0)
        
        logger.info("Сбор логов остановлен")
        
    def _collect_logs_thread(self, log_types, hours_back, callback=None):
        """
        Поток сбора логов
        
        Args:
            log_types (list): Список типов логов для сбора на английском языке
            hours_back (int): Количество часов назад для сбора логов
            callback (function): Функция обратного вызова
        """
        try:
            # В реальной реализации используется win32evtlog
            # В данной реализации создаем тестовые данные для веб-интерфейса
            
            # Определяем временной интервал для запроса
            end_time = datetime.datetime.now()
            start_time = end_time - datetime.timedelta(hours=hours_back)
            
            logger.info(f"Сбор логов в интервале {start_time} - {end_time}")
            
            # Симулируем сбор логов для каждого типа
            for log_type in log_types:
                # Имитация сбора логов
                self._simulate_log_collection(log_type, start_time, end_time, callback)
                
                # Проверка флага остановки
                if not self.is_collecting:
                    break
                    
            logger.info("Сбор логов завершен")
            
        except Exception as e:
            logger.error(f"Ошибка при сборе логов: {str(e)}")
        finally:
            self.is_collecting = False
            
    def _simulate_log_collection(self, log_type, start_time, end_time, callback):
        """
        Имитация сбора логов для демонстрационных целей
        
        Args:
            log_type (str): Тип журнала
            start_time (datetime): Начальное время
            end_time (datetime): Конечное время
            callback (function): Функция обратного вызова
        """
        # Тестовые данные для демонстрации
        event_sources = {
            'System': [
                'Microsoft-Windows-Kernel-General', 'Service Control Manager', 
                'Microsoft-Windows-Power-Troubleshooter', 'DCOM', 'Microsoft-Windows-Kernel-Power'
            ],
            'Application': [
                'Application Hang', 'Application Error', 'Windows Error Reporting', 
                'ESENT', 'Microsoft-Windows-RestartManager'
            ],
            'Security': [
                'Microsoft-Windows-Security-Auditing', 'Microsoft-Windows-Eventlog', 
                'Microsoft-Windows-Audit'
            ],
            'Setup': [
                'Microsoft-Windows-Setup', 'Microsoft-Windows-Servicing', 
                'Microsoft-Windows-WindowsUpdateClient'
            ],
            'DNS Server': [
                'Microsoft-Windows-DNS-Client', 'Microsoft-Windows-DNS-Server', 
                'DNSAPI'
            ],
            'Directory Service': [
                'Microsoft-Windows-ActiveDirectory_DomainService', 'NTDS ISAM', 
                'Microsoft-Windows-GroupPolicy'
            ]
        }
        
        event_samples = {
            'System': [
                'Система была запущена после перезагрузки',
                'Услуга была успешно запущена',
                'Возникла ошибка при инициализации драйвера устройства',
                'Компьютер перешел в спящий режим',
                'Тайм-аут подключения DHCP для сетевого адаптера'
            ],
            'Application': [
                'Приложение завершило работу с ошибкой',
                'Приложение не отвечает',
                'Установка продукта завершена успешно',
                'Обновление приложения доступно',
                'Ошибка при инициализации компонента'
            ],
            'Security': [
                'Успешный вход в систему',
                'Неудачный вход в систему',
                'Создание нового пользователя',
                'Изменение пароля пользователя',
                'Добавление пользователя в группу администраторов'
            ],
            'Setup': [
                'Установка обновления завершена успешно',
                'Ошибка при установке обновления',
                'Запущена установка обновления',
                'Загрузка обновления завершена',
                'Требуется перезагрузка для завершения установки обновлений'
            ],
            'DNS Server': [
                'Не удалось разрешить имя хоста',
                'Сервер DNS запущен',
                'Обновлена зона DNS',
                'Ошибка при загрузке зоны DNS',
                'Запрос DNS отправлен на внешний сервер'
            ],
            'Directory Service': [
                'Успешная репликация домена',
                'Ошибка репликации домена',
                'Изменение групповой политики',
                'Обновление схемы домена',
                'Выполнена операция дефрагментации базы данных Active Directory'
            ]
        }
        
        # Распределение уровней событий (ID -> вес)
        level_weights = {
            1: 0.6,  # Информация (60%)
            2: 0.2,  # Предупреждение (20%)
            3: 0.15,  # Ошибка (15%)
            4: 0.03,  # Успешный аудит (3%)
            5: 0.02   # Неудачный аудит (2%)
        }
        
        sources = event_sources.get(log_type, [])
        samples = event_samples.get(log_type, [])
        
        # Генерируем несколько событий
        num_events = 15  # количество событий для генерации
        time_range = (end_time - start_time).total_seconds()
        
        import random
        for i in range(num_events):
            # Проверка флага остановки
            if not self.is_collecting:
                break
                
            # Генерируем случайное время в заданном интервале
            random_seconds = random.uniform(0, time_range)
            event_time = start_time + datetime.timedelta(seconds=random_seconds)
            
            # Выбираем уровень в соответствии с весами
            level_id = random.choices(list(level_weights.keys()), list(level_weights.values()))[0]
            
            # Создаем событие
            event = {
                'id': random.randint(1000, 9999),
                'time': event_time.strftime('%Y-%m-%d %H:%M:%S'),
                'source': random.choice(sources) if sources else f"Unknown-{log_type}",
                'level': level_id,
                'level_name': self.EVENT_LEVELS.get(level_id, 'Информация'),
                'log_type': log_type,
                'message': random.choice(samples) if samples else f"Событие в журнале {log_type}"
            }
            
            # Отправляем событие через callback, если он задан
            if callback:
                callback(event)
                
            # Небольшая пауза для имитации задержки сбора
            time.sleep(0.1)
            
    def _parse_event(self, event, log_type):
        """
        Преобразование события в словарь с информацией
        
        Args:
            event: Объект события Windows
            log_type (str): Тип журнала
            
        Returns:
            dict: Словарь с информацией о событии
        """
        # В реальной реализации здесь будет парсинг события Windows
        # В тестовой реализации просто возвращаем само событие
        return event
