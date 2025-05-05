# -*- coding: utf-8 -*-
"""
Модуль сбора системных логов Windows 10
"""

import win32evtlog
import win32evtlogutil
import win32con
import win32security
import winerror
import datetime
import pythoncom
import threading
import time
import logging
from agent_logger import AgentLogger

class LogCollector:
    """Класс для сбора системных логов Windows"""
    
    # Словарь типов журналов Windows
    LOG_TYPES = {
        'Система': 'System',
        'Приложение': 'Application',
        'Безопасность': 'Security',
        'Настройка': 'Setup',
        'Перенаправление DNS-сервера': 'DNS Server',
        'Active Directory': 'Directory Service'
    }
    
    # Словарь уровней событий
    EVENT_LEVELS = {
        win32con.EVENTLOG_SUCCESS: 'Информация',
        win32con.EVENTLOG_INFORMATION_TYPE: 'Информация',
        win32con.EVENTLOG_WARNING_TYPE: 'Предупреждение',
        win32con.EVENTLOG_ERROR_TYPE: 'Ошибка',
        win32con.EVENTLOG_AUDIT_SUCCESS: 'Успешный аудит',
        win32con.EVENTLOG_AUDIT_FAILURE: 'Неудачный аудит'
    }
    
    def __init__(self):
        """Инициализация коллектора логов"""
        self.logger = AgentLogger().get_logger('log_collector')
        self.is_collecting = False
        self.collect_thread = None
        self.callback = None
        self.stop_event = threading.Event()
        
    def start_collecting(self, log_types, hours_back=1, callback=None):
        """
        Запуск сбора логов в отдельном потоке
        
        Args:
            log_types (list): Список типов логов для сбора на русском языке
            hours_back (int): Количество часов назад для сбора логов
            callback (function): Функция обратного вызова для передачи собранных логов
        """
        if self.is_collecting:
            self.logger.warning("Сбор логов уже запущен")
            return False
            
        self.callback = callback
        self.stop_event.clear()
        self.is_collecting = True
        
        # Конвертируем русские названия в английские для Win32 API
        english_log_types = [self.LOG_TYPES[log_type] for log_type in log_types if log_type in self.LOG_TYPES]
        
        self.logger.info(f"Начало сбора логов типов: {', '.join(log_types)}")
        self.logger.info(f"Период сбора: {hours_back} часов")
        
        # Запускаем сбор в отдельном потоке
        self.collect_thread = threading.Thread(
            target=self._collect_logs_thread, 
            args=(english_log_types, hours_back)
        )
        self.collect_thread.daemon = True
        self.collect_thread.start()
        
        return True
        
    def stop_collecting(self):
        """Остановка сбора логов"""
        if not self.is_collecting:
            return
            
        self.logger.info("Остановка сбора логов")
        self.stop_event.set()
        
        if self.collect_thread and self.collect_thread.is_alive():
            self.collect_thread.join(timeout=5.0)
            
        self.is_collecting = False
        self.logger.info("Сбор логов остановлен")
    
    def _collect_logs_thread(self, log_types, hours_back):
        """
        Поток сбора логов
        
        Args:
            log_types (list): Список типов логов для сбора на английском языке
            hours_back (int): Количество часов назад для сбора логов
        """
        try:
            pythoncom.CoInitialize()  # Инициализация COM для потока
            
            # Вычисляем время начала
            start_time = datetime.datetime.now() - datetime.timedelta(hours=hours_back)
            
            for log_type in log_types:
                if self.stop_event.is_set():
                    break
                    
                self.logger.info(f"Сбор логов типа: {log_type}")
                
                try:
                    # Открываем журнал событий
                    hand = win32evtlog.OpenEventLog(None, log_type)
                    total_records = win32evtlog.GetNumberOfEventLogRecords(hand)
                    
                    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                    events = win32evtlog.ReadEventLog(hand, flags, 0)
                    
                    while events and not self.stop_event.is_set():
                        for event in events:
                            if self.stop_event.is_set():
                                break
                                
                            # Получаем время события
                            event_time = datetime.datetime(
                                event.TimeGenerated.year,
                                event.TimeGenerated.month,
                                event.TimeGenerated.day,
                                event.TimeGenerated.hour,
                                event.TimeGenerated.minute,
                                event.TimeGenerated.second
                            )
                            
                            # Только события после указанного времени
                            if event_time >= start_time:
                                # Преобразуем событие в словарь
                                event_dict = self._parse_event(event, log_type)
                                
                                # Вызываем callback если он задан
                                if self.callback:
                                    self.callback(event_dict)
                            
                        # Читаем следующую порцию событий
                        try:
                            events = win32evtlog.ReadEventLog(hand, flags, 0)
                        except Exception:
                            # Если больше событий нет, выходим из цикла
                            break
                            
                    # Закрываем журнал
                    win32evtlog.CloseEventLog(hand)
                    
                except Exception as e:
                    self.logger.error(f"Ошибка при сборе логов типа {log_type}: {str(e)}")
                    
            self.logger.info("Сбор логов завершен")
            
        except Exception as e:
            self.logger.error(f"Ошибка в потоке сбора логов: {str(e)}")
        finally:
            pythoncom.CoUninitialize()
            self.is_collecting = False
    
    def _parse_event(self, event, log_type):
        """
        Преобразование события в словарь с информацией
        
        Args:
            event: Объект события Windows
            log_type (str): Тип журнала
            
        Returns:
            dict: Словарь с информацией о событии
        """
        # Получение уровня события
        event_level = self.EVENT_LEVELS.get(event.EventType, "Неизвестный")
        
        # Получение времени события
        event_time = datetime.datetime(
            event.TimeGenerated.year,
            event.TimeGenerated.month,
            event.TimeGenerated.day,
            event.TimeGenerated.hour,
            event.TimeGenerated.minute,
            event.TimeGenerated.second
        )
        
        # Получение имени компьютера
        computer_name = event.ComputerName
        
        # Получение сообщения события
        try:
            message = win32evtlogutil.SafeFormatMessage(event, log_type)
        except Exception:
            message = "Не удалось получить сообщение"
        
        # Получение имени источника
        source_name = event.SourceName
        
        # Получение ID события
        event_id = event.EventID & 0xFFFF  # Младшие 16 бит
        
        # Получение категории
        category = event.EventCategory
        
        # Формируем словарь с событием
        event_dict = {
            'id': event_id,
            'уровень': event_level,
            'время': event_time.strftime('%Y-%m-%d %H:%M:%S'),
            'источник': source_name,
            'категория': category,
            'сообщение': message,
            'компьютер': computer_name,
            'журнал': log_type
        }
        
        return event_dict
