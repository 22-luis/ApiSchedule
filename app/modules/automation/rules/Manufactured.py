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
            return capacity_info["is_at_limit"] or capacity_info["is_over_limit"]

        # --- NEW PRIORITY RULE: Quantities <= 5 go to PESADO ---
        if quantity <= 5:
            weighing_team_info = TeamSelectionService.get_weighing_team(db)
            if weighing_team_info.get("success"):
                weighing_team = weighing_team_info.get("most_suitable_team")
                return self.response(
                    weighing_team["id"],
                    weighing_team["name"],
                    "pesado",
                    f"Cantidad ({quantity}) <= 5. Asignado a PESADO.",
                    "fabrication_qty_le_5_pesado"
                )

        # --- A. REGLAS POR CÓDIGO Y CANTIDAD (PRIORIDAD ALTA) ---
        
        # REGLA: Códigos BX o BE con Cantidad < 13 -> FABRICADO 3
        if (code.startswith("BX") or code.startswith("BE")) and quantity < 13:
            fabricado3_team = teams_by_type.get("fabricado3")
            if fabricado3_team:
                return self.response(
                    fabricado3_team.id,
                    fabricado3_team.name,
                    "fabricado3",
                    f"Código {code[:2]} con cantidad < 13. Asignado a FABRICADO 3.",
                    "fabricado3_bx_be_lt_13"
                )

        # REGLA: Códigos BX con Cantidad > 13 -> FABRICADO 1 (con desborde a FABRICADO 2)
        if code.startswith("BX") and quantity > 13:
            fabricado1_team = teams_by_type.get("fabricado1")
            
            # Verificar capacidad de FABRICADO 1
            if fabricado1_team and check_fab1_capacity(fabricado1_team):
                fabricado2_team = teams_by_type.get("fabricado2")
                if fabricado2_team:
                    return self.response(
                        fabricado2_team.id,
                        fabricado2_team.name,
                        "fabricado2",
                        f"Código BX > 13. FABRICADO 1 saturado, asignado a FABRICADO 2.",
                        "fabricado2_bx_gt_13_overflow"
                    )
            
            if fabricado1_team:
                return self.response(
                    fabricado1_team.id,
                    fabricado1_team.name,
                    "fabricado1",
                    f"Código BX con cantidad > 13. Asignado a FABRICADO 1.",
                    "fabricado1_bx_gt_13"
                )

        # --- B. REGLAS POR TIPO DE ACTIVIDAD (PRIORIDAD MEDIA) ---

        # Regla Global para Líquidos: JARABE, ESEM, ESENCIA, DESINFECTANTE SOLUCION, LIQUIDO o unidad GL/LT
        description = order_data.get("description", "").upper()
        unit = order_data.get("unit", "").upper()
        liquid_keywords = ["JARABE", "ESEM", "ESENCIA", "DESINFECTANTE SOLUCION", "LIQUIDO"]
        is_liquid = any(k in description for k in liquid_keywords) or unit in ["GL", "LT"]

        # M13 (Mezclas Líquidas) o Productos Líquidos -> FABRICADO 3
        if activity_type == "M13" or is_liquid:
            fabricado3_team = teams_by_type.get("fabricado3")
            if fabricado3_team:
                reason = "Actividad M13 (Líquidos)" if activity_type == "M13" else "Producto Identificado como Líquido"
                return self.response(
                    fabricado3_team.id,
                    fabricado3_team.name,
                    "fabricado3",
                    f"{reason}. Asignado a FABRICADO 3.",
                    "fabricado3_liquids"
                )

        # M12 (Gran Volumen) -> FABRICADO 1 (con desborde a FABRICADO 2)
        if activity_type == "M12":
            fabricado1_team = teams_by_type.get("fabricado1")
            
            if fabricado1_team and check_fab1_capacity(fabricado1_team):
                fabricado2_team = teams_by_type.get("fabricado2")
                if fabricado2_team:
                    return self.response(
                        fabricado2_team.id,
                        fabricado2_team.name,
                        "fabricado2",
                        "Actividad M12. FABRICADO 1 saturado, desborde a FABRICADO 2.",
                        "fabricado2_m12_overflow"
                    )
            
            if fabricado1_team:
                 return self.response(
                    fabricado1_team.id,
                    fabricado1_team.name,
                    "fabricado1",
                    "Actividad M12. Asignado a FABRICADO 1.",
                    "fabricado1_m12"
                )

        # M11 / M15 -> FABRICADO 1 (con desborde a FABRICADO 2)
        if activity_type in ["M11", "M15"]:
            fabricado1_team = teams_by_type.get("fabricado1")
             
            if fabricado1_team and check_fab1_capacity(fabricado1_team):
                fabricado2_team = teams_by_type.get("fabricado2")
                if fabricado2_team:
                    return self.response(
                        fabricado2_team.id,
                        fabricado2_team.name,
                        "fabricado2",
                        f"Actividad {activity_type}. FABRICADO 1 saturado, desborde a FABRICADO 2.",
                        "fabricado2_m11_m15_overflow"
                    )
            
            if fabricado1_team:
                 return self.response(
                    fabricado1_team.id,
                    fabricado1_team.name,
                    "fabricado1",
                    f"Actividad {activity_type}. Asignado a FABRICADO 1.",
                    "fabricado1_m11_m15"
                )

        # M5 (Empaque Automático) - Reglas de Especialista
        if activity_type == "M5":
            # PTX1042 y FX185-4 -> FABRICADO 2
            if code == "PTX1042" or code == "FX185-4":
                fabricado2_team = teams_by_type.get("fabricado2")
                if fabricado2_team:
                    return self.response(
                        fabricado2_team.id,
                        fabricado2_team.name,
                        "fabricado2",
                        f"Código {code} (Especialista M5). Asignado a FABRICADO 2.",
                        "fabricado2_m5_specialist"
                    )
            
            # Series FX- (excepto la de arriba) -> FABRICADO 1
            if code.startswith("FX"):
                fabricado1_team = teams_by_type.get("fabricado1")
                if fabricado1_team:
                    return self.response(
                        fabricado1_team.id,
                        fabricado1_team.name,
                        "fabricado1",
                        f"Serie FX (Especialista M5). Asignado a FABRICADO 1.",
                        "fabricado1_m5_fx"
                    )

        # M4 (Empaque Semi Aut.) -> MAQUINAS 1 o 2 (Antes Fab 3)
        if activity_type == "M4":
             maquina1_team = teams_by_type.get("maquina1")
             if maquina1_team:
                 # Aquí no hay check de capacidad explicito en la regla, asumimos maq 1 primero
                 # O si queremos desborde, podemos implementarlo. Regla dice: "Asignado a MAQUINAS 1 o 2"
                 # Asumiremos Maquina 1 y si falla o desborda (no implementado check aun), Maquina 2.
                 # Por simplicidad y consistencia, intentemos Maquina 1.
                 return self.response(
                    maquina1_team.id,
                    maquina1_team.name,
                    "maquina1",
                    "Actividad M4. Asignado a MAQUINA 1.",
                    "maquina1_m4"
                )
             maquina2_team = teams_by_type.get("maquina2")
             if maquina2_team:
                  return self.response(
                    maquina2_team.id,
                    maquina2_team.name,
                    "maquina2",
                    "Actividad M4. Asignado a MAQUINA 2.",
                    "maquina2_m4"
                )

        # M10, M9 (Molienda, Bolsa, Microlotes Familia) -> MOLINO
        if activity_type in ["M10", "M9"]:
            molino_team = teams_by_type.get("molino")
            if molino_team:
                return self.response(
                    molino_team.id,
                    molino_team.name,
                    "molino",
                    f"Actividad {activity_type} (Molino/Bolsa). Asignado a MOLINO.",
                    "molino_m9_m10"
                )

        # --- C. FALLBACK (POR DEFECTO) ---
        
        # Fallback 1: FABRICADO 1
        fabricado1_team = teams_by_type.get("fabricado1")
        if fabricado1_team:
             return self.response(
                fabricado1_team.id,
                fabricado1_team.name,
                "fabricado1",
                "Fallback: Asignado a FABRICADO 1 por defecto.",
                "fallback_fabricado1"
            )
            
        # Fallback 2: FABRICADO 2
        fabricado2_team = teams_by_type.get("fabricado2")
        if fabricado2_team:
             return self.response(
                fabricado2_team.id,
                fabricado2_team.name,
                "fabricado2",
                "Fallback: Asignado a FABRICADO 2 por defecto.",
                "fallback_fabricado2"
            )

        # Fallback 3: FABRICADO 3
        fabricado3_team = teams_by_type.get("fabricado3")
        if fabricado3_team:
             return self.response(
                fabricado3_team.id,
                fabricado3_team.name,
                "fabricado3",
                "Fallback: Asignado a FABRICADO 3 por defecto.",
                "fallback_fabricado3"
            )

        return {
            "success": False,
            "reason": "No se encontró ningún equipo de fabricación disponible.",
            "rule_applied": "no_teams_available"
        }
