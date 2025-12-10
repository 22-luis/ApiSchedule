from datetime import time
from enum import Enum


class ServiceType(Enum):
    WEIGHING = "weighing"
    FABRICATION = "fabrication"
    PACKAGING = "packaging"


class TimeLimits:
    WEIGHING = time(17, 40)
    FABRICATION = time(14, 40)
    PACKAGING = time(14, 40)
    TOLERANCE_MINUTES = 5


class ActivityKeywords:
    WEIGHING_KEYWORDS = [
        "PESADO", "PESAR", "PESO", "BALANZA", "WEIGHING"
    ]
    
    FABRICATION_KEYWORDS = [
        "FABRICACION", "FABRICADO", "MEZCLA", "MOLIENDA", "MOLINO",
        "PASTA", "POLVO", "LIQUIDA", "MAQUINA", "MANUAL", "ADEREZOS", "JALEAS"
    ]
    
    PACKAGING_KEYWORDS = [
        "EMPAQUE", "EMPAQUETADO", "ENVASADO", "EMBALAJE", "PACKAGING"
    ]


class TeamPriorities: 
    WEIGHING_PRIORITIES = [
        "principal",  # Pesado principal
        "pesado 1",   # Pesado 1
        "pesado1",    # Pesado1 (sin espacio)
        "pesado"      # Pesado (general)
    ]
    
    FABRICATION_PRIORITIES = [
        "molino",     # Molino
        "fabricado2", # Fabricado 2 (para esencias y mezclas líquidas)
        "fabricado1", # Fabricado 1 (para mezclas)
        "fabricado3"  # Fabricado 3 (para aderezos y jaleas)
    ]

    PACKAGING_PRIORITIES = [
        "empaque",    # Empaque (para empaque manual grupo)
        "empaque3",   # Empaque 3 (para empaque manual)
        "empaque2",   # Empaque 2 (para esencias)
        "maquina 1",  # MAQUINA 1 (para semi-automática)
        "maquina 2"   # MAQUINA 2 (para automática)
    ]

# Configuración general de servicios
class ServiceConfig:
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
    
    # Obtiene la configuración para un tipo de servicio específico.
    @classmethod
    def get_config(cls, service_type: ServiceType) -> dict:
        return cls.CONFIGURATIONS.get(service_type, {})
    
    # Obtiene el límite de tiempo para un tipo de servicio.
    @classmethod
    def get_time_limit(cls, service_type: ServiceType) -> time:
        config = cls.get_config(service_type)
        return config.get("time_limit", TimeLimits.FABRICATION)
    
    # Obtiene la tolerancia en minutos para un tipo de servicio.
    @classmethod
    def get_tolerance_minutes(cls, service_type: ServiceType) -> int:
        config = cls.get_config(service_type)
        return config.get("tolerance_minutes", TimeLimits.TOLERANCE_MINUTES)
    
    # Obtiene las palabras clave para identificar actividades de un tipo de servicio.
    @classmethod
    def get_activity_keywords(cls, service_type: ServiceType) -> list:
        config = cls.get_config(service_type)
        return config.get("activity_keywords", [])
    
    # Obtiene las prioridades de equipos para un tipo de servicio.
    @classmethod
    def get_team_priorities(cls, service_type: ServiceType) -> list:
        config = cls.get_config(service_type)
        return config.get("team_priorities", [])
