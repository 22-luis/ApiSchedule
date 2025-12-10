from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date

from app.modules.automation.services.utils.team_selection_service import TeamSelectionService
from app.modules.automation.services.utils.capacity_verification_service import CapacityVerificationService
from app.shared.core.enums import ManufacturingActivities
from app.modules.automation.services.config import ServiceType, ServiceConfig

class ManufacturedRule:
    
    def filter_activities(self, activities_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra las actividades para obtener solo las relacionadas con fabricación.
        
        Args:
            activities_data: Diccionario con todas las actividades organizadas por código
            
        Returns:
            Diccionario con solo las actividades de fabricación organizadas por código
        """
        fabrication_activities_by_code = {}
        
        activities_by_code = activities_data.get("activities_by_code", {})
        # Actividades que deben ser consideradas como empaque y por tanto excluidas
        packaging_types = {"M1", "M2", "M3", "M4", "M5"}

        for code, code_data in activities_by_code.items():
            activities = code_data.get("activities", [])
            fabrication_activities = []
            
            # Buscar actividades relacionadas con fabricación usando configuración centralizada
            fabrication_keywords = ServiceConfig.get_activity_keywords(ServiceType.FABRICATION)
            
            for activity in activities:
                # Excluir actividades que son de empaque
                activity_type = activity.get("type")
                if activity_type in packaging_types:
                    continue

                # Excluir actividades de pesado explícitamente
                if activity_type == "M7":
                    continue

                activity_name = activity.get("activity", "").upper()

                # Incluir sólo si coincide con palabras clave de fabricación
                if any(keyword in activity_name for keyword in fabrication_keywords):
                    fabrication_activities.append(activity)
            
            if fabrication_activities:
                fabrication_activities_by_code[code] = {
                    "code": code,
                    "fabrication_activities": fabrication_activities,
                    "total_fabrication_activities": len(fabrication_activities),
                    "found": True
                }
        
        return {
            "fabrication_activities_by_code": fabrication_activities_by_code,
            "total_codes_with_fabrication": len(fabrication_activities_by_code),
            "codes_with_fabrication": list(fabrication_activities_by_code.keys())
        }

    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Obtiene la actividad de fabricación específica para una orden.
        
        Args:
            order_data: Datos de la orden (lote, quantity, code)
            activities_data: Datos de actividades de fabricación con minutos calculados
            
        Returns:
            Actividad de fabricación específica para la orden o None si no se encuentra
        """
        order_code = order_data.get('code')
        if not order_code:
            return None
        
        code_data = activities_data.get("fabrication_activities_by_code", {}).get(order_code)
        
        if not code_data or not code_data.get("fabrication_activities"):
            return None
            
        fabrication_activities = code_data["fabrication_activities"]

        # Prioridad 1: Actividades de molienda
        molienda_keywords = [
            ManufacturingActivities.MOL_PASTA.value.upper(),
            ManufacturingActivities.MOL_POLVO.value.upper()
        ]
        for activity in fabrication_activities:
            activity_name = activity.get("activity", "").upper()
            if any(keyword in activity_name for keyword in molienda_keywords):
                return activity
                
        # Prioridad 2: Actividades de mezcla
        mezcla_keywords = [
            ManufacturingActivities.MEZ_MAQUINA.value.upper(),
            ManufacturingActivities.MEZ_POLVO.value.upper(),
            ManufacturingActivities.MEZ_LIQUIDA.value.upper()
        ]
        for activity in fabrication_activities:
            activity_name = activity.get("activity", "").upper()
            if any(keyword in activity_name for keyword in mezcla_keywords):
                return activity
                
        # Prioridad 3: Actividades de fabricación general
        fabricacion_keywords = [ManufacturingActivities.FABRICACION.value.upper()]
        for activity in fabrication_activities:
            activity_name = activity.get("activity", "").upper()
            if any(keyword in activity_name for keyword in fabricacion_keywords):
                return activity
        
        # Si no se encuentra ninguna actividad específica, usar la primera disponible
        if fabrication_activities:
            return fabrication_activities[0]
        
        return None

    def get_most_suitable_team(self, db: Session, order_data: Dict, activity_type: Optional[str] = None, programming_date: date = None) -> Dict[str, Any]:
        """
        Determina el equipo de fabricación más adecuado según las reglas de negocio del flujograma.
        
        Reglas por tipo de actividad:
        - M11, M15: FABRICADO 1 (si BX y cantidad > 13, verificar capacidad → FABRICADO 2)
        - M13: FABRICADO 3 (especializado en líquidos, si BX/BE y cantidad < 13)
        - M9, M10: MOLINO (molienda)
        - M12: PESADO (mezcla en máquina, lotes grandes)
        
        Verificación de capacidad:
        - Un equipo ha llegado a su límite cuando tiene 460±5 minutos programados (455-465 minutos)
        
        Args:
            db: Sesión de base de datos
            order_data: Datos de la orden (lote, quantity, code)
            activity_type: Tipo de actividad (M9, M10, M11, M12, M13, M15)
            programming_date: Fecha de programación para verificar capacidad (opcional)
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        code = order_data.get("code", "")
        quantity = order_data.get("quantity", 0)
        
        # Obtener todos los equipos de fabricación
        teams_data = TeamSelectionService.get_fabrication_teams(db)
        teams_by_type = teams_data.get("teams_by_type", {})
        
        # REGLA 1: M9 y M10 (Molienda) -> MOLINO
        if activity_type in ["M9", "M10"]:
            molino_team = teams_by_type.get("molino")
            if molino_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(molino_team.id),
                        "name": molino_team.name,
                        "type": "molino"
                    },
                    "reason": f"Actividad {activity_type} (Molienda). Asignado a MOLINO.",
                    "rule_applied": "molino_m9_m10"
                }

        # REGLA 2: M13 (Mezclas Líquidas) -> FABRICADO 3
        if activity_type == "M13":
            fabricado3_team = teams_by_type.get("fabricado3")
            if fabricado3_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado3_team.id),
                        "name": fabricado3_team.name,
                        "type": "fabricado3"
                    },
                    "reason": "Actividad M13 (Mezclas Líquidas). Asignado a FABRICADO 3.",
                    "rule_applied": "fabricado3_m13"
                }

        # REGLA 3: M11 y M15 (Mezcla Manual Polvo / Fabricación Aderezos) -> FABRICADO 1
        # Con verificación de código BX y cantidad > 13 para prioridad alta
        # Y verificación de capacidad (460±5 minutos)
        if activity_type in ["M11", "M15"]:
            # Verificar si es código BX con cantidad > 13 (alta prioridad para FABRICADO 1)
            if code.startswith("BX") and quantity > 13:
                fabricado1_team = teams_by_type.get("fabricado1")
                if fabricado1_team:
                    # Verificar capacidad de FABRICADO 1 si se proporciona fecha de programación
                    if programming_date:
                        capacity_info = CapacityVerificationService.check_team_capacity(
                            db, str(fabricado1_team.id), programming_date
                        )
                        
                        # Si FABRICADO 1 ha llegado a su límite, asignar a FABRICADO 2
                        if capacity_info["is_at_limit"] or capacity_info["is_over_limit"]:
                            fabricado2_team = teams_by_type.get("fabricado2")
                            if fabricado2_team:
                                return {
                                    "success": True,
                                    "selected_team": {
                                        "id": str(fabricado2_team.id),
                                        "name": fabricado2_team.name,
                                        "type": "fabricado2"
                                    },
                                    "reason": f"Actividad {activity_type}, código BX y cantidad > 13. FABRICADO 1 ha llegado a su límite de capacidad ({capacity_info['total_minutes']} minutos), asignado a FABRICADO 2.",
                                    "rule_applied": "fabricado2_m11_m15_bx_gt13_capacity"
                                }
                    
                    # Si tiene capacidad o no se proporcionó fecha, asignar a FABRICADO 1
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(fabricado1_team.id),
                            "name": fabricado1_team.name,
                            "type": "fabricado1"
                        },
                        "reason": f"Actividad {activity_type}, código BX y cantidad > 13. Asignado a FABRICADO 1.",
                        "rule_applied": "fabricado1_m11_m15_bx_gt13"
                    }
                # Si FABRICADO 1 no disponible, usar FABRICADO 2
                fabricado2_team = teams_by_type.get("fabricado2")
                if fabricado2_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(fabricado2_team.id),
                            "name": fabricado2_team.name,
                            "type": "fabricado2"
                        },
                        "reason": f"Actividad {activity_type}, código BX y cantidad > 13. FABRICADO 1 no disponible, asignado a FABRICADO 2.",
                        "rule_applied": "fabricado2_m11_m15_bx_gt13"
                    }
            
            # Para M11/M15 sin condición BX > 13, asignar a FABRICADO 1 con verificación de capacidad
            fabricado1_team = teams_by_type.get("fabricado1")
            if fabricado1_team:
                # Verificar capacidad de FABRICADO 1 si se proporciona fecha de programación
                if programming_date:
                    capacity_info = CapacityVerificationService.check_team_capacity(
                        db, str(fabricado1_team.id), programming_date
                    )
                    
                    # Si FABRICADO 1 ha llegado a su límite, asignar a FABRICADO 2
                    if capacity_info["is_at_limit"] or capacity_info["is_over_limit"]:
                        fabricado2_team = teams_by_type.get("fabricado2")
                        if fabricado2_team:
                            return {
                                "success": True,
                                "selected_team": {
                                    "id": str(fabricado2_team.id),
                                    "name": fabricado2_team.name,
                                    "type": "fabricado2"
                                },
                                "reason": f"Actividad {activity_type}. FABRICADO 1 ha llegado a su límite de capacidad ({capacity_info['total_minutes']} minutos), asignado a FABRICADO 2.",
                                "rule_applied": "fabricado2_m11_m15_capacity"
                            }
                
                # Si tiene capacidad o no se proporcionó fecha, asignar a FABRICADO 1
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado1_team.id),
                        "name": fabricado1_team.name,
                        "type": "fabricado1"
                    },
                    "reason": f"Actividad {activity_type}. Asignado a FABRICADO 1.",
                    "rule_applied": "fabricado1_m11_m15"
                }
            # Fallback a FABRICADO 2 si FABRICADO 1 no está disponible
            fabricado2_team = teams_by_type.get("fabricado2")
            if fabricado2_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado2_team.id),
                        "name": fabricado2_team.name,
                        "type": "fabricado2"
                    },
                    "reason": f"Actividad {activity_type}. FABRICADO 1 no disponible, asignado a FABRICADO 2.",
                    "rule_applied": "fabricado2_m11_m15"
                }

        # REGLA 4: Códigos BX/BE con cantidad < 13 -> FABRICADO 3
        if (code.startswith("BX") or code.startswith("BE")) and quantity < 13:
            fabricado3_team = teams_by_type.get("fabricado3")
            if fabricado3_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado3_team.id),
                        "name": fabricado3_team.name,
                        "type": "fabricado3"
                    },
                    "reason": f"Código {code[:2]} con cantidad < 13. Asignado a FABRICADO 3.",
                    "rule_applied": "fabricado3_bx_be_lt_13"
                }

        # REGLA 5: Códigos BX con cantidad > 13 -> FABRICADO 1 (con fallback a FABRICADO 2)
        if code.startswith("BX") and quantity > 13:
            fabricado1_team = teams_by_type.get("fabricado1")
            if fabricado1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado1_team.id),
                        "name": fabricado1_team.name,
                        "type": "fabricado1"
                    },
                    "reason": f"Código BX con cantidad > 13. Asignado a FABRICADO 1.",
                    "rule_applied": "fabricado1_bx_gt_13"
                }
            # Fallback a FABRICADO 2
            fabricado2_team = teams_by_type.get("fabricado2")
            if fabricado2_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado2_team.id),
                        "name": fabricado2_team.name,
                        "type": "fabricado2"
                    },
                    "reason": f"Código BX con cantidad > 13. FABRICADO 1 no disponible, asignado a FABRICADO 2.",
                    "rule_applied": "fabricado2_bx_gt_13"
                }
        
        # FALLBACK: Asignar por prioridad FABRICADO 1 -> FABRICADO 2 -> FABRICADO 3 -> MOLINO
        fabricado1_team = teams_by_type.get("fabricado1")
        if fabricado1_team:
            return {
                "success": True,
                "selected_team": {
                    "id": str(fabricado1_team.id),
                    "name": fabricado1_team.name,
                    "type": "fabricado1"
                },
                "reason": "Fallback: Asignado a FABRICADO 1 por defecto.",
                "rule_applied": "fallback_fabricado1"
            }

        fabricado2_team = teams_by_type.get("fabricado2")
        if fabricado2_team:
            return {
                "success": True,
                "selected_team": {
                    "id": str(fabricado2_team.id),
                    "name": fabricado2_team.name,
                    "type": "fabricado2"
                },
                "reason": "Fallback: Asignado a FABRICADO 2 por defecto.",
                "rule_applied": "fallback_fabricado2"
            }

        fabricado3_team = teams_by_type.get("fabricado3")
        if fabricado3_team:
            return {
                "success": True,
                "selected_team": {
                    "id": str(fabricado3_team.id),
                    "name": fabricado3_team.name,
                    "type": "fabricado3"
                },
                "reason": "Fallback: Asignado a FABRICADO 3 por defecto.",
                "rule_applied": "fallback_fabricado3"
            }

        # Último fallback: cualquier equipo disponible
        for team_type, team in teams_by_type.items():
            if team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(team.id),
                        "name": team.name,
                        "type": team_type
                    },
                    "reason": f"Fallback: Asignado a {team.name} por defecto.",
                    "rule_applied": f"fallback_{team_type}"
                }

        # Si no hay equipos disponibles
        return {
            "success": False,
            "reason": "No se encontró ningún equipo de fabricación disponible.",
            "rule_applied": "no_teams_available"
        }
