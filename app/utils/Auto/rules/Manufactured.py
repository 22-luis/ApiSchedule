from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.utils.team_selection_service import TeamSelectionService
from app.core.enums import ManufacturingActivities
from app.services.config import ServiceType, ServiceConfig

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

    def get_most_suitable_team(self, db: Session, order_data: Dict, activity_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Determina el equipo de fabricación más adecuado según las reglas de negocio.
        
        Reglas:
        1. Fabricado 1: Códigos que inician con BX y la cantidad a producir es > 13.
        2. Fabricado 2: Aplican EXACTAMENTE las mismas condiciones que Fabricado 1.
        3. Fabricado 3: Códigos que inician con BX o BE y la cantidad a producir es < 13.
        4. Fabricado 3: Códigos de tipo M13.
        5. Molino: Códigos de tipo M9 y M10.
        
        Args:
            db: Sesión de base de datos
            order_data: Datos de la orden (lote, quantity, code)
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        code = order_data.get("code", "")
        quantity = order_data.get("quantity", 0)
        
        # Obtener todos los equipos de fabricación
        teams_data = TeamSelectionService.get_fabrication_teams(db)
        teams_by_type = teams_data.get("teams_by_type", {})
        
        # Si se proporciona el tipo de actividad, priorizar asignación basada en él
        if activity_type:
            if activity_type == "M9" or activity_type == "M10":
                molino_team = teams_by_type.get("molino")
                if molino_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(molino_team.id),
                            "name": molino_team.name,
                            "type": "molino"
                        },
                        "reason": f"Actividad de tipo {activity_type}. Asignado al grupo Molino.",
                        "rule_applied": "molino_m9_m10"
                    }

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
                        "reason": "Actividad M13: asignado a Fabricado 3.",
                        "rule_applied": "fabricado3_m13"
                    }

            if activity_type == "M12":
                # M12 puede ir a Fabricado1 o Fabricado2
                fabricado1_team = teams_by_type.get("fabricado1")
                if fabricado1_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(fabricado1_team.id),
                            "name": fabricado1_team.name,
                            "type": "fabricado1"
                        },
                        "reason": "Actividad M12: asignado a Fabricado 1.",
                        "rule_applied": "fabricado1_m12"
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
                        "reason": "Actividad M12: Fabricado 1 no disponible, asignado a Fabricado 2.",
                        "rule_applied": "fabricado2_m12"
                    }

        # Regla: códigos tipo M11 o M15 -> Fabricado 1
        if "M11" in code or "M15" in code:
            fabricado1_team = teams_by_type.get("fabricado1")
            if fabricado1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado1_team.id),
                        "name": fabricado1_team.name,
                        "type": "fabricado1"
                    },
                    "reason": f"Código de tipo M11/M15. Asignado a Fabricado 1.",
                    "rule_applied": "fabricado1_m11_m15"
                }

        # Reglas para Fabricado 1 y 2: códigos que inician con BX y cantidad > 13
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
                    "reason": f"Código inicia con BX y cantidad > 13. Asignado a Fabricado 1.",
                    "rule_applied": "fabricado1_bx_gt_13"
                }

            # Fabricado 2 actúa como fallback cuando Fabricado 1 no está disponible
            fabricado2_team = teams_by_type.get("fabricado2")
            if fabricado2_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado2_team.id),
                        "name": fabricado2_team.name,
                        "type": "fabricado2"
                    },
                    "reason": f"Código inicia con BX y cantidad > 13. Fabricado 1 no disponible, asignado a Fabricado 2.",
                    "rule_applied": "fabricado2_bx_gt_13"
                }

        # Reglas para Fabricado 3
        if ((code.startswith("BX") or code.startswith("BE")) and quantity < 13) or "M13" in code:
            fabricado3_team = teams_by_type.get("fabricado3")
            if fabricado3_team:
                reason = (
                    f"Código de tipo M13. Asignado a Fabricado 3."
                    if "M13" in code
                    else f"Código inicia con {code[:2]} y cantidad < 13. Asignado a Fabricado 3."
                )
                rule = "fabricado3_m13" if "M13" in code else "fabricado3_bx_be_lt_13"
                
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado3_team.id),
                        "name": fabricado3_team.name,
                        "type": "fabricado3"
                    },
                    "reason": reason,
                    "rule_applied": rule
                }
        
        # Fallback: si no se cumple ninguna regla, asignar a Fabricado 1 si está disponible,
        # luego Fabricado 2, Fabricado 3, y por último cualquier otro equipo disponible
        fabricado1_team = teams_by_type.get("fabricado1")
        fabricado2_team = teams_by_type.get("fabricado2")
        fabricado3_team = teams_by_type.get("fabricado3")

        if fabricado1_team:
            return {
                "success": True,
                "selected_team": {
                    "id": str(fabricado1_team.id),
                    "name": fabricado1_team.name,
                    "type": "fabricado1"
                },
                "reason": "Fallback: Asignado a Fabricado 1 por defecto.",
                "rule_applied": "fallback_fabricado1"
            }

        if fabricado2_team:
            return {
                "success": True,
                "selected_team": {
                    "id": str(fabricado2_team.id),
                    "name": fabricado2_team.name,
                    "type": "fabricado2"
                },
                "reason": "Fallback: Asignado a Fabricado 2 por defecto.",
                "rule_applied": "fallback_fabricado2"
            }

        if fabricado3_team:
            return {
                "success": True,
                "selected_team": {
                    "id": str(fabricado3_team.id),
                    "name": fabricado3_team.name,
                    "type": "fabricado3"
                },
                "reason": "Fallback: Asignado a Fabricado 3 por defecto.",
                "rule_applied": "fallback_fabricado3"
            }

        # Fallback: si no se cumple ninguna regla, asignar a Fabricado 1 si está disponible
        fabricado1_team = teams_by_type.get("fabricado1")
        if fabricado1_team:
            return {
                "success": True,
                "selected_team": {
                    "id": str(fabricado1_team.id),
                    "name": fabricado1_team.name,
                    "type": "fabricado1"
                },
                "reason": "Fallback: Asignado a Fabricado 1 por defecto.",
                "rule_applied": "fallback_fabricado1"
            }

        # Si Fabricado 1 no está disponible, intentar con cualquier otro equipo
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

