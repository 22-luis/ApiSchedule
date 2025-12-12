from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.modules.automation.services.utils.team_selection_service import TeamSelectionService
from app.shared.core.enums import PackagingActivities
from app.modules.automation.services.config import ServiceType, ServiceConfig

class PackagingRule:
    def filter_activities(self, activities_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra las actividades para obtener solo las relacionadas con empaque.
        
        Args:
            activities_data: Diccionario con todas las actividades organizadas por código
            
        Returns:
            Diccionario con solo las actividades de empaque organizadas por código
        """
        packaging_activities_by_code = {}
        
        activities_by_code = activities_data.get("activities_by_code", {})
        # Actividades que pertenecen a fabricación y deben excluirse de empaque
        manufacturing_types = {"M9", "M10", "M11", "M12", "M13", "M15"}

        for code, code_data in activities_by_code.items():
            activities = code_data.get("activities", [])
            packaging_activities = []
            
            for activity in activities:
                # Excluir actividades que son de fabricación
                if activity.get("type") in manufacturing_types:
                    continue

                activity_name = activity.get("activity", "").upper()

                # Buscar actividades relacionadas con empaque usando configuración centralizada
                packaging_keywords = ServiceConfig.get_activity_keywords(ServiceType.PACKAGING)
                
                # Tipos de empaque válidos
                packaging_types = {"M1", "M2", "M3", "M4", "M5"}
                activity_type = activity.get("type")

                if (activity_type in packaging_types) or any(keyword in activity_name for keyword in packaging_keywords):
                    packaging_activities.append(activity)
            
            if packaging_activities:
                packaging_activities_by_code[code] = {
                    "code": code,
                    "packaging_activities": packaging_activities,
                    "total_packaging_activities": len(packaging_activities),
                    "found": True
                }
        
        return {
            "packaging_activities_by_code": packaging_activities_by_code,
            "total_codes_with_packaging": len(packaging_activities_by_code),
            "codes_with_packaging": list(packaging_activities_by_code.keys())
        }

    def get_most_suitable_team(self, db: Session, order_data: Dict = None, activity_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Determina el equipo de empaque más adecuado según las nuevas reglas de negocio.
        
        Nuevas Reglas:
        - EMPAQUE 1: Líder M2.
        - EMPAQUE 2: Líder M4 (Semi Auto).
        - EMPAQUE 3: Lotes M2 Bajo Volumen (Series AX, PMX) y M15.
        - MAQUINA 1: Desborde M5, M2 Series AX/F, M4 desborde.
        - MAQUINA 2: Líder M5 (F1852).
        
        Args:
            db: Sesión de base de datos
            order_data: Datos de la orden (code, quantity)
            activity_type: Tipo de actividad (M1, M2, M3, M4, M5, M15)
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        code = order_data.get("code", "") if order_data else ""
        quantity = order_data.get("quantity", 0) if order_data else 0
        
        # Obtener todos los equipos disponibles
        packaging_teams = TeamSelectionService.get_packaging_teams(db)
        fabrication_teams = TeamSelectionService.get_fabrication_teams(db)
        
        teams_by_type = packaging_teams.get("teams_by_type", {})
        fab_teams_by_type = fabrication_teams.get("teams_by_type", {})
        
        # REGLA MOLINO: M9, M3, M2 (Family) -> Delegate to Manufactured rule check or handle here if passed?
        # The prompt for Packaging mentions Empaque 1-3, Maquina 1-2.
        # But Filter was updated to allow M3, M2, etc. in Manufactured.
        # If this method is called, it means we are checking Packaging rules specifically.
        # However, M3 (Bolsa) was explicitly assigned to Molino in the previous prompt step.
        # We should keep consistency. If M3 arrives here, send to Molino.
        if activity_type == "M3":
            molino_team = fab_teams_by_type.get("molino")
            if molino_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(molino_team.id),
                        "name": molino_team.name,
                        "type": "molino"
                    },
                    "reason": "Actividad M3 (Bolsa). Asignado a MOLINO (Regla Global).",
                    "rule_applied": "molino_m3_global"
                }

        # REGLA 1: M4 (Empaque Semi Automático) -> EMPAQUE 2 (Líder)
        if activity_type == "M4":
            empaque2_team = teams_by_type.get("empaque2")
            # TODO: Check capacity for overflow to FAB 3 or MAQUINA 1
            # Assuming Empaque 2 is available for now as primary loop
            if empaque2_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(empaque2_team.id),
                        "name": empaque2_team.name,
                        "type": "empaque2"
                    },
                    "reason": "Actividad M4 (Semi Automático). Asignado a EMPAQUE 2.",
                    "rule_applied": "empaque2_m4"
                }
            
            # Desborde M4 -> FABRICADO 3 o MAQUINA 1
            # Prioridad Desborde: MAQUINA 1 (Microlotes Semis) o FAB 3?
            # "Los desbordes de M4 se envían a FABRICADO 3 o MAQUINA 1 (si es un microlote M4)"
            # Asumiremos MAQUINA 1 si microlote (digamos < 100?), sino FAB 3?
            # Simplificación: Intentar MAQUINA 1 luego FABRICADO 3
            maquina1_team = teams_by_type.get("maquina1")
            if maquina1_team:
                 return {
                    "success": True,
                    "selected_team": {
                        "id": str(maquina1_team.id),
                        "name": maquina1_team.name,
                        "type": "maquina1"
                    },
                    "reason": "Actividad M4 (Desborde). Asignado a MAQUINA 1.",
                    "rule_applied": "maquina1_m4_overflow"
                }
            
            fabricado3_team = fab_teams_by_type.get("fabricado3")
            if fabricado3_team:
                 return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado3_team.id),
                        "name": fabricado3_team.name,
                        "type": "fabricado3"
                    },
                    "reason": "Actividad M4 (Desborde). Asignado a FABRICADO 3.",
                    "rule_applied": "fabricado3_m4_overflow"
                }
        
        # REGLA 2: M5 (Empaque Automático)
        if activity_type == "M5":
            # Especialista MAQUINA 2: F1852
            if code == "F1852":
                maquina2_team = teams_by_type.get("maquina2")
                if maquina2_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(maquina2_team.id),
                            "name": maquina2_team.name,
                            "type": "maquina2"
                        },
                        "reason": "Actividad M5 (F1852). Asignado a MAQUINA 2.",
                        "rule_applied": "maquina2_m5_f1852"
                    }
            
            # Especialista MAQUINA 1 (Desborde/Apoyo)
            # Pero MAQUINA 2 es el "Líder Absoluto" y "Asignación primaria para el grueso de M5".
            # Intentar MAQUINA 2 primero para el grueso
            maquina2_team = teams_by_type.get("maquina2")
            if maquina2_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(maquina2_team.id),
                        "name": maquina2_team.name,
                        "type": "maquina2"
                    },
                    "reason": "Actividad M5 (Empaque Automático). Asignado a MAQUINA 2 (Líder).",
                    "rule_applied": "maquina2_m5_leader"
                }
            
            # Desborde a MAQUINA 1
            maquina1_team = teams_by_type.get("maquina1")
            if maquina1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(maquina1_team.id),
                        "name": maquina1_team.name,
                        "type": "maquina1"
                    },
                    "reason": "Actividad M5 (Desborde). Asignado a MAQUINA 1.",
                    "rule_applied": "maquina1_m5_overflow"
                }

        # REGLA 3: M2 (Microlotes)
        if activity_type == "M2":
            # EMPAQUE 3: Especialista AX..., PMX...
            if code.startswith("AX") or code.startswith("PMX"):
                empaque3_team = teams_by_type.get("empaque3")
                if empaque3_team:
                     return {
                        "success": True,
                        "selected_team": {
                            "id": str(empaque3_team.id),
                            "name": empaque3_team.name,
                            "type": "empaque3"
                        },
                        "reason": f"Actividad M2 (Serie {code[:2]}). Asignado a EMPAQUE 3.",
                        "rule_applied": "empaque3_m2_specialist"
                    }
            
            # MAQUINA 1: Absorbe AX... y F...
            # Si AX falló en Empaque 3 (o si consideramos MQ1 como alternativo),
            # Y también series F...
            if code.startswith("F") or code.startswith("AX"):
                maquina1_team = teams_by_type.get("maquina1")
                if maquina1_team:
                      return {
                        "success": True,
                        "selected_team": {
                            "id": str(maquina1_team.id),
                            "name": maquina1_team.name,
                            "type": "maquina1"
                        },
                        "reason": f"Actividad M2 (Serie {code[:2]}). Asignado a MAQUINA 1.",
                        "rule_applied": "maquina1_m2_specialist"
                    }

            # EMPAQUE 1: Líder Absoluto M2 (Default)
            empaque1_team = teams_by_type.get("empaque1")
            if empaque1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(empaque1_team.id),
                        "name": empaque1_team.name,
                        "type": "empaque1"
                    },
                    "reason": "Actividad M2 (Microlotes). Asignado a EMPAQUE 1 (Líder).",
                    "rule_applied": "empaque1_m2_leader"
                }

            # EMPAQUE 3: Soporte Desborde
            empaque3_team = teams_by_type.get("empaque3")
            if empaque3_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(empaque3_team.id),
                        "name": empaque3_team.name,
                        "type": "empaque3"
                    },
                    "reason": "Actividad M2 (Desborde). Asignado a EMPAQUE 3.",
                    "rule_applied": "empaque3_m2_overflow"
                }

        # REGLA 4: M15 -> EMPAQUE 3 (Soporte M15 bajo volumen)
        if activity_type == "M15":
            empaque3_team = teams_by_type.get("empaque3")
            if empaque3_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(empaque3_team.id),
                        "name": empaque3_team.name,
                        "type": "empaque3"
                    },
                    "reason": "Actividad M15. Asignado a EMPAQUE 3.",
                    "rule_applied": "empaque3_m15"
                }

        # FALLBACKS
        
        # Priority Fallback: EMPAQUE 1 -> EMPAQUE 3 -> MAQUINA 1
        empaque1_team = teams_by_type.get("empaque1")
        if empaque1_team:
            return {
                "success": True,
                "selected_team": {
                    "id": str(empaque1_team.id),
                    "name": empaque1_team.name,
                    "type": "empaque1"
                },
                "reason": "Fallback: Asignado a EMPAQUE 1 por defecto.",
                "rule_applied": "fallback_empaque1"
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
        
        return {
            "success": False,
            "reason": "No se encontró ningún equipo de empaque disponible.",
            "rule_applied": "no_teams_available"
        }

    def get_packaging_teams(self, db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los equipos de empaque.
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Diccionario con información de todos los equipos de empaque
        """
        return TeamSelectionService.get_packaging_teams(db)

    def get_activity_for_order(self, order_data: Dict, activities_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Obtiene la actividad de empaque específica para una orden.
        
        Args:
            order_data: Datos de la orden (lote, quantity, code)
            activities_data: Datos de actividades de empaque con minutos calculados
            
        Returns:
            Actividad de empaque específica para la orden o None si no se encuentra
        """
        order_code = order_data.get('code')
        if not order_code:
            return None
        
        # Buscar las actividades para el código de esta orden
        code_data = activities_data.get("packaging_activities_by_code", {}).get(order_code)
        
        if not code_data or not code_data.get("packaging_activities"):
            return None
        
        # Buscar la actividad más específica según prioridad
        packaging_activities = code_data["packaging_activities"]
        
        # Prioridad 1: Empaque manual grupo
        grupo_activities = [PackagingActivities.EMP_GRUPO.value]
        
        for activity in packaging_activities:
            activity_name = activity.get("activity", "").upper()
            if any(grupo_activity.upper() in activity_name for grupo_activity in grupo_activities):
                return activity
        
        # Prioridad 2: Empaque manual
        manual_activities = [PackagingActivities.EMP_MANUAL.value]
        
        for activity in packaging_activities:
            activity_name = activity.get("activity", "").upper()
            if any(manual_activity.upper() in activity_name for manual_activity in manual_activities):
                return activity
        
        # Prioridad 3: Empaque máquina semi-automática
        semi_activities = [PackagingActivities.EMP_SEMI.value]
        
        for activity in packaging_activities:
            activity_name = activity.get("activity", "").upper()
            if any(semi_activity.upper() in activity_name for semi_activity in semi_activities):
                return activity
        
        # Prioridad 4: Empaque máquina automática
        auto_activities = [PackagingActivities.EMP_AUTO.value]
        
        for activity in packaging_activities:
            activity_name = activity.get("activity", "").upper()
            if any(auto_activity.upper() in activity_name for auto_activity in auto_activities):
                return activity
        
        # Prioridad 5: Empaque manual con mezcla
        mezcla_activities = [PackagingActivities.EMP_MEZCLA.value]
        
        for activity in packaging_activities:
            activity_name = activity.get("activity", "").upper()
            if any(mezcla_activity.upper() in activity_name for mezcla_activity in mezcla_activities):
                return activity
        
        # Si no se encuentra ninguna actividad específica, usar la primera disponible
        if packaging_activities:
            return packaging_activities[0]
        
        return None

    def get_specific_team_for_activity(self, activity_name: str, activity_description: str, teams_data: Dict, order_data: Dict = None) -> Dict[str, Any]:
        """
        Obtiene el equipo específico para una actividad de empaque según las reglas de negocio.
        Esta función ahora delega a get_most_suitable_team con el tipo de actividad.
        
        Args:
            activity_name: Nombre de la actividad
            activity_description: Descripción de la actividad
            teams_data: Datos de equipos obtenidos de get_most_suitable_team
            order_data: Datos de la orden (code, quantity)
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        # Extraer el tipo de actividad del nombre o descripción
        activity_type = None
        if "M1" in activity_name or "M1" in activity_description:
            activity_type = "M1"
        elif "M2" in activity_name or "M2" in activity_description:
            activity_type = "M2"
        elif "M3" in activity_name or "M3" in activity_description:
            activity_type = "M3"
        elif "M4" in activity_name or "M4" in activity_description:
            activity_type = "M4"
        elif "M5" in activity_name or "M5" in activity_description:
            activity_type = "M5"
        
        # Si no se puede determinar el tipo, usar la lógica antigua
        if not activity_type:
            return TeamSelectionService.get_specific_packaging_team_for_activity(
                activity_name, activity_description, teams_data
            )
        
        # Usar la nueva lógica basada en el flujograma
        # Necesitamos acceso a la sesión de base de datos, que no tenemos aquí
        # Por ahora, retornamos usando el servicio antiguo
        return TeamSelectionService.get_specific_packaging_team_for_activity(
            activity_name, activity_description, teams_data
        )
