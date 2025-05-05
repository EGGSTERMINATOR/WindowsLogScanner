# -*- coding: utf-8 -*-
"""
Модуль с иконками для интерфейса
"""

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice
import base64

# Словарь иконок в формате SVG, закодированных в base64
ICONS = {
    "play": """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <path d="M8 5v14l11-7z" fill="#4CAF50"/>
        </svg>
    """,
    
    "stop": """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <path d="M6 6h12v12H6z" fill="#F44336"/>
        </svg>
    """,
    
    "connect": """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <path d="M16 6h3c1.1 0 2 .9 2 2v8c0 1.1-.9 2-2 2h-3v-2h3V8h-3V6zm-5 12v-2h2v2h-2zm0-4h2v-2h-2v2zm0-4V8h2v2h-2zm-8 8c0 1.1.9 2 2 2h3v-2H5V8h3V6H5c-1.1 0-2 .9-2 2v8z" fill="#2196F3"/>
        </svg>
    """,
    
    "disconnect": """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <path d="M14.39 11L16 12.61V6h-3v2h-2V6H6v8h3v-2h2v2h.61L10 12.39 11.61 11 8 7.39 9.39 6l5 5-5 5L8 14.61 11.61 11 13 12.39zM17 4h3c1.1 0 2 .9 2 2v8c0 1.1-.9 2-2 2h-3v-2h3V8h-3V6zM3 16c0 1.1.9 2 2 2h3v-2H5V8h3V6H5c-1.1 0-2 .9-2 2v8z" fill="#F44336"/>
        </svg>
    """,
    
    "clear": """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <path d="M5 13h14v-2H5v2zm-2 4h14v-2H3v2zM7 7v2h14V7H7z" fill="#607D8B"/>
        </svg>
    """,
    
    "save": """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <path d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z" fill="#FFC107"/>
        </svg>
    """,
    
    "exit": """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <path d="M10.09 15.59L11.5 17l5-5-5-5-1.41 1.41L12.67 11H3v2h9.67l-2.58 2.59zM19 3H5c-1.11 0-2 .9-2 2v4h2V5h14v14H5v-4H3v4c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z" fill="#9E9E9E"/>
        </svg>
    """,
    
    "refresh": """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" fill="#03A9F4"/>
        </svg>
    """,
    
    "settings": """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22l-1.92 3.32c-.12.21-.07.47.12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" fill="#FF9800"/>
        </svg>
    """
}

def get_icon(name):
    """
    Получение иконки по имени
    
    Args:
        name (str): Имя иконки
        
    Returns:
        QIcon: Объект иконки
    """
    if name not in ICONS:
        # Возвращаем пустую иконку, если имя не найдено
        return QIcon()
        
    # Получаем SVG-данные
    svg_data = ICONS[name].strip()
    
    # Создаем иконку из SVG
    icon = QIcon()
    
    # Создаем QByteArray из SVG-данных
    byte_array = QByteArray(svg_data.encode('utf-8'))
    
    # Создаем из массива байтов QIcon
    icon.addData(byte_array)
    
    return icon
