"""
Configuración centralizada para los servicios de tareas.
Define constantes, límites de tiempo y configuraciones compartidas.
"""

from datetime import time
from enum import Enum


class ServiceType(Enum):
    """Tipos de servicios disponibles"""
    WEIGHING = "weighing"
    FABRICATION = "fabrication"
    PACKAGING = "packaging"


class TimeLimits:
    """Límites de tiempo para diferentes tipos de servicios"""
    
    # Límite de tiempo para actividades de pesado: 17:40
    WEIGHING = time(17, 40)
    
    # Límite de tiempo para actividades de fabricación: 14:40
    FABRICATION = time(14, 40)
    
    # Límite de tiempo para actividades de empaque: 14:40 (mismo que fabricación)
    PACKAGING = time(14, 40)
    
    # Tolerancia en minutos para todos los servicios
    TOLERANCE_MINUTES = 5


class ActivityKeywords:
    """Palabras clave para identificar tipos de actividades"""
    
    # Actividades de pesado
    WEIGHING_KEYWORDS = [
        "PESADO", "PESAR", "PESO", "BALANZA", "WEIGHING"
    ]
    
    # Actividades de fabricación
    FABRICATION_KEYWORDS = [
        "FABRICACION", "FABRICADO", "MEZCLA", "MOLIENDA", "MOLINO",
        "PASTA", "POLVO", "LIQUIDA", "MAQUINA", "MANUAL", "ADEREZOS", "JALEAS"
    ]
    
    # Actividades de empaque
    PACKAGING_KEYWORDS = [
        "EMPAQUE", "EMPAQUETADO", "ENVASADO", "EMBALAJE", "PACKAGING"
    ]


class TeamPriorities:
    """Prioridades para selección de equipos"""
    
    # Prioridades para equipos de pesado
    WEIGHING_PRIORITIES = [
        "principal",  # Pesado principal
        "pesado 1",   # Pesado 1
        "pesado1"     # Pesado1 (sin espacio)
    ]
    
    # Prioridades para equipos de fabricación
    FABRICATION_PRIORITIES = [
        "molino",     # Molino
        "fabricado2", # Fabricado 2 (para esencias y mezclas líquidas)
        "fabricado1", # Fabricado 1 (para mezclas)
        "fabricado3"  # Fabricado 3 (para aderezos y jaleas)
    ]
    
    # Prioridades para equipos de empaque
    PACKAGING_PRIORITIES = [
        "empaque",    # Empaque (para empaque manual grupo)
        "empaque3",   # Empaque 3 (para empaque manual)
        "empaque2",   # Empaque 2 (para esencias)
        "maquina 1",  # MAQUINA 1 (para semi-automática)
        "maquina 2"   # MAQUINA 2 (para automática)
    ]


class ServiceConfig:
    """Configuración general de servicios"""
    
    # Configuración por tipo de servicio
    CONFIGURATIONS = {
        ServiceType.WEIGHING: {
            "time_limit": TimeLimits.WEIGHING,
            "tolerance_minutes": TimeLimits.TOLERANCE_MINUTES,
            "activity_keywords": ActivityKeywords.WEIGHING_KEYWORDS,
            "team_priorities": TeamPriorities.WEIGHING_PRIORITIES,
            "description": "Servicio de pesado de materiales"
        },
        ServiceType.FABRICATION: {
            "time_limit": TimeLimits.FABRICATION,
            "tolerance_minutes": TimeLimits.TOLERANCE_MINUTES,
            "activity_keywords": ActivityKeywords.FABRICATION_KEYWORDS,
            "team_priorities": TeamPriorities.FABRICATION_PRIORITIES,
            "description": "Servicio de fabricación de productos"
        },
        ServiceType.PACKAGING: {
            "time_limit": TimeLimits.PACKAGING,
            "tolerance_minutes": TimeLimits.TOLERANCE_MINUTES,
            "activity_keywords": ActivityKeywords.PACKAGING_KEYWORDS,
            "team_priorities": TeamPriorities.PACKAGING_PRIORITIES,
            "description": "Servicio de empaque de productos"
        }
    }
    
    @classmethod
    def get_config(cls, service_type: ServiceType) -> dict:
        """
        Obtiene la configuración para un tipo de servicio específico.
        
        Args:
            service_type: Tipo de servicio
            
        Returns:
            Configuración del servicio
        """
        return cls.CONFIGURATIONS.get(service_type, {})
    
    @classmethod
    def get_time_limit(cls, service_type: ServiceType) -> time:
        """
        Obtiene el límite de tiempo para un tipo de servicio.
        
        Args:
            service_type: Tipo de servicio
            
        Returns:
            Límite de tiempo
        """
        config = cls.get_config(service_type)
        return config.get("time_limit", TimeLimits.FABRICATION)
    
    @classmethod
    def get_tolerance_minutes(cls, service_type: ServiceType) -> int:
        """
        Obtiene la tolerancia en minutos para un tipo de servicio.
        
        Args:
            service_type: Tipo de servicio
            
        Returns:
            Tolerancia en minutos
        """
        config = cls.get_config(service_type)
        return config.get("tolerance_minutes", TimeLimits.TOLERANCE_MINUTES)
    
    @classmethod
    def get_activity_keywords(cls, service_type: ServiceType) -> list:
        """
        Obtiene las palabras clave para identificar actividades de un tipo de servicio.
        
        Args:
            service_type: Tipo de servicio
            
        Returns:
            Lista de palabras clave
        """
        config = cls.get_config(service_type)
        return config.get("activity_keywords", [])
    
    @classmethod
    def get_team_priorities(cls, service_type: ServiceType) -> list:
        """
        Obtiene las prioridades de equipos para un tipo de servicio.
        
        Args:
            service_type: Tipo de servicio
            
        Returns:
            Lista de prioridades de equipos
        """
        config = cls.get_config(service_type)
        return config.get("team_priorities", [])
