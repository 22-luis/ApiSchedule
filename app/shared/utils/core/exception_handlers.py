import traceback
import uuid
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from app.shared.utils.core.logging import get_logger
from app.shared.utils.performance.circuit_breaker import CircuitBreakerOpenError

logger = get_logger("exception_handlers")

# Manejo centralizado de HTTPException
def http_exception_handler(request: Request, exc: HTTPException):
    """
    Maneja excepciones HTTP específicas con logging detallado.
    
    Args:
        request: Request de FastAPI
        exc: Excepción HTTP
        
    Returns:
        JSONResponse con información del error
    """
    error_id = str(uuid.uuid4())
    
    # Log del error
    logger.warning(
        f"HTTP Exception {exc.status_code}: {exc.detail}",
        extra={
            'error_id': error_id,
            'status_code': exc.status_code,
            'endpoint': str(request.url),
            'method': request.method,
            'client_ip': request.client.host if request.client else "unknown"
        }
    )
    
    # Determinar tipo de error para mensaje más específico
    error_type = "client_error" if 400 <= exc.status_code < 500 else "server_error"
    
    response_content = {
        "error": {
            "type": error_type,
            "code": exc.status_code,
            "message": exc.detail,
            "error_id": error_id,
            "timestamp": str(uuid.uuid1().time)
        }
    }
    
    # Agregar información adicional según el tipo de error
    if exc.status_code == 404:
        response_content["error"]["suggestion"] = "Verifica que la URL sea correcta"
    elif exc.status_code == 401:
        response_content["error"]["suggestion"] = "Verifica tus credenciales de autenticación"
    elif exc.status_code == 403:
        response_content["error"]["suggestion"] = "No tienes permisos para acceder a este recurso"
    elif exc.status_code == 429:
        response_content["error"]["suggestion"] = "Demasiadas requests. Intenta más tarde"
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_content
    )

# Manejo centralizado de errores de validación
def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Maneja errores de validación de Pydantic con información detallada.
    
    Args:
        request: Request de FastAPI
        exc: Excepción de validación
        
    Returns:
        JSONResponse con detalles de validación
    """
    error_id = str(uuid.uuid4())
    
    # Log del error de validación
    logger.warning(
        f"Validation Error: {len(exc.errors())} validation errors",
        extra={
            'error_id': error_id,
            'endpoint': str(request.url),
            'method': request.method,
            'validation_errors': exc.errors()
        }
    )
    
    # Procesar errores de validación para mensajes más claros
    processed_errors = []
    has_password_error = False
    
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        
        # Mejorar mensajes específicos para errores de contraseña
        if "password" in field_path.lower():
            has_password_error = True
            if error["type"] == "string_too_short":
                error_message = "La contraseña debe tener al menos 6 caracteres"
            elif error["type"] == "missing":
                error_message = "La contraseña es requerida para crear un nuevo usuario"
            else:
                error_message = error["msg"]
        else:
            error_message = error["msg"]
        
        processed_errors.append({
            "field": field_path,
            "message": error_message,
            "type": error["type"],
            "value": error.get("input")
        })
    
    # Determinar mensaje principal y sugerencia basado en los errores
    if has_password_error:
        main_message = "Error de validación en los datos"
        suggestion = "Para actualizar un usuario sin cambiar la contraseña, deja el campo de contraseña vacío"
    else:
        main_message = "Error de validación en los datos de entrada"
        suggestion = "Verifica que todos los campos requeridos estén presentes y tengan el formato correcto"
    
    response_content = {
        "error": {
            "type": "validation_error",
            "code": 422,
            "message": main_message,
            "error_id": error_id,
            "timestamp": str(uuid.uuid1().time),
            "validation_errors": processed_errors,
            "suggestion": suggestion
        }
    }
    
    return JSONResponse(
        status_code=422,
        content=response_content
    )

# Manejo específico para errores de base de datos
def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Maneja errores específicos de base de datos.
    
    Args:
        request: Request de FastAPI
        exc: Excepción de SQLAlchemy
        
    Returns:
        JSONResponse con información del error de base de datos
    """
    error_id = str(uuid.uuid4())
    
    # Determinar tipo específico de error de base de datos
    if isinstance(exc, IntegrityError):
        error_type = "database_integrity_error"
        message = "Error de integridad en la base de datos"
        suggestion = "Verifica que los datos no violen las restricciones de la base de datos"
    elif isinstance(exc, OperationalError):
        error_type = "database_operational_error"
        message = "Error operacional en la base de datos"
        suggestion = "El servicio de base de datos puede estar temporalmente no disponible"
    else:
        error_type = "database_error"
        message = "Error en la base de datos"
        suggestion = "Contacta al administrador del sistema"
    
    # Log del error
    print("\n" + "="*50)
    print(f"DATABASE ERROR DEBUG: {error_type}")
    import traceback
    print("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    print("="*50 + "\n")
    
    logger.error(
        f"Database Error: {message}",
        extra={
            'error_id': error_id,
            'error_type': error_type,
            'endpoint': str(request.url),
            'method': request.method,
            'exception': str(exc)
        },
        exc_info=True
    )
    
    response_content = {
        "error": {
            "type": error_type,
            "code": 503,
            "message": message,
            "error_id": error_id,
            "timestamp": str(uuid.uuid1().time),
            "suggestion": suggestion
        }
    }
    
    return JSONResponse(
        status_code=503,
        content=response_content
    )


# Manejo específico para circuit breaker
def circuit_breaker_exception_handler(request: Request, exc: CircuitBreakerOpenError):
    """
    Maneja errores de circuit breaker.
    
    Args:
        request: Request de FastAPI
        exc: Excepción de circuit breaker
        
    Returns:
        JSONResponse con información del error
    """
    error_id = str(uuid.uuid4())
    
    logger.warning(
        f"Circuit Breaker Error: {str(exc)}",
        extra={
            'error_id': error_id,
            'endpoint': str(request.url),
            'method': request.method
        }
    )
    
    response_content = {
        "error": {
            "type": "service_unavailable",
            "code": 503,
            "message": "Servicio temporalmente no disponible",
            "error_id": error_id,
            "timestamp": str(uuid.uuid1().time),
            "suggestion": "El servicio está temporalmente sobrecargado. Intenta más tarde."
        }
    }
    
    return JSONResponse(
        status_code=503,
        content=response_content
    )


# Manejo genérico para cualquier otra excepción
def generic_exception_handler(request: Request, exc: Exception):
    """
    Maneja excepciones genéricas no capturadas.
    
    Args:
        request: Request de FastAPI
        exc: Excepción genérica
        
    Returns:
        JSONResponse con información del error
    """
    error_id = str(uuid.uuid4())
    
    # Log del error con stack trace
    logger.error(
        f"Unhandled Exception: {type(exc).__name__}: {str(exc)}",
        extra={
            'error_id': error_id,
            'endpoint': str(request.url),
            'method': request.method,
            'exception_type': type(exc).__name__,
            'stack_trace': traceback.format_exc()
        },
        exc_info=True
    )
    
    response_content = {
        "error": {
            "type": "internal_server_error",
            "code": 500,
            "message": "Error interno del servidor",
            "error_id": error_id,
            "timestamp": str(uuid.uuid1().time),
            "suggestion": "Contacta al administrador del sistema si el problema persiste"
        }
    }
    
    return JSONResponse(
        status_code=500,
        content=response_content
    )