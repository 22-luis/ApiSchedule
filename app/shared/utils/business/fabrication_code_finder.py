from typing import Optional
from sqlalchemy.orm import Session
from app.modules.codes.models.code import Code
from app.shared.utils.core.logging import get_logger

logger = get_logger("services.fabrication_code_finder")


class FabricationCodeFinder:
    """
    Encuentra el código de fabricación asociado a un código de empaque.
    
    Estrategia:
    1. Buscar en Code.fabricationCode si existe
    2. Si el código tiene sufijo, buscar el código base en tabla Code
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
        
        Solo busca en el campo fabricationCode de la tabla Code.
        Si el código tiene sufijo (como -B), también intenta buscar el código base.
        
        Args:
            packaging_code: Código de la orden de empaque (ej: "EA106", "F1041-B")
            db: Sesión de base de datos
            
        Returns:
            Código de fabricación o None si no se encuentra
        """
        if not packaging_code:
            return None
        
        # Paso 1: Buscar directamente en tabla Code (buscar en TODAS las filas)
        # Algunos códigos tienen múltiples filas (una por actividad) y solo algunas tienen fabricationCode
        code_records = db.query(Code).filter(Code.code == packaging_code).all()
        
        for code_record in code_records:
            if code_record.fabricationCode:
                logger.info(
                    f"Found fabricationCode in Code table for '{packaging_code}': "
                    f"{code_record.fabricationCode} (from activity: {code_record.activity})"
                )
                return code_record.fabricationCode
        
        # Paso 2: Si el código tiene sufijo, intentar buscar el código base
        for suffix in cls.VARIANT_SUFFIXES:
            if suffix and packaging_code.endswith(suffix):
                base_code = packaging_code[:-len(suffix)]
                logger.info(f"Trying base code '{base_code}' (without suffix '{suffix}')")
                
                base_record = db.query(Code).filter(Code.code == base_code).first()
                if base_record and base_record.fabricationCode:
                    logger.info(
                        f"Found fabricationCode from base code '{base_code}': "
                        f"{base_record.fabricationCode}"
                    )
                    return base_record.fabricationCode
                break  # Solo intentar un sufijo
        
        # No se encontró código de fabricación
        logger.warning(
            f"No fabricationCode found for '{packaging_code}' in Code table."
        )
        return None
    
