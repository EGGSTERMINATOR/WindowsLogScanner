# -*- coding: utf-8 -*-
"""
Главный модуль приложения для сбора системных логов Windows 10
с возможностью подключения к RabbitMQ
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication
from gui import MainWindow

if __name__ == "__main__":
    # Настройка базового логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Запуск приложения
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Используем Fusion стиль для лучшего внешнего вида
    
    # Создание и показ главного окна
    main_window = MainWindow()
    main_window.show()
    
    # Запуск основного цикла приложения
    sys.exit(app.exec_())
