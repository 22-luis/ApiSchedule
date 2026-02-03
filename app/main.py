import hashlib
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.modules.available.api.routes_available import router as available_router
from app.modules.codes.api.routes_code import router as code_router
from app.modules.quality.api.routes_code_test import router as code_test_router
from app.modules.codes.api.routes_preparation import router as preparation_router
# Import Routers
from app.modules.core.api.routes_auth import router as auth_router
from app.modules.core.api.routes_team import router as team_router
from app.modules.core.api.routes_user import router as user_router
from app.modules.monitoring.api.routes import router as monitoring_router
from app.modules.programming.api.routes_calculations import router as calculations_router
from app.modules.programming.api.routes_notification import router as notification_router
from app.modules.programming.api.routes_order import router as order_router
from app.modules.programming.api.routes_programming import router as programming_router
from app.modules.programming.api.routes_task import router as task_router
from app.modules.programming.api.routes_task_status_log import router as task_status_log_router
from app.modules.programming.api.routes_surplus import router as surplus_router
from app.modules.quality.api.routes_manual import router as manual_router
from app.modules.quality.api.routes_qctest import router as qc_router
from app.modules.quality.api.routes_test_question import router as test_question_router
from app.modules.quality.api.routes_test_record import router as test_record_router
from app.modules.quality.api.routes_catalog_test import router as catalog_test_router
from app.modules.reports.api.routes_report import router as report_router
from app.modules.timer.api.routes_record_stopwatch import router as record_stopwatch_router
from app.modules.timer.api.routes_timer import router as timer_router
from app.modules.warehouse.api.routes_history import router as warehouse_history_router
from app.shared.core.config import settings, validate_critical_settings
from app.shared.utils.core.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    circuit_breaker_exception_handler,
    generic_exception_handler
)
from app.shared.utils.core.logging import setup_logging, get_logger
from app.shared.utils.performance.circuit_breaker import CircuitBreakerOpenError
from app.shared.utils.performance.metrics import start_system_metrics_collector
from app.shared.utils.performance.rate_limiting import rate_limit_middleware

# Import models to ensure they are registered with Base

# Initialize logging
setup_logging()
logger = get_logger("main")

# --- Events ---

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION} en {settings.ENVIRONMENT}")
    validate_critical_settings()

    try:
        start_system_metrics_collector()
        logger.info("Sistema de métricas inicializado")
    except Exception as e:
        logger.error(f"Error inicializando métricas: {e}")

    yield  #funcion que maneja el ciclo de vida del servidor

    # Shutdown
    logger.info(f"Finalizando {settings.APP_NAME}")

if settings.is_development:
    print(f"🚀 ApiSchedule iniciado correctamente! Health: http://localhost:8000/api/v1/health")

# Start Application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ApiSchedule - API de Gestión de Programaciones, cronometro y reportes",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# --- Middlewares ---

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        user_id = None
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                user_id = hashlib.md5(token.encode()).hexdigest()[:8]
        except (IndexError, AttributeError, ValueError):
            pass
        
        start_time = time.time()
        logger.info(
            f"Request iniciada: {request.method} {request.url}",
            extra={'request_id': request_id, 'method': request.method, 'endpoint': str(request.url), 'user_id': user_id}
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(
                f"Request completada: {request.method} {request.url} - {response.status_code} ({duration:.3f}s)",
                extra={'request_id': request_id, 'status_code': response.status_code, 'duration': duration}
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            logger.error(f"Error en request: {str(e)}", exc_info=True)
            raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

if settings.is_production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

app.add_middleware(RequestLoggingMiddleware)

if settings.RATE_LIMIT_ENABLED:
    app.middleware("http")(rate_limit_middleware)

# --- Exception Handlers ---

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(CircuitBreakerOpenError, circuit_breaker_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# --- Routes ---

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(user_router, tags=["users"])
api_router.include_router(team_router, tags=["teams"])
api_router.include_router(order_router, tags=["orders"])
api_router.include_router(task_router, tags=["tasks"])
api_router.include_router(task_status_log_router, tags=["tasks"])
api_router.include_router(preparation_router, tags=["preparations"])
api_router.include_router(code_router, tags=["codes"])
api_router.include_router(catalog_test_router, tags=["catalog-tests"])
api_router.include_router(code_test_router, tags=["codes"])
api_router.include_router(programming_router, tags=["programmings"])
api_router.include_router(calculations_router, tags=["calculations"])
api_router.include_router(timer_router, tags=["Timer"])
api_router.include_router(record_stopwatch_router, tags=["Record Stopwatch"])
api_router.include_router(report_router, tags=["reports"])
api_router.include_router(available_router, tags=["available"])
api_router.include_router(monitoring_router)
api_router.include_router(notification_router, tags=["notifications"])
api_router.include_router(manual_router, tags=["manual"])
api_router.include_router(qc_router, tags=["qctest"])
api_router.include_router(test_question_router, tags=["test-questions"])
api_router.include_router(test_record_router, tags=["test-record"])
api_router.include_router(warehouse_history_router, tags=["warehouse"])
api_router.include_router(surplus_router, tags=["surplus"])

app.include_router(api_router)
