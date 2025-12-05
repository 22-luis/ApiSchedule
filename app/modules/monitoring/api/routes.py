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

@router.get("/debug-friday-tasks", include_in_schema=False)
async def debug_friday_tasks():
    """DEBUG: Muestra todas las tareas del viernes para debugging"""
    from app.shared.db.session import SessionLocal
    from app.modules.programming.models.programming import Programming, ProgrammingTask
    from app.modules.programming.models.task import Task
    from datetime import date
    
    db = SessionLocal()
    try:
        friday_date = date(2025, 12, 5)
        friday_id = '4a28a6c2-dcbe-48f5-bc51-2fea49878df4'
        
        # Get programming
        programming = db.query(Programming).filter(
            Programming.id == friday_id
        ).first()
        
        if not programming:
            return {"error": "Programming not found"}
        
        # Get all tasks
        programming_tasks = db.query(ProgrammingTask).filter(
            ProgrammingTask.programming_id == friday_id
        ).order_by(ProgrammingTask.start_time).all()
        
        tasks_data = []
        for pt in programming_tasks:
            task = db.query(Task).filter(Task.id == pt.task_id).first()
            if task:
                tasks_data.append({
                    "lote": task.lote,
                    "start_time": str(pt.start_time) if pt.start_time else None,
                    "end_time": str(pt.end_time) if pt.end_time else None,
                    "duration": task.minutes,
                    "order": pt.order
                })
        
        # Calculate current_end_minutes
        if programming_tasks:
            last_task = max(programming_tasks, key=lambda x: x.end_time if x.end_time else x.start_time)
            if last_task.end_time:
                end_minutes = last_task.end_time.hour * 60 + last_task.end_time.minute
            else:
                end_minutes = None
        else:
            end_minutes = 420
        
        return {
            "programming_id": friday_id,
            "date": str(programming.date),
            "status": programming.status,
            "total_tasks": len(programming_tasks),
            "current_end_minutes": end_minutes,
            "current_end_time": f"{end_minutes // 60}:{end_minutes % 60:02d}" if end_minutes else None,
            "tasks": tasks_data
        }
    finally:
        db.close()

@router.post("/cleanup-friday-tasks", include_in_schema=False)
async def cleanup_friday_tasks():
    """DEBUG: Elimina TODAS las tareas del viernes para limpiar datos corruptos"""
    from app.shared.db.session import SessionLocal
    from app.modules.programming.models.programming import Programming, ProgrammingTask
    from app.modules.programming.models.task import Task
    from datetime import date
    
    db = SessionLocal()
    try:
        friday_id = '4a28a6c2-dcbe-48f5-bc51-2fea49878df4'
        
        # Get all ProgrammingTasks for this Friday
        programming_tasks = db.query(ProgrammingTask).filter(
            ProgrammingTask.programming_id == friday_id
        ).all()
        
        task_ids = [pt.task_id for pt in programming_tasks]
        deleted_count = len(programming_tasks)
        
        # Delete ProgrammingTask relationships first
        for pt in programming_tasks:
            db.delete(pt)
        
        # Delete the Task objects
        for task_id in task_ids:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                db.delete(task)
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} tasks from Friday",
            "deleted_task_count": deleted_count,
            "friday_id": friday_id
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()
