# Architecture Overview

## Overview

This application is a Windows Log Collection Agent designed to gather system logs from Windows systems and optionally forward them to a RabbitMQ message broker. The system provides two interfaces:

1. A web interface built with Flask
2. A desktop GUI application built with PyQt5

The agent can collect various Windows log types (System, Application, Security, etc.), filter them based on criteria, and either display them through the interfaces or send them to a configured RabbitMQ server for further processing.

## System Architecture

The application follows a modular architecture with clear separation of concerns:

```
                  ┌─────────────────┐
                  │     Web UI      │
                  │    (Flask)      │
                  └────────┬────────┘
                           │
┌─────────────────┐  ┌─────┴──────┐  ┌─────────────────┐
│    Desktop UI   │  │    Core    │  │    RabbitMQ     │
│     (PyQt5)     ├──┤   Logic    ├──┤     Client      │
└─────────────────┘  └─────┬──────┘  └─────────────────┘
                           │
                  ┌────────┴────────┐
                  │  Log Collector  │
                  │    (Windows)    │
                  └─────────────────┘
```

### Design Patterns

1. **Singleton Pattern**: Used for the `AgentLogger` to ensure a single logging instance throughout the application.
2. **Publisher/Subscriber Pattern**: Implemented through RabbitMQ integration for log message distribution.
3. **Thread-based Processing**: Log collection and RabbitMQ operations run in separate threads to prevent UI blocking.

## Key Components

### 1. Log Collector (`log_collector.py`)

Responsible for interfacing with Windows Event Log API to collect system logs.

- Supports multiple log types (System, Application, Security, etc.)
- Maintains offsets to avoid duplicate log collection
- Implements filtering by log level and time range

### 2. RabbitMQ Client (`rabbitmq_client.py`)

Handles communication with RabbitMQ message broker:

- Connection management
- Message queuing and publishing
- Reconnection handling
- SSL/TLS support

### 3. Agent Logger (`agent_logger.py`)

Provides centralized logging capabilities:

- Implements Singleton pattern
- Supports log rotation
- Configurable log levels

### 4. Web Interface (`main.py` and templates)

Flask-based web application that provides:

- Dashboard overview of system status
- Log viewing and filtering
- RabbitMQ connection configuration
- Agent settings management

### 5. Desktop GUI (`gui.py`)

PyQt5-based desktop application that offers:

- Alternative interface for the agent
- Real-time log collection visualization 
- Configuration management

### 6. Configuration Management

Supports multiple configuration formats:

- INI format (`config.ini`)
- YAML format (`config.yml`)
- Command-line parameters

## Data Flow

1. **Log Collection**:
   - The Log Collector periodically queries Windows Event Logs
   - New log entries are processed, filtered based on configuration
   - Collected logs are stored in memory and optionally sent to RabbitMQ

2. **RabbitMQ Integration**:
   - Logs are serialized to JSON format
   - Messages are published to configured exchange with routing keys
   - Failed message delivery is handled through a queue system

3. **User Interfaces**:
   - Both web and desktop interfaces display collected logs
   - Users can trigger manual log collection
   - Configuration changes are persisted and applied at runtime

## External Dependencies

### Core Dependencies

- **Flask**: Web framework for the HTTP interface
- **PyQt5**: GUI toolkit for the desktop application
- **pika**: RabbitMQ client library
- **YAML**: Configuration file parsing
- **gunicorn**: WSGI HTTP server for production deployment

### External Services

- **RabbitMQ**: Message broker for log distribution
  - Configured via host, port, virtual host, credentials
  - Optional SSL/TLS support
  - Exchange and routing key configuration

## Deployment Strategy

The application is designed for flexible deployment:

### Development Environment

- Flask development server with debug mode
- Direct execution through Python interpreter

### Production Deployment

- Gunicorn WSGI server for the web interface
- Auto-scaling configuration through Replit
- Environment-specific configuration through config files

The deployment configuration in `.replit` indicates the application is designed to be deployed in a cloud environment with:

```
[deployment]
deploymentTarget = "autoscale"
run = ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
```

### Configuration Management

The application uses a hierarchical configuration approach:

1. Default configurations built into the code
2. Configuration files (`config.ini`, `config.yml`)
3. Environment variables for sensitive information
4. Runtime configuration through the UI

## Security Considerations

- Support for SSL/TLS when connecting to RabbitMQ
- Password storage in configuration files (should be improved with environment variables)
- No explicit authentication for the web interface (should be added for production use)

## Future Enhancements

Potential areas for architectural improvement:

1. Add user authentication for the web interface
2. Implement a more secure credential management system
3. Add database integration for persistent log storage
4. Expand monitoring capabilities with metrics collection
5. Implement a more robust message delivery guarantee system

## Limitations

- The current architecture is primarily designed for Windows systems
- No built-in clustering or high-availability features
- Limited persistent storage capabilities for collected logs