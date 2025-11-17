"""
Sistema de logging centralizado para la aplicación.
Proporciona logging estructurado con diferentes niveles y formatos.
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Formateador JSON para logging estructurado"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro como JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Agregar campos adicionales si existen
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
        
        # Agregar excepción si existe
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class CustomFormatter(logging.Formatter):
    """Formateador personalizado para desarrollo"""
    
    # Colores para diferentes niveles
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro con colores en desarrollo"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Formato base
        formatted = super().format(record)
        
        # Agregar colores si no es producción
        if not settings.is_production:
            formatted = f"{color}{formatted}{reset}"
        
        return formatted


def setup_logging() -> None:
    """Configura el sistema de logging"""
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configurar nivel de logging
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # Configurar logging de SQLAlchemy
    sqlalchemy_log_level = getattr(logging, settings.SQLALCHEMY_LOG_LEVEL.upper(), logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(sqlalchemy_log_level)
    logging.getLogger('sqlalchemy.pool').setLevel(sqlalchemy_log_level)
    logging.getLogger('sqlalchemy.dialects').setLevel(sqlalchemy_log_level)
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Aplicar formateador según el entorno
    if settings.is_production:
        console_formatter = JSONFormatter()
    else:
        console_formatter = CustomFormatter(settings.LOG_FORMAT)
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Handler para archivo (solo en producción)
    if settings.is_production:
        file_handler = logging.FileHandler(
            log_dir / f"{settings.APP_NAME.lower()}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    # Configurar loggers específicos
    setup_specific_loggers()


def setup_specific_loggers() -> None:
    """Configura loggers específicos para diferentes módulos"""
    # Logger para base de datos
    db_logger = logging.getLogger("sqlalchemy.engine")
    db_logger.setLevel(logging.WARNING if settings.is_production else logging.INFO)
    
    # Logger para FastAPI
    fastapi_logger = logging.getLogger("uvicorn")
    fastapi_logger.setLevel(logging.INFO)
    
    # Logger para la aplicación
    app_logger = logging.getLogger("app")
    app_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger configurado"""
    return logging.getLogger(f"app.{name}")


class RequestLogger:
    """Logger especializado para requests HTTP"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_request(self, method: str, url: str, user_id: Optional[str] = None, 
                   request_id: Optional[str] = None) -> None:
        """Registra el inicio de una request"""
        extra = {
            'method': method,
            'endpoint': url,
            'user_id': user_id,
            'request_id': request_id
        }
        self.logger.info(f"Request iniciada: {method} {url}", extra=extra)
    
    def log_response(self, method: str, url: str, status_code: int, 
                    duration: float, user_id: Optional[str] = None,
                    request_id: Optional[str] = None) -> None:
        """Registra la respuesta de una request"""
        level = logging.ERROR if status_code >= 400 else logging.INFO
        extra = {
            'method': method,
            'endpoint': url,
            'status_code': status_code,
            'duration': duration,
            'user_id': user_id,
            'request_id': request_id
        }
        self.logger.log(level, f"Request completada: {method} {url} - {status_code} ({duration:.3f}s)", extra=extra)
    
    def log_error(self, method: str, url: str, error: Exception, 
                 user_id: Optional[str] = None, request_id: Optional[str] = None) -> None:
        """Registra un error en una request"""
        extra = {
            'method': method,
            'endpoint': url,
            'user_id': user_id,
            'request_id': request_id
        }
        self.logger.error(f"Error en request: {method} {url} - {str(error)}", extra=extra, exc_info=True)


def log_function_call(func_name: str, **kwargs) -> None:
    """Decorador para logging de llamadas a funciones"""
    logger = get_logger("function_calls")
    logger.debug(f"Llamada a función: {func_name}", extra={'function': func_name, 'params': kwargs})


def log_database_operation(operation: str, table: str, record_id: Optional[str] = None, 
                          user_id: Optional[str] = None) -> None:
    """Registra operaciones de base de datos"""
    logger = get_logger("database")
    extra = {
        'operation': operation,
        'table': table,
        'record_id': record_id,
        'user_id': user_id
    }
    logger.info(f"Operación DB: {operation} en {table}", extra=extra)


def log_security_event(event_type: str, user_id: Optional[str] = None, 
                      details: Optional[Dict[str, Any]] = None) -> None:
    """Registra eventos de seguridad"""
    logger = get_logger("security")
    extra = {
        'event_type': event_type,
        'user_id': user_id,
        'details': details or {}
    }
    logger.warning(f"Evento de seguridad: {event_type}", extra=extra)


def log_business_logic(operation: str, entity: str, entity_id: Optional[str] = None,
                      user_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
    """Registra operaciones de lógica de negocio"""
    logger = get_logger("business")
    extra = {
        'operation': operation,
        'entity': entity,
        'entity_id': entity_id,
        'user_id': user_id,
        'details': details or {}
    }
    logger.info(f"Lógica de negocio: {operation} en {entity}", extra=extra)
