"""
Script de prueba para verificar la búsqueda de código de fabricación.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from dotenv import load_dotenv
load_dotenv()

from app.shared.db.session import SessionLocal
from app.shared.utils.business.fabrication_code_finder import FabricationCodeFinder
from app.modules.codes.models.code import Code

def test_fabrication_code_lookup():
    """Prueba la búsqueda de código de fabricación para A1012"""
    
    db = SessionLocal()
    try:
        print("="*60)
        print("PRUEBA DE BÚSQUEDA DE CÓDIGO DE FABRICACIÓN")
        print("="*60)
        
        test_code = "A1012"
        print(f"\n📦 Código de empaque de prueba: {test_code}")
        
        # Paso 1: Verificar si existe en tabla Code
        print(f"\n1️⃣ Buscando '{test_code}' en tabla Code...")
        code_record = db.query(Code).filter(Code.code == test_code).first()
        
        if code_record:
            print(f"   ✓ Encontrado en tabla Code")
            print(f"   - ID: {code_record.id}")
            print(f"   - Code: {code_record.code}")
            print(f"   - Description: {code_record.description}")
            print(f"   - FabricationCode: {code_record.fabricationCode or '(vacío)'}")
            print(f"   - Activity: {code_record.activity}")
            print(f"   - Type: {code_record.type}")
        else:
            print(f"   ✗ NO encontrado en tabla Code")
        
        # Paso 2: Buscar código de fabricación usando el servicio
        print(f"\n2️⃣ Ejecutando FabricationCodeFinder.find_fabrication_code()...")
        fabrication_code = FabricationCodeFinder.find_fabrication_code(test_code, db)
        
        if fabrication_code:
            print(f"   ✓ Código de fabricación encontrado: {fabrication_code}")
            
            # Verificar si ese código existe en la tabla
            fab_code_record = db.query(Code).filter(Code.code == fabrication_code).first()
            if fab_code_record:
                print(f"   ✓ Código de fabricación existe en tabla Code")
                print(f"   - Description: {fab_code_record.description}")
                print(f"   - Activity: {fab_code_record.activity}")
                print(f"   - Type: {fab_code_record.type}")
        else:
            print(f"   ✗ NO se encontró código de fabricación")
        
        # Paso 3: Mostrar candidatos generados
        print(f"\n3️⃣ Candidatos generados:")
        candidates = FabricationCodeFinder._generate_candidate_codes(test_code)
        for i, candidate in enumerate(candidates[:10], 1):  # Mostrar solo primeros 10
            exists = db.query(Code).filter(Code.code == candidate).first()
            status = "✓ EXISTE" if exists else "✗ no existe"
            print(f"   {i}. {candidate:20s} {status}")
        
        # Paso 4: Buscar orden manufactured
        print(f"\n4️⃣ Buscando orden manufactured con cantidad 500...")
        fab_order_info = FabricationCodeFinder.find_manufactured_order(
            packaging_code=test_code,
            packaging_quantity=500,
            db=db
        )
        
        if fab_order_info:
            print(f"   ✓ Orden manufactured encontrada:")
            print(f"   - Lote: {fab_order_info['lote']}")
            print(f"   - Code: {fab_order_info['code']}")
            print(f"   - Quantity: {fab_order_info['quantity']}")
            print(f"   - Status: {fab_order_info['status']}")
        else:
            print(f"   ✗ NO se encontró orden manufactured")
        
        print("\n" + "="*60)
        print("RESUMEN")
        print("="*60)
        print(f"Código de empaque:    {test_code}")
        print(f"Código de fabricación: {fabrication_code or 'NO ENCONTRADO'}")
        print(f"Orden manufactured:    {'SÍ' if fab_order_info else 'NO'}")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_fabrication_code_lookup()
