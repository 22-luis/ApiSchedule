from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.modules.programming.services.utils.team_selection_service import TeamSelectionService
from app.shared.core.enums import PackagingActivities
from app.modules.programming.services.config import ServiceType, ServiceConfig

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
                if any(keyword in activity_name for keyword in packaging_keywords):
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
        Determina el equipo de empaque más adecuado según las reglas del flujograma.
        
        Reglas por tipo de actividad:
        - M4: EMPAQUE 2 (lotes grandes 100-200 unidades, códigos ER1062)
        - M5: Según código específico (F119-125→MOLINO, F1852→MAQUINA 2, resto→MAQUINA 1)
        - M1: FABRICADO 3 (microlotes/pruebas, ej. K139)
        - M3: MOLINO (código F119-125, lote ~12 unidades)
        - M2: Lógica compleja de 6 niveles de prioridad
        
        Args:
            db: Sesión de base de datos
            order_data: Datos de la orden (code, quantity)
            activity_type: Tipo de actividad (M1, M2, M3, M4, M5)
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        code = order_data.get("code", "") if order_data else ""
        quantity = order_data.get("quantity", 0) if order_data else 0
        
        # Obtener todos los equipos disponibles
        packaging_teams = TeamSelectionService.get_packaging_teams(db)
        fabrication_teams = TeamSelectionService.get_fabrication_teams(db)
        weighing_team_info = TeamSelectionService.get_weighing_team(db)
        
        teams_by_type = packaging_teams.get("teams_by_type", {})
        fab_teams_by_type = fabrication_teams.get("teams_by_type", {})
        
        # REGLA 1: M4 (Empaque Máquina Semi Automática) -> EMPAQUE 2
        if activity_type == "M4":
            empaque2_team = teams_by_type.get("empaque2")
            if empaque2_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(empaque2_team.id),
                        "name": empaque2_team.name,
                        "type": "empaque2"
                    },
                    "reason": "Actividad M4 (Empaque Semi Automático, lotes grandes 100-200 unidades). Asignado a EMPAQUE 2.",
                    "rule_applied": "empaque2_m4"
                }
        
        # REGLA 2: M5 (Empaque Máquina Automática) -> Según código
        if activity_type == "M5":
            # M5 con código F119-125 -> MOLINO
            if code.startswith("F119") or code.startswith("F120") or code.startswith("F121") or \
               code.startswith("F122") or code.startswith("F123") or code.startswith("F124") or code.startswith("F125"):
                molino_team = fab_teams_by_type.get("molino")
                if molino_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(molino_team.id),
                            "name": molino_team.name,
                            "type": "molino"
                        },
                        "reason": "Actividad M5, código F119-125 (lote fijo ~12 unidades). Asignado a MOLINO.",
                        "rule_applied": "molino_m5_f119_125"
                    }
            
            # M5 con código F1852 -> MAQUINA 2
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
                        "reason": "Actividad M5, código F1852 (lote fijo 27 unidades). Asignado a MAQUINA 2.",
                        "rule_applied": "maquina2_m5_f1852"
                    }
            
            # Resto de M5 -> MAQUINA 1
            maquina1_team = teams_by_type.get("maquina1")
            if maquina1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(maquina1_team.id),
                        "name": maquina1_team.name,
                        "type": "maquina1"
                    },
                    "reason": "Actividad M5 (lotes 25-55 unidades, códigos PM-, PG-, K1051-25). Asignado a MAQUINA 1.",
                    "rule_applied": "maquina1_m5"
                }
        
        # REGLA 3: M1 (Empaque Manual más Mezcla) -> FABRICADO 3
        if activity_type == "M1":
            fabricado3_team = fab_teams_by_type.get("fabricado3")
            if fabricado3_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado3_team.id),
                        "name": fabricado3_team.name,
                        "type": "fabricado3"
                    },
                    "reason": "Actividad M1 (Empaque Manual más Mezcla, microlotes/pruebas). Asignado a FABRICADO 3.",
                    "rule_applied": "fabricado3_m1"
                }
        
        # REGLA 4: M3 (Empaque Bolsa de 50, 55 LB) -> MOLINO
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
                    "reason": "Actividad M3 (Empaque Bolsa 50/55 LB, código F119-125, lote ~12 unidades). Asignado a MOLINO.",
                    "rule_applied": "molino_m3"
                }
        
        # REGLA 5: M2 (Empaque Manual Grupo) -> Lógica compleja de 6 prioridades
        if activity_type == "M2":
            # Prioridad 1: PT1042 con cantidad < 15 -> MAQUINA 2
            if code == "PT1042" and quantity < 15:
                maquina2_team = teams_by_type.get("maquina2")
                if maquina2_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(maquina2_team.id),
                            "name": maquina2_team.name,
                            "type": "maquina2"
                        },
                        "reason": "Actividad M2, código PT1042 con cantidad < 15 (microlotes). Asignado a MAQUINA 2.",
                        "rule_applied": "maquina2_m2_pt1042_lt15"
                    }
            
            # Prioridad 2: F119-X25 con cantidad 1-5 -> EMPAQUE 2
            if (code.startswith("F119") and code.endswith("25")) and (1 <= quantity <= 5):
                empaque2_team = teams_by_type.get("empaque2")
                if empaque2_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(empaque2_team.id),
                            "name": empaque2_team.name,
                            "type": "empaque2"
                        },
                        "reason": "Actividad M2, código F119-X25 con cantidad 1-5 (microlotes masivos). Asignado a EMPAQUE 2.",
                        "rule_applied": "empaque2_m2_f119_x25_1_5"
                    }
            
            # Prioridad 3: Macrolotes (P1069, K2081-B) con > 150 -> EMPAQUE 1 o EMPAQUE 3
            if (code.startswith("P1069") or code.startswith("K2081")) and quantity > 150:
                empaque1_team = teams_by_type.get("empaque1")
                if empaque1_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(empaque1_team.id),
                            "name": empaque1_team.name,
                            "type": "empaque1"
                        },
                        "reason": "Actividad M2, macrolote (P1069/K2081-B) con > 150 unidades. Asignado a EMPAQUE 1.",
                        "rule_applied": "empaque1_m2_macrolote"
                    }
                # Alternar con EMPAQUE 3 si EMPAQUE 1 no disponible
                empaque3_team = teams_by_type.get("empaque3")
                if empaque3_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(empaque3_team.id),
                            "name": empaque3_team.name,
                            "type": "empaque3"
                        },
                        "reason": "Actividad M2, macrolote (P1069/K2081-B) con > 150 unidades. Asignado a EMPAQUE 3.",
                        "rule_applied": "empaque3_m2_macrolote"
                    }
            
            # Prioridad 4: Lotes medianos/grandes (A1012-V, A2138) 75-300 -> FABRICADO 1
            if (code.startswith("A1012") or code.startswith("A2138")) and (75 <= quantity <= 300):
                fabricado1_team = fab_teams_by_type.get("fabricado1")
                if fabricado1_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(fabricado1_team.id),
                            "name": fabricado1_team.name,
                            "type": "fabricado1"
                        },
                        "reason": "Actividad M2, lote mediano/grande (A1012-V/A2138) 75-300 unidades. Asignado a FABRICADO 1.",
                        "rule_applied": "fabricado1_m2_mediano"
                    }
            
            # Prioridad 5: Resto M2 con cantidad < 15 -> PESADO
            if quantity < 15:
                if weighing_team_info.get("success"):
                    weighing_team = weighing_team_info.get("most_suitable_team")
                    return {
                        "success": True,
                        "selected_team": {
                            "id": weighing_team.get("id"),
                            "name": weighing_team.get("name"),
                            "type": "pesado"
                        },
                        "reason": "Actividad M2, cantidad < 15 (microlotes secundarios). Asignado a PESADO.",
                        "rule_applied": "pesado_m2_lt15"
                    }
            
            # Prioridad 6: Resto M2 con cantidad > 15 -> EMPAQUE 1 o EMPAQUE 3
            if quantity > 15:
                empaque1_team = teams_by_type.get("empaque1")
                if empaque1_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(empaque1_team.id),
                            "name": empaque1_team.name,
                            "type": "empaque1"
                        },
                        "reason": "Actividad M2, cantidad > 15 (lotes medianos). Asignado a EMPAQUE 1.",
                        "rule_applied": "empaque1_m2_gt15"
                    }
                # Alternar con EMPAQUE 3
                empaque3_team = teams_by_type.get("empaque3")
                if empaque3_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(empaque3_team.id),
                            "name": empaque3_team.name,
                            "type": "empaque3"
                        },
                        "reason": "Actividad M2, cantidad > 15 (lotes medianos). Asignado a EMPAQUE 3.",
                        "rule_applied": "empaque3_m2_gt15"
                    }
        
        # FALLBACK: Si no se cumple ninguna regla específica
        # Intentar asignar a equipos de empaque en orden de prioridad
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
