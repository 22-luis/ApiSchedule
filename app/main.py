"""
Aplicación principal de FastAPI para ApiSchedule.
Configuración centralizada con logging, rate limiting y manejo de errores.
"""
import time
import uuid
from fastapi import APIRouter, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Usar configuración simple temporalmente
try:
    from app.shared.core.config import settings, validate_critical_settings
    if settings.is_development:
        print("✅ Usando configuración completa con pydantic-settings")
except ImportError as e:
    if settings.is_development:
        print(f"⚠️  Error importando configuración completa: {e}")
    from app.shared.core.config_simple import settings, validate_critical_settings
    if settings.is_development:
        print("✅ Usando configuración simple")

from app.shared.db.session import engine
from app.shared.db.database import Base
from app.shared.utils.core.exception_handlers import (
    http_exception_handler, 
    validation_exception_handler, 
    database_exception_handler,
    circuit_breaker_exception_handler,
    generic_exception_handler
)
from sqlalchemy.exc import SQLAlchemyError
from app.shared.utils.performance.circuit_breaker import CircuitBreakerOpenError

# Importar logging y rate limiting solo si están disponibles
try:
    from app.shared.utils.core.logging import setup_logging, get_logger, RequestLogger
    from app.shared.utils.performance.rate_limiting import rate_limit_middleware, get_rate_limit_stats
    LOGGING_AVAILABLE = True
    if settings.is_development:
        print("✅ Sistema de logging y rate limiting disponible")
except ImportError as e:
    LOGGING_AVAILABLE = False
    if settings.is_development:
        print(f"⚠️  Sistema de logging no disponible: {e}")
        print("   Usando logging básico")
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_logger(name): return logging.getLogger(name)
    def setup_logging(): pass
    def rate_limit_middleware(request, call_next): return call_next(request)
    def get_rate_limit_stats(): return {"error": "Rate limiting no disponible"}

from app.modules.core.api.routes_auth import router as auth_router
from app.modules.core.api.routes_user import router as user_router
from app.modules.core.api.routes_team import router as team_router
from app.modules.programming.api.routes_order import router as order_router
from app.modules.programming.api.routes_task import router as task_router
from app.modules.programming.api.routes_task_status_log import router as task_status_log_router
from app.modules.programming.api.routes_preparation import router as preparation_router
from app.modules.programming.api.routes_code import router as code_router
from app.modules.programming.api.routes_programming import router as programming_router
from app.modules.programming.api.routes_calculations import router as calculations_router
from app.modules.timer.api.routes_timer import router as timer_router
from app.modules.timer.api.routes_record_stopwatch import router as record_stopwatch_router

from app.modules.reports.api.routes_report import router as report_router

# Import models to ensure they are registered with Base
from app.modules.core.models import user, team
from app.modules.programming.models import task, order, preparation, programming

# Configurar logging si está disponible
if LOGGING_AVAILABLE:
    setup_logging()
logger = get_logger("main")

# Validar configuración crítica
try:
    validate_critical_settings()
    logger.info("Configuración crítica validada correctamente")
