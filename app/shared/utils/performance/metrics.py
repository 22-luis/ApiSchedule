"""
Sistema de métricas de performance para monitoreo de la aplicación.
Proporciona métricas de rendimiento, latencia y uso de recursos.
"""
import time
import threading
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from app.shared.utils.core.logging import get_logger

logger = get_logger("metrics")

# Importar psutil de forma opcional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil no disponible - métricas del sistema limitadas")


@dataclass
class MetricPoint:
    """Punto de métrica con timestamp y valor"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    Recolector de métricas de performance.
    
    Almacena métricas históricas y proporciona estadísticas en tiempo real.
    """
    
    def __init__(self, max_history_size: int = 1000):
        """
        Inicializa el recolector de métricas.
        
        Args:
            max_history_size: Número máximo de puntos históricos por métrica
        """
        self.max_history_size = max_history_size
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self.lock = threading.Lock()
        
        # Métricas del sistema
        self.system_metrics = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_usage_percent": 0.0,
            "network_io": {"bytes_sent": 0, "bytes_recv": 0}
        }
        
        # Contadores de requests
        self.request_counters = defaultdict(int)
        self.error_counters = defaultdict(int)
        
        # Métricas de latencia
        self.latency_metrics = defaultdict(list)
        
        logger.info("Sistema de métricas inicializado")
    
    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Registra una nueva métrica.
        
        Args:
            name: Nombre de la métrica
            value: Valor de la métrica
            labels: Etiquetas adicionales
        """
        with self.lock:
            metric_point = MetricPoint(
                timestamp=time.time(),
                value=value,
                labels=labels or {}
            )
            self.metrics[name].append(metric_point)
    
    def record_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """
        Registra métricas de una request HTTP.
        
        Args:
            endpoint: Endpoint de la request
            method: Método HTTP
            status_code: Código de estado
            duration: Duración en segundos
        """
        # Contador de requests
        key = f"{method}_{endpoint}"
        self.request_counters[key] += 1
        
        # Contador de errores
        if status_code >= 400:
            error_key = f"error_{status_code}_{method}_{endpoint}"
            self.error_counters[error_key] += 1
        
        # Latencia
        latency_key = f"latency_{method}_{endpoint}"
        self.latency_metrics[latency_key].append(duration)
        
        # Limpiar latencias antiguas (mantener solo las últimas 100)
        if len(self.latency_metrics[latency_key]) > 100:
            self.latency_metrics[latency_key] = self.latency_metrics[latency_key][-100:]
        
        # Registrar métricas
        self.record_metric("http_requests_total", 1, {
            "method": method,
            "endpoint": endpoint,
            "status_code": str(status_code)
        })
        
        self.record_metric("http_request_duration_seconds", duration, {
            "method": method,
            "endpoint": endpoint
        })
    
    def update_system_metrics(self):
        """Actualiza las métricas del sistema"""
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil no disponible - saltando actualización de métricas del sistema")
            return
        
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_metrics["cpu_percent"] = cpu_percent
            self.record_metric("system_cpu_percent", cpu_percent)
            
            # Memoria
            memory = psutil.virtual_memory()
            self.system_metrics["memory_percent"] = memory.percent
            self.record_metric("system_memory_percent", memory.percent)
            self.record_metric("system_memory_available_gb", memory.available / (1024**3))
            
            # Disco
            disk = psutil.disk_usage('/')
            self.system_metrics["disk_usage_percent"] = disk.percent
            self.record_metric("system_disk_usage_percent", disk.percent)
            self.record_metric("system_disk_free_gb", disk.free / (1024**3))
            
            # Red
            network = psutil.net_io_counters()
            self.system_metrics["network_io"] = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv
            }
            self.record_metric("system_network_bytes_sent", network.bytes_sent)
            self.record_metric("system_network_bytes_recv", network.bytes_recv)
            
        except Exception as e:
            logger.error(f"Error actualizando métricas del sistema: {e}")
    
    def get_metric_stats(self, name: str, window_minutes: int = 5) -> Dict[str, Any]:
        """
        Obtiene estadísticas de una métrica en una ventana de tiempo.
        
        Args:
            name: Nombre de la métrica
            window_minutes: Ventana de tiempo en minutos
            
        Returns:
            Dict con estadísticas de la métrica
        """
        with self.lock:
            if name not in self.metrics:
                return {"error": f"Métrica '{name}' no encontrada"}
            
            cutoff_time = time.time() - (window_minutes * 60)
            values = [
                point.value for point in self.metrics[name]
                if point.timestamp >= cutoff_time
            ]
            
            if not values:
                return {"error": f"No hay datos para '{name}' en la ventana especificada"}
            
            return {
                "name": name,
                "window_minutes": window_minutes,
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1] if values else None
            }
    
    def get_latency_stats(self, endpoint: str = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas de latencia.
        
        Args:
            endpoint: Endpoint específico (opcional)
            
        Returns:
            Dict con estadísticas de latencia
        """
        with self.lock:
            if endpoint:
                latency_key = f"latency_*_{endpoint}"
                matching_keys = [k for k in self.latency_metrics.keys() if endpoint in k]
            else:
                matching_keys = list(self.latency_metrics.keys())
            
            if not matching_keys:
                return {"error": "No hay datos de latencia disponibles"}
            
            all_latencies = []
            for key in matching_keys:
                all_latencies.extend(self.latency_metrics[key])
            
            if not all_latencies:
                return {"error": "No hay datos de latencia en la ventana especificada"}
            
            return {
                "total_requests": len(all_latencies),
                "avg_latency_ms": (sum(all_latencies) / len(all_latencies)) * 1000,
                "min_latency_ms": min(all_latencies) * 1000,
                "max_latency_ms": max(all_latencies) * 1000,
                "p95_latency_ms": sorted(all_latencies)[int(len(all_latencies) * 0.95)] * 1000,
                "p99_latency_ms": sorted(all_latencies)[int(len(all_latencies) * 0.99)] * 1000
            }
    
    def get_request_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de requests"""
        with self.lock:
            total_requests = sum(self.request_counters.values())
            total_errors = sum(self.error_counters.values())
            
            return {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": (total_errors / total_requests * 100) if total_requests > 0 else 0,
                "requests_by_endpoint": dict(self.request_counters),
                "errors_by_type": dict(self.error_counters)
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema"""
        return {
            "cpu_percent": self.system_metrics["cpu_percent"],
            "memory_percent": self.system_metrics["memory_percent"],
            "disk_usage_percent": self.system_metrics["disk_usage_percent"],
            "network_io": self.system_metrics["network_io"]
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Obtiene todas las métricas disponibles"""
        return {
            "system": self.get_system_stats(),
            "requests": self.get_request_stats(),
            "latency": self.get_latency_stats(),
            "custom_metrics": {
                name: self.get_metric_stats(name)
                for name in self.metrics.keys()
                if not name.startswith(("system_", "http_"))
            }
        }


# Instancia global del recolector de métricas
metrics_collector = MetricsCollector()


class MetricsMiddleware:
    """Middleware para recolectar métricas automáticamente"""
    
    def __init__(self, app):
        self.app = app
        self.metrics_collector = metrics_collector
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        
        # Interceptar la respuesta para obtener el status code
        status_code = 200
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            
            # Extraer información de la request
            method = scope.get("method", "UNKNOWN")
            path = scope.get("path", "/")
            
            # Registrar métricas
            self.metrics_collector.record_request(
                endpoint=path,
                method=method,
                status_code=status_code,
                duration=duration
            )


# Función para actualizar métricas del sistema periódicamente
def start_system_metrics_collector():
    """Inicia el recolector de métricas del sistema en segundo plano"""
    def collect_loop():
        while True:
            try:
                metrics_collector.update_system_metrics()
                time.sleep(30)  # Actualizar cada 30 segundos
            except Exception as e:
                logger.error(f"Error en recolector de métricas: {e}")
                time.sleep(60)  # Esperar más tiempo en caso de error
    
    thread = threading.Thread(target=collect_loop, daemon=True)
    thread.start()
    logger.info("Recolector de métricas del sistema iniciado")


# Decorador para medir performance de funciones
def measure_performance(metric_name: str):
    """
    Decorador para medir el performance de una función.
    
    Args:
        metric_name: Nombre de la métrica a registrar
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                metrics_collector.record_metric(f"{metric_name}_duration", duration)
                metrics_collector.record_metric(f"{metric_name}_success", 1)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_metric(f"{metric_name}_duration", duration)
                metrics_collector.record_metric(f"{metric_name}_error", 1)
                raise
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics_collector.record_metric(f"{metric_name}_duration", duration)
                metrics_collector.record_metric(f"{metric_name}_success", 1)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_metric(f"{metric_name}_duration", duration)
                metrics_collector.record_metric(f"{metric_name}_error", 1)
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
