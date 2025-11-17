"""
Sistema de caché para la aplicación usando Redis con fallback a memoria.
Proporciona funciones para cachear respuestas de API y datos frecuentemente accedidos.
"""
import json
import hashlib
import time
from typing import Any, Optional, Dict, List
from functools import wraps
import logging

# Importar configuración
try:
    from app.core.config import settings
    REDIS_AVAILABLE = settings.RATE_LIMIT_USE_REDIS
except ImportError:
    REDIS_AVAILABLE = False

# Importar Redis si está disponible
if REDIS_AVAILABLE:
    try:
        import redis
        REDIS_CLIENT = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        # Probar conexión
        REDIS_CLIENT.ping()
        REDIS_ACTIVE = True
    except Exception as e:
        logging.warning(f"Redis no disponible, usando caché en memoria: {e}")
        REDIS_ACTIVE = False
        REDIS_CLIENT = None
else:
    REDIS_ACTIVE = False
    REDIS_CLIENT = None

# Caché en memoria como fallback
_memory_cache: Dict[str, Dict[str, Any]] = {}


class CacheManager:
    """Gestor de caché con soporte para Redis y memoria"""
    
    def __init__(self, prefix: str = "api"):
        self.prefix = prefix
        self.logger = logging.getLogger(f"cache.{prefix}")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Genera una clave única para el caché"""
        # Crear string con todos los argumentos
        key_data = f"{args}:{sorted(kwargs.items())}"
        # Generar hash MD5
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{self.prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del caché"""
        try:
            if REDIS_ACTIVE and REDIS_CLIENT:
                # Intentar obtener de Redis
                value = REDIS_CLIENT.get(key)
                if value:
                    return json.loads(value)
            else:
                # Usar caché en memoria
                if key in _memory_cache:
                    cache_entry = _memory_cache[key]
                    if cache_entry['expires_at'] > time.time():
                        return cache_entry['value']
                    else:
                        # Eliminar entrada expirada
                        del _memory_cache[key]
        except Exception as e:
            self.logger.warning(f"Error obteniendo del caché: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Establece un valor en el caché con TTL"""
        try:
            if REDIS_ACTIVE and REDIS_CLIENT:
                # Guardar en Redis
                return REDIS_CLIENT.setex(key, ttl, json.dumps(value))
            else:
                # Guardar en memoria
                _memory_cache[key] = {
                    'value': value,
                    'expires_at': time.time() + ttl
                }
                return True
        except Exception as e:
            self.logger.warning(f"Error guardando en caché: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Elimina una clave del caché"""
        try:
            if REDIS_ACTIVE and REDIS_CLIENT:
                return bool(REDIS_CLIENT.delete(key))
            else:
                if key in _memory_cache:
                    del _memory_cache[key]
                    return True
        except Exception as e:
            self.logger.warning(f"Error eliminando del caché: {e}")
        
        return False
    
    def clear(self, pattern: str = None) -> int:
        """Limpia el caché"""
        try:
            if REDIS_ACTIVE and REDIS_CLIENT:
                if pattern:
                    keys = REDIS_CLIENT.keys(f"{self.prefix}:{pattern}")
                else:
                    keys = REDIS_CLIENT.keys(f"{self.prefix}:*")
                if keys:
                    return REDIS_CLIENT.delete(*keys)
            else:
                if pattern:
                    # Eliminar claves que coincidan con el patrón
                    keys_to_delete = [k for k in _memory_cache.keys() if pattern in k]
                else:
                    keys_to_delete = list(_memory_cache.keys())
                
                for key in keys_to_delete:
                    del _memory_cache[key]
                return len(keys_to_delete)
        except Exception as e:
            self.logger.warning(f"Error limpiando caché: {e}")
        
        return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché"""
        try:
            if REDIS_ACTIVE and REDIS_CLIENT:
                info = REDIS_CLIENT.info()
                return {
                    "type": "redis",
                    "connected": True,
                    "keys": len(REDIS_CLIENT.keys(f"{self.prefix}:*")),
                    "memory_used": info.get('used_memory_human', 'N/A'),
                    "uptime": info.get('uptime_in_seconds', 0)
                }
            else:
                return {
                    "type": "memory",
                    "connected": True,
                    "keys": len(_memory_cache),
                    "memory_used": "N/A",
                    "uptime": 0
                }
        except Exception as e:
            return {
                "type": "unknown",
                "connected": False,
                "error": str(e)
            }


# Instancia global del caché
cache_manager = CacheManager()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorador para cachear resultados de funciones
    
    Args:
        ttl: Tiempo de vida en segundos (default: 5 minutos)
        key_prefix: Prefijo adicional para la clave del caché
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave única
            cache_key = cache_manager._generate_key(
                f"{key_prefix}:{func.__name__}", *args, **kwargs
            )
            
            # Intentar obtener del caché
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Ejecutar función y cachear resultado
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def cache_response(ttl: int = 300, key_fields: List[str] = None):
    """
    Decorador para cachear respuestas de endpoints de FastAPI
    
    Args:
        ttl: Tiempo de vida en segundos
        key_fields: Campos específicos a incluir en la clave del caché
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave basada en parámetros de la función
            cache_data = {}
            
            # Incluir campos específicos si se especifican
            if key_fields:
                for field in key_fields:
                    if field in kwargs:
                        cache_data[field] = kwargs[field]
            
            # Incluir argumentos posicionales
            if args:
                cache_data['args'] = args
            
            cache_key = cache_manager._generate_key(
                f"endpoint:{func.__name__}", **cache_data
            )
            
            # Intentar obtener del caché
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Ejecutar función y cachear resultado
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern: str = None):
    """
    Decorador para invalidar caché después de operaciones de escritura
    
    Args:
        pattern: Patrón para eliminar claves específicas del caché
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidar caché
            if pattern:
                cache_manager.clear(pattern)
            else:
                # Invalidar todo el caché del módulo
                module_name = func.__module__.split('.')[-1]
                cache_manager.clear(module_name)
            
            return result
        return wrapper
    return decorator
