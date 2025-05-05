// Основные функции JavaScript для интерфейса агента сбора логов

// Обновление текущего времени
function updateTime() {
    const now = new Date();
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
    };
    document.getElementById('current-time').textContent = now.toLocaleDateString('ru-RU', options);
}

// Обновление статуса подключения к RabbitMQ
function updateRabbitMQStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            const statusIndicator = document.getElementById('rabbitmq-status-indicator');
            const statusText = document.getElementById('rabbitmq-status-text');
            
            if (data.rabbitmq_connected) {
                statusIndicator.className = 'status-indicator status-connected';
                statusText.textContent = 'RabbitMQ: Подключен';
            } else {
                statusIndicator.className = 'status-indicator status-disconnected';
                statusText.textContent = 'RabbitMQ: Не подключен';
            }
            
            // Обновление состояния кнопок, если они есть на странице
            const connectButton = document.getElementById('connect-rabbitmq');
            const disconnectButton = document.getElementById('disconnect-rabbitmq');
            
            if (connectButton && disconnectButton) {
                connectButton.disabled = data.rabbitmq_connected;
                disconnectButton.disabled = !data.rabbitmq_connected;
            }
        })
        .catch(error => {
            console.error('Ошибка при получении статуса:', error);
        });
}

// Показ уведомления
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Автоматическое скрытие уведомления через 5 секунд
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
    }, 5000);
}

// Подключение к RabbitMQ
function connectToRabbitMQ() {
    const button = document.getElementById('connect-rabbitmq');
    if (button) {
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Подключение...';
    }
    
    fetch('/api/connect-rabbitmq', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успешное подключение к RabbitMQ', 'success');
        } else {
            showAlert('Ошибка подключения: ' + data.message, 'danger');
        }
        
        updateRabbitMQStatus();
        
        if (button) {
            button.innerHTML = '<i class="bi bi-plug-fill me-1"></i> Подключиться к RabbitMQ';
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        showAlert('Ошибка при подключении к RabbitMQ', 'danger');
        
        if (button) {
            button.innerHTML = '<i class="bi bi-plug-fill me-1"></i> Подключиться к RabbitMQ';
            button.disabled = false;
        }
    });
}

// Отключение от RabbitMQ
function disconnectFromRabbitMQ() {
    const button = document.getElementById('disconnect-rabbitmq');
    if (button) {
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Отключение...';
    }
    
    fetch('/api/disconnect-rabbitmq', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Успешное отключение от RabbitMQ', 'info');
        } else {
            showAlert('Ошибка отключения: ' + data.message, 'danger');
        }
        
        updateRabbitMQStatus();
        
        if (button) {
            button.innerHTML = '<i class="bi bi-plug me-1"></i> Отключиться от RabbitMQ';
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        showAlert('Ошибка при отключении от RabbitMQ', 'danger');
        
        if (button) {
            button.innerHTML = '<i class="bi bi-plug me-1"></i> Отключиться от RabbitMQ';
            button.disabled = false;
        }
    });
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Запуск обновления времени
    updateTime();
    setInterval(updateTime, 1000);
    
    // Запуск обновления статуса RabbitMQ
    updateRabbitMQStatus();
    setInterval(updateRabbitMQStatus, 10000);
    
    // Добавление обработчиков событий к кнопкам
    const connectButton = document.getElementById('connect-rabbitmq');
    if (connectButton) {
        connectButton.addEventListener('click', connectToRabbitMQ);
    }
    
    const disconnectButton = document.getElementById('disconnect-rabbitmq');
    if (disconnectButton) {
        disconnectButton.addEventListener('click', disconnectFromRabbitMQ);
    }
});
