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
        # Actividades que deben ser consideradas como empaque y por tanto excluidas
        # Solo excluimos M1 que es Empaque puro sin componente de fabricación asignado
        packaging_types = {"M1"}

        for code, code_data in activities_by_code.items():
            activities = code_data.get("activities", [])
            fabrication_activities = []
            
            # Buscar actividades relacionadas con fabricación usando configuración centralizada
            fabrication_keywords = ServiceConfig.get_activity_keywords(ServiceType.FABRICATION)
            
            for activity in activities:
                # Excluir actividades que son de empaque
                activity_type = activity.get("type")
                # Actividades que deben ser consideradas como empaque y por tanto excluidas
                if activity_type == "M1":
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
        Determina el equipo de fabricación más adecuado según las nuevas reglas de negocio.
        
        Args:
            db: Sesión de base de datos
            order_data: Datos de la orden (lote, quantity, code)
            activity_type: Tipo de actividad
            programming_date: Fecha de programación
            
        Returns:
            Diccionario con el equipo seleccionado y la razón
        """
        code = order_data.get("code", "")
        quantity = order_data.get("quantity", 0)
        
        # Obtener todos los equipos de fabricación
        teams_data = TeamSelectionService.get_fabrication_teams(db)
        teams_by_type = teams_data.get("teams_by_type", {})
        
        # Helper para verificar capacidad de FABRICADO 1
        def check_fab1_capacity(fab1_team):
            if not programming_date or not fab1_team:
                return False # Asume que tiene capacidad si no hay fecha
                
            capacity_info = CapacityVerificationService.check_team_capacity(
                db, str(fab1_team.id), programming_date
            )
            # Límite: 455-465 minutos (usamos is_over_limit o is_at_limit del servicio)
            # El servicio define min_capacity y max_capacity para is_at_limit
            # Si is_over_limit es True, definitivamente desborda.
            # Según regla: "si supera 455-465", es decir si ya está lleno.
            return capacity_info["is_at_limit"] or capacity_info["is_over_limit"]

        # --- REGLAS POR CÓDIGO Y CANTIDAD (PRIORIDAD ALTA) ---
        
        # REGLA: Códigos BX o BE con Cantidad < 13 -> FABRICADO 3
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

        # REGLA: Códigos BX con Cantidad > 13 -> FABRICADO 1
        if code.startswith("BX") and quantity > 13:
            fabricado1_team = teams_by_type.get("fabricado1")
            if fabricado1_team:
                # Verificar Capacidad
                if check_fab1_capacity(fabricado1_team):
                     fabricado2_team = teams_by_type.get("fabricado2")
                     if fabricado2_team:
                        return {
                            "success": True,
                            "selected_team": {
                                "id": str(fabricado2_team.id),
                                "name": fabricado2_team.name,
                                "type": "fabricado2"
                            },
                            "reason": f"Código BX > 13. FABRICADO 1 saturado, asignado a FABRICADO 2.",
                            "rule_applied": "fabricado2_bx_gt_13_overflow"
                        }
                
                # Si tiene capacidad
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

        # --- REGLAS POR TIPO DE ACTIVIDAD (TYPE) ---

        # M13 (Mezclas Líquidas) -> FABRICADO 3 (Líder Absoluto)
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
                    "reason": "Actividad M13 (Líquidos). Asignado a FABRICADO 3.",
                    "rule_applied": "fabricado3_m13"
                }
        
        # M10 (Equilibrio) -> FABRICADO 1 (Especialista Único)
        if activity_type == "M10":
             fabricado1_team = teams_by_type.get("fabricado1")
             if fabricado1_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado1_team.id),
                        "name": fabricado1_team.name,
                        "type": "fabricado1"
                    },
                    "reason": "Actividad M10 (Equilibrio). Asignado a FABRICADO 1.",
                    "rule_applied": "fabricado1_m10"
                }

        # M12 (Gran Volumen)
        if activity_type == "M12":
            fabricado1_team = teams_by_type.get("fabricado1")
            
            # Verificar capacidad de FABRICADO 1
            if fabricado1_team and check_fab1_capacity(fabricado1_team):
                # Desborde a FABRICADO 2
                fabricado2_team = teams_by_type.get("fabricado2")
                if fabricado2_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(fabricado2_team.id),
                            "name": fabricado2_team.name,
                            "type": "fabricado2"
                        },
                        "reason": "Actividad M12. FABRICADO 1 saturado, desborde a FABRICADO 2.",
                        "rule_applied": "fabricado2_m12_overflow"
                    }
            
            # Si hay capacidad en FAB 1 o FAB 2 no existe
            if fabricado1_team:
                 return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado1_team.id),
                        "name": fabricado1_team.name,
                        "type": "fabricado1"
                    },
                    "reason": "Actividad M12 (Gran Volumen). Asignado a FABRICADO 1.",
                    "rule_applied": "fabricado1_m12"
                }

        # M11 / M15 (Mezcla Manual / Aderezos)
        if activity_type in ["M11", "M15"]:
            fabricado1_team = teams_by_type.get("fabricado1")
             # Verificar capacidad de FABRICADO 1
            if fabricado1_team and check_fab1_capacity(fabricado1_team):
                # Desborde a FABRICADO 2
                fabricado2_team = teams_by_type.get("fabricado2")
                if fabricado2_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(fabricado2_team.id),
                            "name": fabricado2_team.name,
                            "type": "fabricado2"
                        },
                        "reason": f"Actividad {activity_type}. FABRICADO 1 saturado, desborde a FABRICADO 2.",
                        "rule_applied": "fabricado2_m11_m15_overflow"
                    }
            
            if fabricado1_team:
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

        # M5 (Empaque Automático) - Reglas de Especialista
        if activity_type == "M5":
            # PTX1042 y FX185-4 -> FABRICADO 2
            if code == "PTX1042" or code == "FX185-4":
                fabricado2_team = teams_by_type.get("fabricado2")
                if fabricado2_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(fabricado2_team.id),
                            "name": fabricado2_team.name,
                            "type": "fabricado2"
                        },
                        "reason": f"Código {code} (Especialista M5). Asignado a FABRICADO 2.",
                        "rule_applied": "fabricado2_m5_specialist"
                    }
            
            # Series FX- (excepto la de arriba) -> FABRICADO 1
            if code.startswith("FX"):
                fabricado1_team = teams_by_type.get("fabricado1")
                if fabricado1_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(fabricado1_team.id),
                            "name": fabricado1_team.name,
                            "type": "fabricado1"
                        },
                        "reason": f"Serie FX (Especialista M5). Asignado a FABRICADO 1.",
                        "rule_applied": "fabricado1_m5_fx"
                    }

        # M2 (Microlotes/Manual) -> FABRICADO 3 (REMOVED - Now Molino)
        # if activity_type == "M2": ... (Removed logic)

        # M4 (Empaque Semi Aut.) -> FABRICADO 3 (Soporte/Desborde de EMPAQUE 2, asumimos que viene aquí si no es empaque)
        # Nota: El usuario menciona M4 en FABRICADO 3: "Soporte/Desborde de EMPAQUE 2".
        if activity_type == "M4":
             fabricado3_team = teams_by_type.get("fabricado3")
             if fabricado3_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(fabricado3_team.id),
                        "name": fabricado3_team.name,
                        "type": "fabricado3"
                    },
                    "reason": "Actividad M4. Asignado a FABRICADO 3.",
                    "rule_applied": "fabricado3_m4"
                }

        # M7 (Máximo Volumen) - Regla Complementaria
        # "Absorbe volumen bajo de M7" en FABRICADO 3
        # "Maneja desborde de M7" en FABRICADO 1
        # Interpretación: Cantidad baja -> FAB 3, Cantidad alta -> FAB 1
        if activity_type == "M7":
            if quantity < 13: # Usamos el mismo umbral de "bajo volumen" que en otras reglas
                 fabricado3_team = teams_by_type.get("fabricado3")
                 if fabricado3_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(fabricado3_team.id),
                            "name": fabricado3_team.name,
                            "type": "fabricado3"
                        },
                        "reason": "Actividad M7 (< 13). Asignado a FABRICADO 3.",
                        "rule_applied": "fabricado3_m7_low"
                    }
            else:
                 fabricado1_team = teams_by_type.get("fabricado1")
                 if fabricado1_team:
                    return {
                        "success": True,
                        "selected_team": {
                            "id": str(fabricado1_team.id),
                            "name": fabricado1_team.name,
                            "type": "fabricado1"
                        },
                        "reason": "Actividad M7 (> 13). Asignado a FABRICADO 1.",
                        "rule_applied": "fabricado1_m7_high"
                    }

        # M9 (Molienda) -> MOLINO (Mantener regla anterior si aplica, usuario no especificó cambio para M9 pero M10 cambio a FAB1)
        # El usuario NO mencionó MOLINO explícitamente en el nuevo prompt, pero M9 suele ser molienda.
        # "1. FABRICADO 1 ... M10 (Equilibrio)"
        # Asumiremos que si no está en las reglas nuevas, mantenemos lógica existente o fallback.
        # REGLA MOLINO: M9 (Pulverización) y M3 (Bolsa) -> MOLINO
        if activity_type in ["M9", "M3"]:
            molino_team = teams_by_type.get("molino")
            if molino_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(molino_team.id),
                        "name": molino_team.name,
                        "type": "molino"
                    },
                    "reason": f"Actividad {activity_type} (Molino/Bolsa). Asignado a MOLINO.",
                    "rule_applied": "molino_m9_m3"
                }
        
        # REGLA MOLINO: M2 (Microlotes) -> MOLINO (Absorción Familia)
        # Nota: Previamente M2 iba a FAB 3, ahora PROMPT dice MOLINO.
        if activity_type == "M2":
             molino_team = teams_by_type.get("molino")
             if molino_team:
                return {
                    "success": True,
                    "selected_team": {
                        "id": str(molino_team.id),
                        "name": molino_team.name,
                        "type": "molino"
                    },
                    "reason": "Actividad M2 (Microlotes Familia). Asignado a MOLINO.",
                    "rule_applied": "molino_m2"
                }

        # FALLBACKS
        
        # Fallback 1: FABRICADO 1
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
            
        # Fallback 2: FABRICADO 2
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

        # Fallback 3: FABRICADO 3
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

        return {
            "success": False,
            "reason": "No se encontró ningún equipo de fabricación disponible.",
            "rule_applied": "no_teams_available"
        }
