"""
Tests para el extractor de código defabricación.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from app.shared.utils.business.fabrication_code_extractor import FabricationCodeExtractor


class TestFabricationCodeExtractor:
    """Tests para la extracción de códigos de fabricación desde códigos de empaque."""
    
    def test_extract_basic_pattern(self):
        """Prueba extracción básica con patrón estándar."""
        assert FabricationCodeExtractor.extract_fabrication_code("A1012M2AX1012") == "AX1012"
        assert FabricationCodeExtractor.extract_fabrication_code("E1061M2EX1061") == "EX1061"
    
    def test_extract_with_variant_suffix_v(self):
        """Prueba extracción con sufijo -V."""
        assert FabricationCodeExtractor.extract_fabrication_code("A1012-VM2AX1012") == "AX1012"
    
    def test_extract_with_variant_suffix_l(self):
        """Prueba extracción con sufijo -L."""
        assert FabricationCodeExtractor.extract_fabrication_code("E1061-LM2EX1061") == "EX1061"
    
    def test_extract_with_variant_suffix_f(self):
        """Prueba extracción con sufijo -F."""
        assert FabricationCodeExtractor.extract_fabrication_code("E1061-FM2EX1061") == "EX1061"
    
    def test_extract_with_numeric_variant_8(self):
        """Prueba extracción con sufijo -8."""
        assert FabricationCodeExtractor.extract_fabrication_code("ER1011-8M2ERX1011") == "ERX1011"
    
    def test_extract_with_numeric_variant_5(self):
        """Prueba extracción con sufijo -5."""
        assert FabricationCodeExtractor.extract_fabrication_code("F1041-5M2FX1041") == "FX1041"
    
    def test_extract_with_variant_suffix_b(self):
        """Prueba extracción con sufijo -B."""
        assert FabricationCodeExtractor.extract_fabrication_code("F1041-BM2FX1041") == "FX1041"
    
    def test_extract_with_variant_suffix_c(self):
        """Prueba extracción con sufijo -C."""
        assert FabricationCodeExtractor.extract_fabrication_code("E1068-CM4EX1068") == "EX1068"
    
    def test_extract_with_variant_suffix_a(self):
        """Prueba extracción con sufijo -A."""
        # Nota: según tabla, E1068-AM4EX1068-A mantiene parte del sufijo
        result = FabricationCodeExtractor.extract_fabrication_code("E1068-AM4EX1068-A")
        assert result == "EX1068-A"
    
    def test_extract_with_doc_suffix(self):
        """Prueba extracción con sufijo -DOC."""
        assert FabricationCodeExtractor.extract_fabrication_code("BX101-1DOCM2BX101") == "BX101"
    
    def test_extract_different_relation_keys(self):
        """Prueba extracción con diferentes claves de relación."""
        assert FabricationCodeExtractor.extract_fabrication_code("A1012M2AX1012") == "AX1012"
        assert FabricationCodeExtractor.extract_fabrication_code("B2034M4BX2034") == "BX2034"
        assert FabricationCodeExtractor.extract_fabrication_code("C3045M5CX3045") == "CX3045"
        assert FabricationCodeExtractor.extract_fabrication_code("D4056M7DX4056") == "DX4056"
        assert FabricationCodeExtractor.extract_fabrication_code("E5067M12EX5067") == "EX5067"
        assert FabricationCodeExtractor.extract_fabrication_code("F6078M13FX6078") == "FX6078"
    
    def test_extract_with_details(self):
        """Prueba extracción con detalles completos."""
        result = FabricationCodeExtractor.extract_with_details("A1012-VM2AX1012")
        
        assert result["original_code"] == "A1012-VM2AX1012"
        assert result["base_code"] == "A1012-V"
        assert result["relation_key"] == "M2"
        assert result["fabrication_code"] == "AX1012"
        assert result["success"] is True
    
    def test_extract_no_relation_key(self):
        """Prueba con código sin clave de relación."""
        assert FabricationCodeExtractor.extract_fabrication_code("SIMPLECODEWITHOUTM") is None
    
    def test_extract_empty_string(self):
        """Prueba con string vacío."""
        assert FabricationCodeExtractor.extract_fabrication_code("") is None
    
    def test_extract_none(self):
        """Prueba con None."""
        assert FabricationCodeExtractor.extract_fabrication_code(None) is None
    
    def test_extract_with_whitespace(self):
        """Prueba con espacios en blanco."""
        assert FabricationCodeExtractor.extract_fabrication_code("  A1012M2AX1012  ") == "AX1012"
    
    def test_validate_extraction(self):
        """Prueba validación de extracción."""
        assert FabricationCodeExtractor.validate_extraction("A1012M2AX1012", "AX1012") is True
        assert FabricationCodeExtractor.validate_extraction("A1012M2AX1012", "WRONG") is False