except Exception as e:
    logger.error(f"Error en configuración crítica: {e}")
    print(f"⚠️  Error en configuración: {e}")

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    # ApiSchedule - API de Gestión de Programaciones, cronometro y reportes

  ## Endpoints de Monitoreo

    * `GET /health` - Estado de salud de la aplicación
    * `GET /health/detailed` - Información detallada de salud
    * `GET /info` - Información de la aplicación
    * `GET /metrics` - Métricas de rendimiento (solo desarrollo)
    * `GET /circuit-breakers` - Estado de circuit breakers (solo desarrollo)
    """,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    debug=settings.DEBUG,
    openapi_tags=[
        {
            "name": "auth",
            "description": "Operaciones de autenticación y autorización"
        },
        {
            "name": "users",
            "description": "Gestión de usuarios del sistema"
        },
        {
            "name": "teams",
            "description": "Gestión de equipos de trabajo"
        },
        {
            "name": "tasks",
            "description": "Gestión de tareas y programaciones"
        },
        {
            "name": "orders",
            "description": "Gestión de órdenes de producción"
        },
        {
            "name": "codes",
            "description": "Gestión de códigos predefinidos"
        },
        {
            "name": "preparations",
            "description": "Gestión de preparaciones"
        },
        {
            "name": "calculations",
            "description": "Cálculos de negocio y utilidades"
        },
        {
            "name": "reports",
            "description": "Reportes de productividad y rendimiento"
        }
    ],
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Servidor de desarrollo"
        }
    ]
)

# Middleware para logging de requests
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging de requests HTTP"""
    
    async def dispatch(self, request: Request, call_next):
        # Generar ID único para la request
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Obtener información del usuario si está autenticado
        user_id = None
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # Aquí podrías decodificar el token para obtener el user_id
                # Por ahora usamos un hash del token
                import hashlib
                token = auth_header.split(" ")[1]
                user_id = hashlib.md5(token.encode()).hexdigest()[:8]
        except Exception:
            pass
        
        # Log del inicio de la request
        start_time = time.time()
        logger.info(
            f"Request iniciada: {request.method} {request.url}",
            extra={
                'request_id': request_id,
                'method': request.method,
                'endpoint': str(request.url),
                'user_id': user_id,
                'client_ip': request.client.host if request.client else "unknown"
            }
        )
        
        try:
            # Procesar la request
            response = await call_next(request)
            
            # Calcular duración
            duration = time.time() - start_time
            
            # Log de la respuesta
            logger.info(
                f"Request completada: {request.method} {request.url} - {response.status_code} ({duration:.3f}s)",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'endpoint': str(request.url),
                    'status_code': response.status_code,
                    'duration': duration,
                    'user_id': user_id
                }
            )
            
            # Agregar headers de request ID
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log de errores
            duration = time.time() - start_time
            logger.error(
                f"Error en request: {request.method} {request.url} - {str(e)}",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'endpoint': str(request.url),
                    'duration': duration,
                    'user_id': user_id
                },
                exc_info=True
            )
            raise

# Configuración de CORS mejorada
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Middleware de hosts confiables (solo en producción)
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configurar hosts específicos en producción
    )

# Middleware de logging de requests
app.add_middleware(RequestLoggingMiddleware)

# Middleware de rate limiting
if settings.RATE_LIMIT_ENABLED and LOGGING_AVAILABLE:
    app.middleware("http")(rate_limit_middleware)

# Registro de exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(CircuitBreakerOpenError, circuit_breaker_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Registro de routers
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(user_router, tags=["users"])
api_router.include_router(team_router, tags=["teams"])
api_router.include_router(order_router, tags=["orders"])
api_router.include_router(task_router, tags=["tasks"])
api_router.include_router(task_status_log_router, tags=["tasks"])
api_router.include_router(preparation_router, tags=["preparations"])
api_router.include_router(code_router, tags=["codes"])
api_router.include_router(programming_router, tags=["programmings"])
api_router.include_router(calculations_router, tags=["calculations"])
api_router.include_router(timer_router, tags=["Timer"])
api_router.include_router(record_stopwatch_router, tags=["Record Stopwatch"])
api_router.include_router(report_router, tags=["reports"])

# Incluir el router principal en la app
app.include_router(api_router)

# Endpoint de health check
@app.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud de la aplicación.
    
    Returns:
        Dict con el estado de salud básico del sistema
    """
    from app.shared.utils.core.health_checks import get_quick_health_status
    return await get_quick_health_status()


@app.get("/health/detailed")
async def detailed_health_check():
    """
    Endpoint de verificación de salud detallada de la aplicación.
    
    Realiza verificaciones completas de:
    - Conexión a base de datos
    - Uso de memoria y disco
    - Estado del rate limiting
    - Configuración crítica
    
    Returns:
        Dict con el estado de salud completo del sistema
    """
    from app.shared.utils.core.health_checks import get_health_status
    return await get_health_status()

# Endpoint de información de la aplicación
@app.get("/info")
async def app_info():
    """Endpoint de información de la aplicación"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "database_configured": bool(settings.SQLALCHEMY_DATABASE_URI),
        "rate_limiting_enabled": settings.RATE_LIMIT_ENABLED,
        "cors_origins": settings.CORS_ORIGINS,
        "working_hours": {
            "monday_friday": settings.WORKING_HOURS_MONDAY_FRIDAY,
            "saturday": settings.WORKING_HOURS_SATURDAY,
            "sunday": settings.WORKING_HOURS_SUNDAY
        }
    }

