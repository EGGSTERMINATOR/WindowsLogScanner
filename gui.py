# -*- coding: utf-8 -*-
"""
Модуль графического интерфейса для агента сбора логов
"""

import os
import sys
import datetime
import time
import json
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTabWidget, QLabel, QPushButton, QComboBox, 
                            QCheckBox, QGroupBox, QTableWidget, QTableWidgetItem,
                            QLineEdit, QTextEdit, QSpinBox, QFileDialog, 
                            QMessageBox, QHeaderView, QSplitter, QMenu, QAction,
                            QToolBar, QStatusBar, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QColor, QFont, QPixmap, QTextCursor
import configparser
import traceback

from log_collector import LogCollector
from rabbitmq_client import RabbitMQClient
from agent_logger import AgentLogger
from resources.icons import get_icon
from utils import create_default_config

class LogCollectorThread(QThread):
    """Поток для сбора логов"""
    
    # Сигнал для передачи собранного лога
    log_collected = pyqtSignal(dict)
    
    def __init__(self, log_collector, log_types, hours_back):
        """
        Инициализация потока
        
        Args:
            log_collector (LogCollector): Экземпляр коллектора логов
            log_types (list): Список типов логов для сбора
            hours_back (int): Количество часов назад для сбора логов
        """
        super().__init__()
        self.log_collector = log_collector
        self.log_types = log_types
        self.hours_back = hours_back
        
    def run(self):
        """Запуск потока сбора логов"""
        self.log_collector.start_collecting(
            log_types=self.log_types,
            hours_back=self.hours_back,
            callback=self._on_log_collected
        )
        
    def _on_log_collected(self, log_data):
        """Обработчик события сбора лога"""
        self.log_collected.emit(log_data)
        
    def stop(self):
        """Остановка потока"""
        self.log_collector.stop_collecting()
        self.wait()


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        """Инициализация главного окна"""
        super().__init__()
        
        # Инициализация компонентов
        self.logger = AgentLogger().get_logger('gui')
        self.log_collector = LogCollector()
        self.rabbitmq_client = RabbitMQClient()
        self.collected_logs = []
        self.collector_thread = None
        
        # Загрузка конфигурации
        self.config = configparser.ConfigParser()
        self.config_path = 'config.ini'
        
        if not os.path.exists(self.config_path):
            self.logger.info("Файл конфигурации не найден, создаем новый")
            create_default_config(self.config_path)
            
        self.config.read(self.config_path, encoding='utf-8')
        
        # Установка параметров окна
        self.setWindowTitle("Агент сбора системных логов Windows")
        self.setGeometry(100, 100, 1200, 700)
        
        # Создание интерфейса
        self._create_ui()
        
        # Восстановление настроек из конфигурации
        self._load_settings_from_config()
        
        # Автоматическое подключение к RabbitMQ, если указано в настройках
        if self.config.getboolean('RabbitMQ', 'autoconnect', fallback=False):
            self._connect_to_rabbitmq()
            
        self.logger.info("Приложение запущено")
        
    def _create_ui(self):
        """Создание пользовательского интерфейса"""
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной вертикальный лейаут
        main_layout = QVBoxLayout(central_widget)
        
        # Создаем вкладки
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Вкладка сбора логов
        self.tab_logs = QWidget()
        self.tabs.addTab(self.tab_logs, "Сбор логов")
        
        # Вкладка настроек
        self.tab_settings = QWidget()
        self.tabs.addTab(self.tab_settings, "Настройки")
        
        # Вкладка журнала агента
        self.tab_agent_log = QWidget()
        self.tabs.addTab(self.tab_agent_log, "Журнал агента")
        
        # Добавляем вкладки на основной лейаут
        main_layout.addWidget(self.tabs)
        
        # Инициализация вкладок
        self._init_logs_tab()
        self._init_settings_tab()
        self._init_agent_log_tab()
        
        # Создаем статус бар
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Создаем индикатор состояния подключения RabbitMQ
        self.rabbitmq_status_label = QLabel("RabbitMQ: Не подключен")
        self.statusBar.addPermanentWidget(self.rabbitmq_status_label)
        
        # Таймер для обновления статуса
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(5000)  # Обновление каждые 5 секунд
        
        # Создаем панель инструментов
        self.toolbar = QToolBar("Основная панель")
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
        # Добавляем действия в панель инструментов
        action_start = QAction(get_icon("play"), "Начать сбор", self)
        action_start.triggered.connect(self._start_collecting)
        self.toolbar.addAction(action_start)
        
        action_stop = QAction(get_icon("stop"), "Остановить сбор", self)
        action_stop.triggered.connect(self._stop_collecting)
        self.toolbar.addAction(action_stop)
        
        self.toolbar.addSeparator()
        
        action_connect = QAction(get_icon("connect"), "Подключиться к RabbitMQ", self)
        action_connect.triggered.connect(self._connect_to_rabbitmq)
        self.toolbar.addAction(action_connect)
        
        action_disconnect = QAction(get_icon("disconnect"), "Отключиться от RabbitMQ", self)
        action_disconnect.triggered.connect(self._disconnect_from_rabbitmq)
        self.toolbar.addAction(action_disconnect)
        
        self.toolbar.addSeparator()
        
        action_clear = QAction(get_icon("clear"), "Очистить собранные логи", self)
        action_clear.triggered.connect(self._clear_logs)
        self.toolbar.addAction(action_clear)
        
        action_save = QAction(get_icon("save"), "Сохранить логи в файл", self)
        action_save.triggered.connect(self._save_logs_to_file)
        self.toolbar.addAction(action_save)
        
        self.toolbar.addSeparator()
        
        action_exit = QAction(get_icon("exit"), "Выход", self)
        action_exit.triggered.connect(self.close)
        self.toolbar.addAction(action_exit)
        
    def _init_logs_tab(self):
        """Инициализация вкладки сбора логов"""
        layout = QVBoxLayout(self.tab_logs)
        
        # Верхняя панель с настройками сбора
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        
        # Группа выбора журналов
        logs_group = QGroupBox("Журналы для сбора")
        logs_layout = QVBoxLayout(logs_group)
        
        self.cb_system = QCheckBox("Система")
        self.cb_system.setChecked(True)
        logs_layout.addWidget(self.cb_system)
        
        self.cb_application = QCheckBox("Приложение")
        self.cb_application.setChecked(True)
        logs_layout.addWidget(self.cb_application)
        
        self.cb_security = QCheckBox("Безопасность")
        logs_layout.addWidget(self.cb_security)
        
        self.cb_setup = QCheckBox("Настройка")
        logs_layout.addWidget(self.cb_setup)
        
        self.cb_dns = QCheckBox("Перенаправление DNS-сервера")
        logs_layout.addWidget(self.cb_dns)
        
        self.cb_active_directory = QCheckBox("Active Directory")
        logs_layout.addWidget(self.cb_active_directory)
        
        top_layout.addWidget(logs_group)
        
        # Группа периода сбора
        period_group = QGroupBox("Период сбора")
        period_layout = QVBoxLayout(period_group)
        
        period_label = QLabel("Количество часов назад:")
        period_layout.addWidget(period_label)
        
        self.spin_hours = QSpinBox()
        self.spin_hours.setRange(1, 168)  # От 1 часа до 7 дней
        self.spin_hours.setValue(1)
        period_layout.addWidget(self.spin_hours)
        
        filter_label = QLabel("Фильтр уровня событий:")
        period_layout.addWidget(filter_label)
        
        self.combo_level = QComboBox()
        self.combo_level.addItem("Все")
        self.combo_level.addItem("Информация")
        self.combo_level.addItem("Предупреждение")
        self.combo_level.addItem("Ошибка")
        self.combo_level.addItem("Успешный аудит")
        self.combo_level.addItem("Неудачный аудит")
        period_layout.addWidget(self.combo_level)
        
        period_layout.addStretch()
        
        top_layout.addWidget(period_group)
        
        # Группа управления
        control_group = QGroupBox("Управление")
        control_layout = QVBoxLayout(control_group)
        
        self.btn_start = QPushButton("Начать сбор")
        self.btn_start.clicked.connect(self._start_collecting)
        control_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("Остановить сбор")
        self.btn_stop.clicked.connect(self._stop_collecting)
        self.btn_stop.setEnabled(False)
        control_layout.addWidget(self.btn_stop)
        
        self.chk_send_rabbitmq = QCheckBox("Отправлять в RabbitMQ")
        control_layout.addWidget(self.chk_send_rabbitmq)
        
        control_layout.addStretch()
        
        top_layout.addWidget(control_group)
        
        # Поиск
        search_group = QGroupBox("Поиск")
        search_layout = QVBoxLayout(search_group)
        
        search_label = QLabel("Текст для поиска:")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите текст для поиска...")
        self.search_input.textChanged.connect(self._filter_logs)
        search_layout.addWidget(self.search_input)
        
        self.btn_clear_search = QPushButton("Очистить")
        self.btn_clear_search.clicked.connect(lambda: self.search_input.clear())
        search_layout.addWidget(self.btn_clear_search)
        
        search_layout.addStretch()
        
        top_layout.addWidget(search_group)
        
        layout.addWidget(top_panel)
        
        # Таблица с логами
        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(6)
        self.logs_table.setHorizontalHeaderLabels([
            "Время", "Уровень", "Источник", "Журнал", "ID", "Сообщение"
        ])
        # Растягиваем последнюю колонку
        self.logs_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        # Устанавливаем ресайз для остальных колонок
        for i in range(5):
            self.logs_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # Контекстное меню для таблицы
        self.logs_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.logs_table.customContextMenuRequested.connect(self._show_log_context_menu)
        
        layout.addWidget(self.logs_table)
        
        # Индикатор статуса сбора
        self.status_label = QLabel("Статус: Готов к сбору логов")
        layout.addWidget(self.status_label)
        
    def _init_settings_tab(self):
        """Инициализация вкладки настроек"""
        layout = QVBoxLayout(self.tab_settings)
        
        # Настройки RabbitMQ
        rabbitmq_group = QGroupBox("Настройки RabbitMQ")
        rabbitmq_layout = QVBoxLayout(rabbitmq_group)
        
        # Хост
        host_layout = QHBoxLayout()
        host_label = QLabel("Хост:")
        host_layout.addWidget(host_label)
        self.rabbitmq_host = QLineEdit()
        self.rabbitmq_host.setText("localhost")
        host_layout.addWidget(self.rabbitmq_host)
        rabbitmq_layout.addLayout(host_layout)
        
        # Порт
        port_layout = QHBoxLayout()
        port_label = QLabel("Порт:")
        port_layout.addWidget(port_label)
        self.rabbitmq_port = QSpinBox()
        self.rabbitmq_port.setRange(1, 65535)
        self.rabbitmq_port.setValue(5672)
        port_layout.addWidget(self.rabbitmq_port)
        rabbitmq_layout.addLayout(port_layout)
        
        # Виртуальный хост
        vhost_layout = QHBoxLayout()
        vhost_label = QLabel("Виртуальный хост:")
        vhost_layout.addWidget(vhost_label)
        self.rabbitmq_vhost = QLineEdit()
        self.rabbitmq_vhost.setText("/")
        vhost_layout.addWidget(self.rabbitmq_vhost)
        rabbitmq_layout.addLayout(vhost_layout)
        
        # Имя пользователя
        username_layout = QHBoxLayout()
        username_label = QLabel("Имя пользователя:")
        username_layout.addWidget(username_label)
        self.rabbitmq_username = QLineEdit()
        self.rabbitmq_username.setText("guest")
        username_layout.addWidget(self.rabbitmq_username)
        rabbitmq_layout.addLayout(username_layout)
        
        # Пароль
        password_layout = QHBoxLayout()
        password_label = QLabel("Пароль:")
        password_layout.addWidget(password_label)
        self.rabbitmq_password = QLineEdit()
        self.rabbitmq_password.setText("guest")
        self.rabbitmq_password.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.rabbitmq_password)
        rabbitmq_layout.addLayout(password_layout)
        
        # Обменник
        exchange_layout = QHBoxLayout()
        exchange_label = QLabel("Обменник:")
        exchange_layout.addWidget(exchange_label)
        self.rabbitmq_exchange = QLineEdit()
        self.rabbitmq_exchange.setText("windows_logs")
        exchange_layout.addWidget(self.rabbitmq_exchange)
        rabbitmq_layout.addLayout(exchange_layout)
        
        # Ключ маршрутизации
        routing_key_layout = QHBoxLayout()
        routing_key_label = QLabel("Ключ маршрутизации:")
        routing_key_layout.addWidget(routing_key_label)
        self.rabbitmq_routing_key = QLineEdit()
        self.rabbitmq_routing_key.setText("system.logs")
        routing_key_layout.addWidget(self.rabbitmq_routing_key)
        rabbitmq_layout.addLayout(routing_key_layout)
        
        # Автоподключение
        self.rabbitmq_autoconnect = QCheckBox("Автоматически подключаться при запуске")
        rabbitmq_layout.addWidget(self.rabbitmq_autoconnect)
        
        # Кнопки подключения/отключения
        rabbitmq_buttons_layout = QHBoxLayout()
        
        self.btn_connect = QPushButton("Подключиться")
        self.btn_connect.clicked.connect(self._connect_to_rabbitmq)
        rabbitmq_buttons_layout.addWidget(self.btn_connect)
        
        self.btn_disconnect = QPushButton("Отключиться")
        self.btn_disconnect.clicked.connect(self._disconnect_from_rabbitmq)
        self.btn_disconnect.setEnabled(False)
        rabbitmq_buttons_layout.addWidget(self.btn_disconnect)
        
        rabbitmq_layout.addLayout(rabbitmq_buttons_layout)
        
        layout.addWidget(rabbitmq_group)
        
        # Настройки журналирования
        logging_group = QGroupBox("Настройки журналирования")
        logging_layout = QVBoxLayout(logging_group)
        
        # Директория для журналов
        log_dir_layout = QHBoxLayout()
        log_dir_label = QLabel("Директория для журналов:")
        log_dir_layout.addWidget(log_dir_label)
        self.log_dir = QLineEdit()
        self.log_dir.setText("logs")
        log_dir_layout.addWidget(self.log_dir)
        self.btn_browse_log_dir = QPushButton("Обзор...")
        self.btn_browse_log_dir.clicked.connect(self._browse_log_dir)
        log_dir_layout.addWidget(self.btn_browse_log_dir)
        logging_layout.addLayout(log_dir_layout)
        
        layout.addWidget(logging_group)
        
        # Кнопки сохранения/загрузки настроек
        settings_buttons_layout = QHBoxLayout()
        
        self.btn_save_settings = QPushButton("Сохранить настройки")
        self.btn_save_settings.clicked.connect(self._save_settings)
        settings_buttons_layout.addWidget(self.btn_save_settings)
        
        self.btn_load_settings = QPushButton("Загрузить настройки")
        self.btn_load_settings.clicked.connect(self._load_settings_from_config)
        settings_buttons_layout.addWidget(self.btn_load_settings)
        
        layout.addLayout(settings_buttons_layout)
        
        # Добавляем растягивающий элемент
        layout.addStretch()
        
    def _init_agent_log_tab(self):
        """Инициализация вкладки журнала агента"""
        layout = QVBoxLayout(self.tab_agent_log)
        
        # Текстовое поле для отображения журнала
        self.agent_log_text = QTextEdit()
        self.agent_log_text.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.agent_log_text.setFont(font)
        layout.addWidget(self.agent_log_text)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.btn_refresh_log = QPushButton("Обновить")
        self.btn_refresh_log.clicked.connect(self._refresh_agent_log)
        buttons_layout.addWidget(self.btn_refresh_log)
        
        self.btn_clear_log = QPushButton("Очистить отображение")
        self.btn_clear_log.clicked.connect(lambda: self.agent_log_text.clear())
        buttons_layout.addWidget(self.btn_clear_log)
        
        layout.addLayout(buttons_layout)
        
        # Первоначальное заполнение журнала
        self._refresh_agent_log()
        
    def _load_settings_from_config(self):
        """Загрузка настроек из конфигурационного файла"""
        try:
            # RabbitMQ настройки
            self.rabbitmq_host.setText(self.config.get('RabbitMQ', 'host', fallback='localhost'))
            self.rabbitmq_port.setValue(self.config.getint('RabbitMQ', 'port', fallback=5672))
            self.rabbitmq_vhost.setText(self.config.get('RabbitMQ', 'vhost', fallback='/'))
            self.rabbitmq_username.setText(self.config.get('RabbitMQ', 'username', fallback='guest'))
            self.rabbitmq_password.setText(self.config.get('RabbitMQ', 'password', fallback='guest'))
            self.rabbitmq_exchange.setText(self.config.get('RabbitMQ', 'exchange', fallback='windows_logs'))
            self.rabbitmq_routing_key.setText(self.config.get('RabbitMQ', 'routing_key', fallback='system.logs'))
            self.rabbitmq_autoconnect.setChecked(self.config.getboolean('RabbitMQ', 'autoconnect', fallback=False))
            
            # Настройки логирования
            self.log_dir.setText(self.config.get('Logging', 'directory', fallback='logs'))
            
            # Настройки сбора логов
            self.cb_system.setChecked(self.config.getboolean('Logs', 'system', fallback=True))
            self.cb_application.setChecked(self.config.getboolean('Logs', 'application', fallback=True))
            self.cb_security.setChecked(self.config.getboolean('Logs', 'security', fallback=False))
            self.cb_setup.setChecked(self.config.getboolean('Logs', 'setup', fallback=False))
            self.cb_dns.setChecked(self.config.getboolean('Logs', 'dns', fallback=False))
            self.cb_active_directory.setChecked(self.config.getboolean('Logs', 'active_directory', fallback=False))
            
            self.spin_hours.setValue(self.config.getint('Logs', 'hours_back', fallback=1))
            
            level_index = self.config.getint('Logs', 'level_filter', fallback=0)
            self.combo_level.setCurrentIndex(level_index)
            
            self.chk_send_rabbitmq.setChecked(self.config.getboolean('Logs', 'send_to_rabbitmq', fallback=False))
            
            self.logger.info("Настройки загружены из конфигурационного файла")
            
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке настроек: {str(e)}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить настройки: {str(e)}")
    
    def _save_settings(self):
        """Сохранение настроек в конфигурационный файл"""
        try:
            # RabbitMQ настройки
            if not self.config.has_section('RabbitMQ'):
                self.config.add_section('RabbitMQ')
                
            self.config.set('RabbitMQ', 'host', self.rabbitmq_host.text())
            self.config.set('RabbitMQ', 'port', str(self.rabbitmq_port.value()))
            self.config.set('RabbitMQ', 'vhost', self.rabbitmq_vhost.text())
            self.config.set('RabbitMQ', 'username', self.rabbitmq_username.text())
            self.config.set('RabbitMQ', 'password', self.rabbitmq_password.text())
            self.config.set('RabbitMQ', 'exchange', self.rabbitmq_exchange.text())
            self.config.set('RabbitMQ', 'routing_key', self.rabbitmq_routing_key.text())
            self.config.set('RabbitMQ', 'autoconnect', str(self.rabbitmq_autoconnect.isChecked()))
            
            # Настройки логирования
            if not self.config.has_section('Logging'):
                self.config.add_section('Logging')
                
            self.config.set('Logging', 'directory', self.log_dir.text())
            
            # Настройки сбора логов
            if not self.config.has_section('Logs'):
                self.config.add_section('Logs')
                
            self.config.set('Logs', 'system', str(self.cb_system.isChecked()))
            self.config.set('Logs', 'application', str(self.cb_application.isChecked()))
            self.config.set('Logs', 'security', str(self.cb_security.isChecked()))
            self.config.set('Logs', 'setup', str(self.cb_setup.isChecked()))
            self.config.set('Logs', 'dns', str(self.cb_dns.isChecked()))
            self.config.set('Logs', 'active_directory', str(self.cb_active_directory.isChecked()))
            
            self.config.set('Logs', 'hours_back', str(self.spin_hours.value()))
            self.config.set('Logs', 'level_filter', str(self.combo_level.currentIndex()))
            self.config.set('Logs', 'send_to_rabbitmq', str(self.chk_send_rabbitmq.isChecked()))
            
            # Сохраняем конфигурацию в файл
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
                
            self.logger.info("Настройки сохранены в конфигурационный файл")
            QMessageBox.information(self, "Сохранение настроек", "Настройки успешно сохранены")
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении настроек: {str(e)}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")
    
    def _browse_log_dir(self):
        """Выбор директории для журналов"""
        directory = QFileDialog.getExistingDirectory(
            self, "Выберите директорию для журналов", self.log_dir.text()
        )
        
        if directory:
            self.log_dir.setText(directory)
    
    def _connect_to_rabbitmq(self):
        """Подключение к серверу RabbitMQ"""
        try:
            host = self.rabbitmq_host.text()
            port = self.rabbitmq_port.value()
            vhost = self.rabbitmq_vhost.text()
            username = self.rabbitmq_username.text()
            password = self.rabbitmq_password.text()
            exchange = self.rabbitmq_exchange.text()
            routing_key = self.rabbitmq_routing_key.text()
            
            # Отключаем кнопки на время подключения
            self.btn_connect.setEnabled(False)
            
            # Пытаемся подключиться
            success = self.rabbitmq_client.connect(
                host=host,
                port=port,
                virtual_host=vhost,
                username=username,
                password=password,
                exchange=exchange,
                routing_key=routing_key
            )
            
            if success:
                self.logger.info(f"Успешное подключение к RabbitMQ: {host}:{port}/{vhost}")
                self.rabbitmq_status_label.setText(f"RabbitMQ: Подключен ({host}:{port})")
                self.btn_connect.setEnabled(False)
                self.btn_disconnect.setEnabled(True)
                QMessageBox.information(self, "Подключение", "Успешное подключение к RabbitMQ")
            else:
                self.logger.error(f"Не удалось подключиться к RabbitMQ: {host}:{port}/{vhost}")
                self.rabbitmq_status_label.setText("RabbitMQ: Не подключен")
                self.btn_connect.setEnabled(True)
                QMessageBox.warning(self, "Ошибка подключения", 
                                   f"Не удалось подключиться к RabbitMQ: {host}:{port}/{vhost}")
        
        except Exception as e:
            self.logger.error(f"Ошибка при подключении к RabbitMQ: {str(e)}")
            self.rabbitmq_status_label.setText("RabbitMQ: Ошибка подключения")
            self.btn_connect.setEnabled(True)
            QMessageBox.warning(self, "Ошибка", f"Ошибка при подключении к RabbitMQ: {str(e)}")
    
    def _disconnect_from_rabbitmq(self):
        """Отключение от сервера RabbitMQ"""
        try:
            self.rabbitmq_client.disconnect()
            self.rabbitmq_status_label.setText("RabbitMQ: Не подключен")
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
            self.logger.info("Отключено от RabbitMQ")
            
        except Exception as e:
            self.logger.error(f"Ошибка при отключении от RabbitMQ: {str(e)}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка при отключении от RabbitMQ: {str(e)}")
    
    def _start_collecting(self):
        """Начало сбора логов"""
        try:
            # Проверяем, что хотя бы один тип логов выбран
            log_types = []
            if self.cb_system.isChecked():
                log_types.append("Система")
            if self.cb_application.isChecked():
                log_types.append("Приложение")
            if self.cb_security.isChecked():
                log_types.append("Безопасность")
            if self.cb_setup.isChecked():
                log_types.append("Настройка")
            if self.cb_dns.isChecked():
                log_types.append("Перенаправление DNS-сервера")
            if self.cb_active_directory.isChecked():
                log_types.append("Active Directory")
                
            if not log_types:
                QMessageBox.warning(self, "Внимание", "Необходимо выбрать хотя бы один тип логов")
                return
                
            # Получаем период сбора
            hours_back = self.spin_hours.value()
            
            # Меняем статус интерфейса
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.status_label.setText("Статус: Сбор логов...")
            
            # Очищаем таблицу и список логов
            self.logs_table.setRowCount(0)
            self.collected_logs = []
            
            # Запускаем поток сбора логов
            self.collector_thread = LogCollectorThread(
                self.log_collector, log_types, hours_back
            )
            self.collector_thread.log_collected.connect(self._on_log_collected)
            self.collector_thread.start()
            
            self.logger.info(f"Начат сбор логов типов: {', '.join(log_types)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при запуске сбора логов: {str(e)}")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.status_label.setText("Статус: Ошибка сбора логов")
            QMessageBox.warning(self, "Ошибка", f"Не удалось запустить сбор логов: {str(e)}")
    
    def _stop_collecting(self):
        """Остановка сбора логов"""
        try:
            if self.collector_thread and self.collector_thread.isRunning():
                self.status_label.setText("Статус: Остановка сбора логов...")
                self.collector_thread.stop()
                
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.status_label.setText("Статус: Сбор логов остановлен")
            self.logger.info("Сбор логов остановлен")
            
        except Exception as e:
            self.logger.error(f"Ошибка при остановке сбора логов: {str(e)}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка при остановке сбора логов: {str(e)}")
    
    def _on_log_collected(self, log_data):
        """Обработчик события сбора лога"""
        try:
            # Получаем выбранный уровень фильтрации
            level_filter = self.combo_level.currentText()
            
            # Если выбран фильтр по уровню и уровень не соответствует
            if level_filter != "Все" and log_data['уровень'] != level_filter:
                return
                
            # Добавляем лог в список
            self.collected_logs.append(log_data)
            
            # Добавляем строку в таблицу
            row_position = self.logs_table.rowCount()
            self.logs_table.insertRow(row_position)
            
            # Заполняем ячейки таблицы
            self.logs_table.setItem(row_position, 0, QTableWidgetItem(log_data['время']))
            
            level_item = QTableWidgetItem(log_data['уровень'])
            # Устанавливаем цвет в зависимости от уровня
            if log_data['уровень'] == 'Ошибка':
                level_item.setForeground(QColor(255, 0, 0))
            elif log_data['уровень'] == 'Предупреждение':
                level_item.setForeground(QColor(255, 165, 0))
            elif log_data['уровень'] == 'Информация':
                level_item.setForeground(QColor(0, 128, 0))
            self.logs_table.setItem(row_position, 1, level_item)
            
            self.logs_table.setItem(row_position, 2, QTableWidgetItem(log_data['источник']))
            self.logs_table.setItem(row_position, 3, QTableWidgetItem(log_data['журнал']))
            self.logs_table.setItem(row_position, 4, QTableWidgetItem(str(log_data['id'])))
            
            # Сокращаем сообщение для отображения в таблице
            message = log_data['сообщение']
            if len(message) > 100:
                message = message[:100] + "..."
            self.logs_table.setItem(row_position, 5, QTableWidgetItem(message))
            
            # Отправляем в RabbitMQ, если включена опция
            if self.chk_send_rabbitmq.isChecked() and self.rabbitmq_client.is_connected:
                self.rabbitmq_client.publish_log(log_data)
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке собранного лога: {str(e)}")
    
    def _filter_logs(self):
        """Фильтрация логов по введенному тексту"""
        search_text = self.search_input.text().lower()
        
        # Если текст поиска пустой, показываем все логи
        if not search_text:
            self.logs_table.setRowCount(0)
            for log_data in self.collected_logs:
                row_position = self.logs_table.rowCount()
                self.logs_table.insertRow(row_position)
                
                self.logs_table.setItem(row_position, 0, QTableWidgetItem(log_data['время']))
                
                level_item = QTableWidgetItem(log_data['уровень'])
                if log_data['уровень'] == 'Ошибка':
                    level_item.setForeground(QColor(255, 0, 0))
                elif log_data['уровень'] == 'Предупреждение':
                    level_item.setForeground(QColor(255, 165, 0))
                elif log_data['уровень'] == 'Информация':
                    level_item.setForeground(QColor(0, 128, 0))
                self.logs_table.setItem(row_position, 1, level_item)
                
                self.logs_table.setItem(row_position, 2, QTableWidgetItem(log_data['источник']))
                self.logs_table.setItem(row_position, 3, QTableWidgetItem(log_data['журнал']))
                self.logs_table.setItem(row_position, 4, QTableWidgetItem(str(log_data['id'])))
                
                message = log_data['сообщение']
                if len(message) > 100:
                    message = message[:100] + "..."
                self.logs_table.setItem(row_position, 5, QTableWidgetItem(message))
            
            return
            
        # Фильтруем логи по тексту
        self.logs_table.setRowCount(0)
        for log_data in self.collected_logs:
            # Проверяем наличие текста в каждом поле
            if (search_text in str(log_data['id']).lower() or
                search_text in log_data['уровень'].lower() or
                search_text in log_data['источник'].lower() or
                search_text in log_data['журнал'].lower() or
                search_text in log_data['сообщение'].lower()):
                
                row_position = self.logs_table.rowCount()
                self.logs_table.insertRow(row_position)
                
                self.logs_table.setItem(row_position, 0, QTableWidgetItem(log_data['время']))
                
                level_item = QTableWidgetItem(log_data['уровень'])
                if log_data['уровень'] == 'Ошибка':
                    level_item.setForeground(QColor(255, 0, 0))
                elif log_data['уровень'] == 'Предупреждение':
                    level_item.setForeground(QColor(255, 165, 0))
                elif log_data['уровень'] == 'Информация':
                    level_item.setForeground(QColor(0, 128, 0))
                self.logs_table.setItem(row_position, 1, level_item)
                
                self.logs_table.setItem(row_position, 2, QTableWidgetItem(log_data['источник']))
                self.logs_table.setItem(row_position, 3, QTableWidgetItem(log_data['журнал']))
                self.logs_table.setItem(row_position, 4, QTableWidgetItem(str(log_data['id'])))
                
                message = log_data['сообщение']
                if len(message) > 100:
                    message = message[:100] + "..."
                self.logs_table.setItem(row_position, 5, QTableWidgetItem(message))
    
    def _clear_logs(self):
        """Очистка собранных логов"""
        if self.collected_logs:
            reply = QMessageBox.question(
                self, "Очистка логов",
                "Вы уверены, что хотите очистить все собранные логи?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.logs_table.setRowCount(0)
                self.collected_logs = []
                self.logger.info("Собранные логи очищены")
    
    def _save_logs_to_file(self):
        """Сохранение логов в файл"""
        if not self.collected_logs:
            QMessageBox.warning(self, "Внимание", "Нет собранных логов для сохранения")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить логи", "", "JSON Files (*.json);;CSV Files (*.csv);;Text Files (*.txt)"
        )
        
        if not file_path:
            return
            
        try:
            # Определяем формат файла по расширению
            ext = file_path.split('.')[-1].lower()
            
            if ext == 'json':
                # Сохраняем в JSON
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.collected_logs, f, ensure_ascii=False, indent=4)
                    
            elif ext == 'csv':
                # Сохраняем в CSV
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Записываем заголовки
                    writer.writerow(['ID', 'Уровень', 'Время', 'Источник', 'Категория', 
                                     'Сообщение', 'Компьютер', 'Журнал'])
                    # Записываем данные
                    for log in self.collected_logs:
                        writer.writerow([
                            log['id'], log['уровень'], log['время'], log['источник'],
                            log['категория'], log['сообщение'], log['компьютер'], log['журнал']
                        ])
                        
            elif ext == 'txt':
                # Сохраняем в текстовый файл
                with open(file_path, 'w', encoding='utf-8') as f:
                    for log in self.collected_logs:
                        f.write(f"ID: {log['id']}\n")
                        f.write(f"Уровень: {log['уровень']}\n")
                        f.write(f"Время: {log['время']}\n")
                        f.write(f"Источник: {log['источник']}\n")
                        f.write(f"Категория: {log['категория']}\n")
                        f.write(f"Журнал: {log['журнал']}\n")
                        f.write(f"Компьютер: {log['компьютер']}\n")
                        f.write(f"Сообщение: {log['сообщение']}\n")
                        f.write("-" * 50 + "\n")
            
            else:
                raise ValueError(f"Неподдерживаемый формат файла: {ext}")
                
            self.logger.info(f"Логи сохранены в файл: {file_path}")
            QMessageBox.information(self, "Сохранение логов", f"Логи успешно сохранены в файл:\n{file_path}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении логов в файл: {str(e)}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить логи в файл: {str(e)}")
    
    def _show_log_context_menu(self, position):
        """Отображение контекстного меню для таблицы логов"""
        # Создаем меню
        menu = QMenu()
        
        # Получаем текущую строку
        current_row = self.logs_table.currentRow()
        
        if current_row >= 0:
            # Добавляем действие для просмотра подробной информации
            action_view = QAction("Просмотреть подробности", self)
            action_view.triggered.connect(lambda: self._show_log_details(current_row))
            menu.addAction(action_view)
            
            # Добавляем действие для копирования сообщения
            action_copy = QAction("Копировать сообщение", self)
            action_copy.triggered.connect(lambda: self._copy_log_message(current_row))
            menu.addAction(action_copy)
            
            # Добавляем действие для отправки в RabbitMQ
            if self.rabbitmq_client.is_connected:
                action_send = QAction("Отправить в RabbitMQ", self)
                action_send.triggered.connect(lambda: self._send_log_to_rabbitmq(current_row))
                menu.addAction(action_send)
            
        # Показываем меню
        menu.exec_(self.logs_table.viewport().mapToGlobal(position))
    
    def _show_log_details(self, row):
        """Отображение подробной информации о логе"""
        if row < 0 or row >= len(self.collected_logs):
            return
            
        log_data = self.collected_logs[row]
        
        # Создаем диалог
        dialog = QDialog(self)
        dialog.setWindowTitle("Подробная информация о событии")
        dialog.resize(600, 400)
        
        # Создаем вертикальный лейаут
        layout = QVBoxLayout(dialog)
        
        # Создаем текстовое поле
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        # Форматируем текст
        html = "<h3>Подробная информация о событии</h3>"
        html += f"<p><b>ID события:</b> {log_data['id']}</p>"
        html += f"<p><b>Уровень:</b> {log_data['уровень']}</p>"
        html += f"<p><b>Время:</b> {log_data['время']}</p>"
        html += f"<p><b>Источник:</b> {log_data['источник']}</p>"
        html += f"<p><b>Категория:</b> {log_data['категория']}</p>"
        html += f"<p><b>Журнал:</b> {log_data['журнал']}</p>"
        html += f"<p><b>Компьютер:</b> {log_data['компьютер']}</p>"
        html += "<p><b>Сообщение:</b></p>"
        html += f"<pre>{log_data['сообщение']}</pre>"
        
        text_edit.setHtml(html)
        layout.addWidget(text_edit)
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        # Показываем диалог
        dialog.exec_()
    
    def _copy_log_message(self, row):
        """Копирование сообщения в буфер обмена"""
        if row < 0 or row >= len(self.collected_logs):
            return
            
        log_data = self.collected_logs[row]
        
        # Копируем сообщение в буфер обмена
        from PyQt5.QtGui import QGuiApplication
        QGuiApplication.clipboard().setText(log_data['сообщение'])
        
        self.status_label.setText("Сообщение скопировано в буфер обмена")
    
    def _send_log_to_rabbitmq(self, row):
        """Отправка лога в RabbitMQ"""
        if row < 0 or row >= len(self.collected_logs):
            return
            
        if not self.rabbitmq_client.is_connected:
            QMessageBox.warning(self, "Ошибка", "Необходимо подключиться к RabbitMQ")
            return
            
        log_data = self.collected_logs[row]
        
        # Отправляем лог
        if self.rabbitmq_client.publish_log(log_data):
            self.status_label.setText("Лог отправлен в RabbitMQ")
        else:
            self.status_label.setText("Ошибка отправки лога в RabbitMQ")
    
    def _refresh_agent_log(self):
        """Обновление журнала агента"""
        try:
            # Получаем записи журнала
            log_entries = AgentLogger().get_log_entries(max_entries=1000)
            
            # Очищаем текстовое поле
            self.agent_log_text.clear()
            
            # Заполняем текстовое поле
            for entry in log_entries:
                # Раскрашиваем в зависимости от уровня
                if " - ERROR - " in entry:
                    self.agent_log_text.setTextColor(QColor(255, 0, 0))
                elif " - WARNING - " in entry:
                    self.agent_log_text.setTextColor(QColor(255, 165, 0))
                elif " - INFO - " in entry:
                    self.agent_log_text.setTextColor(QColor(0, 128, 0))
                else:
                    self.agent_log_text.setTextColor(QColor(0, 0, 0))
                    
                self.agent_log_text.append(entry)
                
            # Прокручиваем до конца
            cursor = self.agent_log_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.agent_log_text.setTextCursor(cursor)
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении журнала агента: {str(e)}")
    
    def _update_status(self):
        """Обновление статуса подключения"""
        # Проверяем статус подключения к RabbitMQ
        if self.rabbitmq_client.is_connected:
            host = self.rabbitmq_client.connection_params.get('host', '')
            port = self.rabbitmq_client.connection_params.get('port', '')
            self.rabbitmq_status_label.setText(f"RabbitMQ: Подключен ({host}:{port})")
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
        else:
            self.rabbitmq_status_label.setText("RabbitMQ: Не подключен")
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
            
        # Обновляем счетчик логов
        if self.collected_logs:
            self.status_label.setText(f"Статус: Собрано логов: {len(self.collected_logs)}")
        
    def closeEvent(self, event):
        """Обработка события закрытия окна"""
        # Останавливаем сбор логов если он запущен
        if self.collector_thread and self.collector_thread.isRunning():
            self.collector_thread.stop()
            
        # Отключаемся от RabbitMQ
        if self.rabbitmq_client.is_connected:
            self.rabbitmq_client.disconnect()
            
        # Сохраняем настройки
        try:
            self._save_settings()
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении настроек при закрытии: {str(e)}")
            
        self.logger.info("Приложение закрыто")
        event.accept()
