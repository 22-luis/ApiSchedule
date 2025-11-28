"""
Servicio para obtener el código de fabricación de un código de empaque.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.modules.codes.models.code import Code
from app.shared.utils.core.logging import get_logger

logger = get_logger("services.fabrication_code_finder")


class FabricationCodeFinder:
    """
    Encuentra el código de fabricación asociado a un código de empaque.
    
    Estrategia:
    1. Buscar en Code.fabricationCode si existe
    2. Si no, generar variantes del código y buscar en tabla Code
    """
    
    # Sufijos conocidos de variantes
    VARIANT_SUFFIXES = [
        '',      # Sin sufijo (código base)
        '-V',    # Variación/Versión
        '-L',    # Long/Largo  
        '-F',    # Formato/Tipo
        '-8',    # Número de variante
        '-5',    # Número de variante
        '-B',    # Variación/Base
        '-C',    # Variación/Custom
        '-A',    # Variación/Alterna
        '-DOC',  # Documentación
        '-1', '-2', '-3', '-4', '-6', '-7', '-9',  # Otros números
    ]
    
    @classmethod
    def find_fabrication_code(cls, packaging_code: str, db: Session) -> Optional[str]:
        """
        Encuentra el código de fabricación para un código de empaque.
        
        Args:
            packaging_code: Código de la orden de empaque (ej: "A1012")
            db: Sesión de base de datos
            
        Returns:
            Código de fabricación o None si no se encuentra
        """
        if not packaging_code:
            return None
        
        # Paso 1: Buscar en tabla Code si tiene fabricationCode
        code_record = db.query(Code).filter(Code.code == packaging_code).first()
        
        if code_record and code_record.fabricationCode:
            logger.info(
                f"Found fabricationCode in Code table for '{packaging_code}': "
                f"{code_record.fabricationCode}"
            )
            return code_record.fabricationCode
        
        # Paso 2: Si no tiene fabricationCode, generar candidatos
        logger.info(
            f"No fabricationCode in Code table for '{packaging_code}'. "
            f"Generating candidate codes..."
        )
        
        candidate_codes = cls._generate_candidate_codes(packaging_code)
        
        # Buscar cuál de los candidatos existe en la tabla Code
        for candidate in candidate_codes:
            exists = db.query(Code).filter(Code.code == candidate).first()
            if exists:
                logger.info(
                    f"Found matching code in Code table: '{candidate}' "
                    f"(generated from '{packaging_code}')"
                )
                return candidate
        
        # Si no se encuentra ningún candidato
        logger.warning(
            f"No fabrication code found for '{packaging_code}'. "
            f"Tried candidates: {candidate_codes}"
        )
        return None
    
    @classmethod
    def _generate_candidate_codes(cls, base_code: str) -> List[str]:
        """
        Genera códigos candidatos basándose en el patrón de sufijos.
        
        Ejemplos:
        - A1012 → [AX1012, A1012-V, A1012-L, ...]
        - E1061 → [EX1061, E1061-L, E1061-F, ...]
        
        Args:
            base_code: Código base (ej: "A1012")
            
        Returns:
            Lista de códigos candidatos
        """
        candidates = []
        
        # Patrón 1: Agregar X después de la primera letra
        # A1012 → AX1012, E1061 → EX1061
        if len(base_code) > 0:
            first_letter = base_code[0]
            rest = base_code[1:]
            candidates.append(f"{first_letter}X{rest}")
        
        # Patrón 2: Código base + sufijos
        for suffix in cls.VARIANT_SUFFIXES:
            if suffix:  # Skip empty suffix
                candidates.append(f"{base_code}{suffix}")
        
        # Patrón 3: Código base sin modificar (por si la orden de fabricación tiene el mismo código)
        candidates.append(base_code)
        
        return candidates
    
    @classmethod
    def find_manufactured_order(
        cls,
        packaging_code: str,
        packaging_quantity: float,
        db: Session
    ) -> Optional[dict]:
        """
        Encuentra una orden de fabricación manufactured que coincida.
        
        Args:
            packaging_code: Código de la orden de empaque
            packaging_quantity: Cantidad de la orden de empaque
            db: Sesión de base de datos
            
        Returns:
            Dict con información de la orden encontrada o None
        """
        from app.modules.programming.models.order import Order
        from app.modules.programming.models.state import OrderStatus
        
        # Obtener código de fabricación
        fabrication_code = cls.find_fabrication_code(packaging_code, db)
        
        if not fabrication_code:
            return None
        
        # Buscar orden manufactured con ese código y cantidad
        fab_order = db.query(Order).filter(
            Order.code == fabrication_code,
            Order.status == OrderStatus.manufactured,
            Order.quantity == packaging_quantity
        ).first()
        
        if fab_order:
            return {
                "lote": fab_order.lote,
                "code": fab_order.code,
                "quantity": fab_order.quantity,
                "status": fab_order.status
            }
        
        return None
