from typing import Dict, Any, Optional, Set, List
from sqlalchemy.orm import Session
from datetime import date

from app.modules.automation.services.utils.team_selection_service import TeamSelectionService
from app.modules.automation.services.utils.capacity_verification_service import CapacityVerificationService
from app.shared.core.enums import ManufacturingActivities
from app.modules.automation.services.config import ServiceType, ServiceConfig
from app.modules.automation.rules.base_rule import BaseAutomationRule

class ManufacturedRule(BaseAutomationRule):
    
    @property
    def service_type(self) -> ServiceType:
        return ServiceType.FABRICATION

    @property
    def activity_list_key(self) -> str:
        return "fabrication_activities"

    @property
    def excluded_types(self) -> Set[str]:
        return {"M1", "M7"}

    @property
    def priority_keywords_groups(self) -> List[List[str]]:
        return [
            [
                ManufacturingActivities.MOL_PASTA.value,
                ManufacturingActivities.MOL_POLVO.value
            ],
            [
                ManufacturingActivities.MEZ_MAQUINA.value,
                ManufacturingActivities.MEZ_POLVO.value,
                ManufacturingActivities.MEZ_LIQUIDA.value
            ],
            [ManufacturingActivities.FABRICACION.value]
        ]

    def response(self, name, type, reason, rule):
        return {
            "success": True,
            "selected_team": {
                "id": str(self),
                "name": name,
                "type": type
            },
            "reason": reason,
            "rule_applied": rule
        }

    def get_most_suitable_team(self, db: Session, order_data: Dict, activity_type: Optional[str] = None, programming_date: date = None) -> Dict[str, Any]:
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
                return response(fabricado3_team.id,
                                fabricado3_team.name,
                                f"fabricado3","Código {code[:2]} con cantidad < 13. Asignado a FABRICADO 3.",
                                "fabricado3_bx_be_lt_13" )


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
        if activity_type in ["M10", "M9", "M3"]:
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
