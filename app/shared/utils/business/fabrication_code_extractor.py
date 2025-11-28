"""
Utilidad para extraer el código de fabricación desde un código de empaque.

El código de empaque sigue el patrón: [CodigoBase][-Sufijo][M#][CodigoFabricacion]

Ejemplo: A1012-VM2AX1012
- Código Base: A1012
- Sufijo: -V
- Clave de Relación: M2
- Código de Fabricación: AX1012
"""

import re
from typing import Optional, Dict
from app.shared.utils.core.logging import get_logger

logger = get_logger("fabrication_code_extractor")


class FabricationCodeExtractor:
    """
    Extrae el código de fabricación desde un código de empaque siguiendo las reglas de limpieza.
    """
    
    # Sufijos conocidos de variante
    VARIANT_SUFFIXES = [
        '-V',    # Variación/Versión
        '-L',    # Long/Largo
        '-F',    # Formato/Tipo
        '-8',    # Número de variante
        '-5',    # Número de variante
        '-B',    # Variación/Base
        '-C',    # Variación/Custom
        '-A',    # Variación/Alterna
        '-DOC',  # Documentación
        '-1',    # Número de variante
        '-2',    # Número de variante
        '-3',    # Número de variante
        '-4',    # Número de variante
        '-6',    # Número de variante
        '-7',    # Número de variante
        '-9',    # Número de variante
    ]
    
    # Patrón para detectar la clave de relación (M seguido de uno o más dígitos)
    # Ejemplos: M1, M2, M3, M4, M5, M7, M9, M10, M11, M12, M13, M15
    RELATION_KEY_PATTERN = re.compile(r'M\d+')
    
    @classmethod
    def extract_fabrication_code(cls, packaging_code: str) -> Optional[str]:
        """
        Extrae el código de fabricación desde un código de empaque.
        
        Args:
            packaging_code: Código de empaque completo (ej: A1012-VM2AX1012)
            
        Returns:
            Código de fabricación extraído o None si no se puede extraer
            
        Examples:
            >>> FabricationCodeExtractor.extract_fabrication_code("A1012-VM2AX1012")
            "AX1012"
            >>> FabricationCodeExtractor.extract_fabrication_code("E1061-LM2EX1061")
            "EX1061"
            >>> FabricationCodeExtractor.extract_fabrication_code("BX101-1DOCM2BX101")
            "BX101"
        """
        if not packaging_code or not isinstance(packaging_code, str):
            logger.warning(f"Invalid packaging code: {packaging_code}")
            return None
            
        # Limpiar espacios en blanco
        code = packaging_code.strip()
        
        # Buscar la clave de relación (M#)
        match = cls.RELATION_KEY_PATTERN.search(code)
        
        if not match:
            logger.info(f"No relation key pattern (M#) found in code: {code}")
            return None
        
        # La posición donde inicia la clave de relación
        relation_start = match.start()
        # La posición donde termina la clave de relación
        relation_end = match.end()
        
        # El código de fabricación es todo lo que viene después de la clave de relación
        fabrication_code = code[relation_end:].strip()
        
        if not fabrication_code:
            logger.warning(f"No fabrication code found after relation key in: {code}")
            return None
        
        logger.info(f"Extracted fabrication code: '{fabrication_code}' from '{packaging_code}'")
        return fabrication_code
    
    @classmethod
    def extract_with_details(cls, packaging_code: str) -> Dict[str, Optional[str]]:
        """
        Extrae el código de fabricación y proporciona detalles del análisis.
        
        Args:
            packaging_code: Código de empaque completo
            
        Returns:
            Diccionario con detalles de la extracción:
            - original_code: Código original
            - base_code: Código base (antes de M#)
            - relation_key: Clave de relación encontrada (M2, M4, etc.)
            - fabrication_code: Código de fabricación extraído
            - success: Si la extracción fue exitosa
        """
        result = {
            "original_code": packaging_code,
            "base_code": None,
            "relation_key": None,
            "fabrication_code": None,
            "success": False
        }
        
        if not packaging_code or not isinstance(packaging_code, str):
            return result
        
        code = packaging_code.strip()
        result["original_code"] = code
        
        # Buscar la clave de relación
        match = cls.RELATION_KEY_PATTERN.search(code)
        
        if not match:
            return result
        
        # Extraer componentes
        relation_start = match.start()
        relation_end = match.end()
        
        result["base_code"] = code[:relation_start].strip()
        result["relation_key"] = match.group()
        result["fabrication_code"] = code[relation_end:].strip()
        result["success"] = bool(result["fabrication_code"])
        
        return result
    
    @classmethod
    def validate_extraction(cls, packaging_code: str, expected_fabrication_code: str) -> bool:
        """
        Valida que la extracción del código de fabricación sea correcta.
        
        Args:
            packaging_code: Código de empaque
            expected_fabrication_code: Código de fabricación esperado
            
        Returns:
            True si la extracción coincide con lo esperado
        """
        extracted = cls.extract_fabrication_code(packaging_code)
        return extracted == expected_fabrication_code
