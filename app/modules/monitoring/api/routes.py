from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from app.modules.monitoring.services.monitoring_service import monitoring_service
from app.shared.core.config import settings
from app.modules.monitoring.schemas.monitoring import (
    AppInfoOut,
    HealthStatusOut,
    DetailsHealthStatusOut,
    SystemStatusOut
)

router = APIRouter(tags=["monitoring"])

# Endpoint de health check
@router.get("/health", response_model=HealthStatusOut)
async def health_check():
    return await monitoring_service.get_health(detailed=False)


@router.get("/health/detailed", response_model=DetailsHealthStatusOut)
async def detailed_health_check():
    return await monitoring_service.get_health(detailed=True)

# Endpoint de información de la aplicación
@router.get("/info", response_model=AppInfoOut)
async def app_info():
    return await monitoring_service.get_app_info()

# Endpoint de estadísticas de rate limiting (solo en desarrollo)
@router.get("/rate-limit-stats", response_model=SystemStatusOut)
async def rate_limit_stats():
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Endpoint no disponible en producción")
    
    from app.shared.utils.performance.rate_limiting import get_rate_limit_stats
    return {"data": get_rate_limit_stats()}


# Endpoint de métricas de rendimiento (solo en desarrollo)
@router.get("/metrics", response_model=SystemStatusOut)
async def get_metrics():
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Endpoint no disponible en producción")
    
    from app.shared.utils.performance.metrics import metrics_collector
    return {"data": metrics_collector.get_all_metrics()}


# Endpoint de estado de circuit breakers (solo en desarrollo)
@router.get("/circuit-breakers", response_model=SystemStatusOut)
async def get_circuit_breakers():
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Endpoint no disponible en producción")
    
    from app.shared.utils.performance.circuit_breaker import circuit_breakers
    return {"data": circuit_breakers.get_status()}

@router.get("/cache-stats", include_in_schema=False)
async def get_cache_stats():
    """Obtiene estadísticas del sistema de caché"""
    try:
        from app.shared.utils.cache import cache_manager
        return cache_manager.get_stats()
    except ImportError:
        return {"error": "Sistema de caché no disponible"}

@router.get("/db-pool-info", include_in_schema=False)
async def get_database_pool_info():
    """Obtiene información del pool de conexiones de base de datos"""
    try:
        from app.shared.db.session import get_database_info
        return get_database_info()
    except ImportError:
        return {"error": "Información de base de datos no disponible"}
