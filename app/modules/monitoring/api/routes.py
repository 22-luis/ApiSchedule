from fastapi import APIRouter, HTTPException
from app.shared.core.config import settings

router = APIRouter(tags=["monitoring"])

# Endpoint de health check
@router.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud de la aplicación.
    
    Returns:
        Dict con el estado de salud básico del sistema
    """
    from app.shared.utils.core.health_checks import get_quick_health_status
    return await get_quick_health_status()


@router.get("/health/detailed")
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
@router.get("/info")
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
@router.get("/rate-limit-stats")
async def rate_limit_stats():
    """Endpoint para ver estadísticas de rate limiting"""
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Endpoint no disponible en producción")
    
    from app.shared.utils.performance.rate_limiting import get_rate_limit_stats
    return get_rate_limit_stats()


# Endpoint de métricas de performance (solo en desarrollo)
@router.get("/metrics")
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
@router.get("/circuit-breakers")
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