# Endpoint de estadísticas de rate limiting (solo en desarrollo)
@app.get("/rate-limit-stats")
async def rate_limit_stats():
    """Endpoint para ver estadísticas de rate limiting"""
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Endpoint no disponible en producción")
    
    return get_rate_limit_stats()


# Endpoint de métricas de performance (solo en desarrollo)
@app.get("/metrics")
async def get_metrics():
    """
    Endpoint para obtener métricas de performance de la aplicación.
    
    Returns:
        Dict con métricas del sistema, requests, latencia y métricas personalizadas
    """
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Endpoint no disponible en producción")
    
    from app.shared.utils.performance.metrics import metrics_collector
    return metrics_collector.get_all_metrics()


# Endpoint de estado de circuit breakers (solo en desarrollo)
@app.get("/circuit-breakers")
async def get_circuit_breakers():
    """
    Endpoint para obtener el estado de los circuit breakers.
    
    Returns:
        Dict con el estado de todos los circuit breakers
    """
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Endpoint no disponible en producción")
    
    from app.shared.utils.performance.circuit_breaker import circuit_breakers
    return circuit_breakers.get_status()

@app.get("/cache-stats", include_in_schema=False)
async def get_cache_stats():
    """Obtiene estadísticas del sistema de caché"""
    try:
        from app.shared.utils.cache import cache_manager
        return cache_manager.get_stats()
    except ImportError:
        return {"error": "Sistema de caché no disponible"}

@app.get("/db-pool-info", include_in_schema=False)
async def get_database_pool_info():
    """Obtiene información del pool de conexiones de base de datos"""
    try:
        from app.shared.db.session import get_database_info
        return get_database_info()
    except ImportError:
        return {"error": "Información de base de datos no disponible"}

# Eventos de la aplicación
@app.on_event("startup")
async def startup_event():
    """Evento ejecutado al iniciar la aplicación"""
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Entorno: {settings.ENVIRONMENT}")
    
    # Logs adicionales solo en desarrollo
    if settings.is_development:
        logger.info(f"Debug: {settings.DEBUG}")
        logger.info(f"Rate limiting: {'Habilitado' if settings.RATE_LIMIT_ENABLED else 'Deshabilitado'}")
    
    # Crear tablas de base de datos
    try:
        # Base.metadata.create_all(bind=engine) # Deshabilitado para usar Alembic
        logger.info("La inicialización de la base de datos ahora se maneja con Alembic.")
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")
        if settings.is_development:
            print(f"⚠️  Error inicializando base de datos: {e}")
            print("   Asegúrate de que PostgreSQL esté ejecutándose y configurado correctamente")
    
    # Inicializar sistema de métricas
    try:
        from app.shared.utils.performance.metrics import start_system_metrics_collector
        start_system_metrics_collector()
        logger.info("Sistema de métricas inicializado correctamente")
    except Exception as e:
        logger.error(f"Error inicializando sistema de métricas: {e}")
        if settings.is_development:
            print(f"⚠️  Error inicializando métricas: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Evento ejecutado al cerrar la aplicación"""
    logger.info(f"Cerrando {settings.APP_NAME}")

# Log de inicio
logger.info("Aplicación configurada correctamente")
if settings.is_development:
    print("🚀 ApiSchedule iniciado correctamente!")
    print(f"📊 Health check: http://localhost:8000/health")
    print(f"📚 Documentación: http://localhost:8000/docs")