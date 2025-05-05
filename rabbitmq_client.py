# -*- coding: utf-8 -*-
"""
Модуль для работы с RabbitMQ
"""

import json
import pika
import threading
import time
import logging
import queue
from agent_logger import AgentLogger

class RabbitMQClient:
    """Класс для работы с RabbitMQ"""
    
    def __init__(self):
        """Инициализация клиента RabbitMQ"""
        self.logger = AgentLogger().get_logger('rabbitmq_client')
        self.connection = None
        self.channel = None
        self.is_connected = False
        self.connection_params = {}
        self.publish_queue = queue.Queue()
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.publish_exchange = 'windows_logs'
        self.publish_routing_key = 'system.logs'
        
    def connect(self, host='localhost', port=5672, 
                virtual_host='/', username='guest', password='guest', 
                exchange='windows_logs', routing_key='system.logs',
                auto_reconnect=True):
        """
        Подключение к серверу RabbitMQ
        
        Args:
            host (str): Хост сервера RabbitMQ
            port (int): Порт сервера RabbitMQ
            virtual_host (str): Виртуальный хост
            username (str): Имя пользователя
            password (str): Пароль
            exchange (str): Имя обменника
            routing_key (str): Ключ маршрутизации
            auto_reconnect (bool): Автоматическое переподключение
            
        Returns:
            bool: Успешность подключения
        """
        # Сохраняем параметры для возможного переподключения
        self.connection_params = {
            'host': host,
            'port': port,
            'virtual_host': virtual_host,
            'username': username,
            'password': password,
            'exchange': exchange,
            'routing_key': routing_key,
            'auto_reconnect': auto_reconnect
        }
        
        self.publish_exchange = exchange
        self.publish_routing_key = routing_key
        
        # Закрываем существующее соединение, если оно есть
        self._disconnect()
        
        try:
            self.logger.info(f"Подключение к RabbitMQ: {host}:{port}/{virtual_host}")
            
            # Параметры подключения
            credentials = pika.PlainCredentials(username, password)
            parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=virtual_host,
                credentials=credentials,
                heartbeat=60,
                blocked_connection_timeout=300
            )
            
            # Устанавливаем соединение
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Объявляем обменник
            self.channel.exchange_declare(
                exchange=exchange,
                exchange_type='topic',
                durable=True,
                auto_delete=False
            )
            
            self.is_connected = True
            self.logger.info("Успешное подключение к RabbitMQ")
            
            # Запускаем поток для отправки сообщений
            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._worker_thread)
            self.worker_thread.daemon = True
            self.worker_thread.start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка подключения к RabbitMQ: {str(e)}")
            self.is_connected = False
            return False
    
    def _disconnect(self):
        """Отключение от сервера RabbitMQ"""
        # Останавливаем поток
        if self.worker_thread and self.worker_thread.is_alive():
            self.stop_event.set()
            self.worker_thread.join(timeout=5.0)
        
        # Закрываем соединение
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
            except Exception as e:
                self.logger.error(f"Ошибка при закрытии соединения: {str(e)}")
                
        self.is_connected = False
        self.connection = None
        self.channel = None
    
    def disconnect(self):
        """Отключение от сервера RabbitMQ (публичный метод)"""
        self.logger.info("Отключение от RabbitMQ")
        self._disconnect()
        self.logger.info("Отключено от RabbitMQ")
    
    def publish_log(self, log_data):
        """
        Публикация лога в очередь для последующей отправки
        
        Args:
            log_data (dict): Данные лога для отправки
            
        Returns:
            bool: Успешность добавления в очередь
        """
        if not self.worker_thread or not self.worker_thread.is_alive():
            self.logger.warning("Рабочий поток не запущен, невозможно отправить сообщение")
            return False
            
        try:
            self.publish_queue.put(log_data)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка добавления сообщения в очередь: {str(e)}")
            return False
    
    def _worker_thread(self):
        """Рабочий поток для отправки сообщений"""
        self.logger.info("Запущен поток отправки сообщений")
        
        reconnect_delay = 5  # Начальная задержка для переподключения
        max_reconnect_delay = 60  # Максимальная задержка
        
        while not self.stop_event.is_set():
            try:
                # Если нет подключения, пытаемся переподключиться
                if not self.is_connected and self.connection_params.get('auto_reconnect', True):
                    try:
                        # Подождем перед попыткой переподключения
                        time.sleep(reconnect_delay)
                        
                        # Пытаемся переподключиться
                        self.logger.info(f"Попытка переподключения к RabbitMQ через {reconnect_delay} секунд")
                        params = self.connection_params.copy()
                        auto_reconnect = params.pop('auto_reconnect', True)
                        
                        # Подключаемся с сохраненными параметрами
                        if self.connect(**params, auto_reconnect=auto_reconnect):
                            # Если успешно, сбрасываем задержку
                            reconnect_delay = 5
                        else:
                            # Увеличиваем задержку до максимума
                            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                            
                    except Exception as e:
                        self.logger.error(f"Ошибка при переподключении: {str(e)}")
                        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                        continue
                
                # Если подключены, обрабатываем сообщения из очереди
                if self.is_connected:
                    try:
                        # Получаем сообщение из очереди с таймаутом
                        log_data = self.publish_queue.get(block=True, timeout=1.0)
                        
                        # Преобразуем в JSON
                        message = json.dumps(log_data, ensure_ascii=False)
                        
                        # Отправляем сообщение
                        self.channel.basic_publish(
                            exchange=self.publish_exchange,
                            routing_key=self.publish_routing_key,
                            body=message,
                            properties=pika.BasicProperties(
                                delivery_mode=2,  # Persistent
                                content_type='application/json',
                                content_encoding='utf-8'
                            )
                        )
                        
                        # Помечаем задачу как выполненную
                        self.publish_queue.task_done()
                        
                    except queue.Empty:
                        # Если очередь пуста, продолжаем цикл
                        pass
                        
                    except pika.exceptions.AMQPError as e:
                        # Если произошла ошибка связи с RabbitMQ
                        self.logger.error(f"Ошибка AMQP при отправке сообщения: {str(e)}")
                        self._disconnect()
                        self.is_connected = False
                        
                    except Exception as e:
                        self.logger.error(f"Ошибка при отправке сообщения: {str(e)}")
                        
                else:
                    # Если не подключены, просто ждем
                    time.sleep(1.0)
                    
            except Exception as e:
                self.logger.error(f"Ошибка в рабочем потоке: {str(e)}")
                time.sleep(1.0)
                
        self.logger.info("Поток отправки сообщений остановлен")
