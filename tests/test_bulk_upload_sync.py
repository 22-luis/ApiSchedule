import sys
import os
import uuid
import json

# Añadir el directorio raíz al path para importar los módulos de la app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.shared.db.session import SessionLocal
from app.modules.codes.models.code import Code
from app.modules.codes.models.preparation import Preparation
from app.modules.codes.api.routes_code import bulk_upload_codes
from app.modules.codes.api.routes_preparation import bulk_upload_preparations

def test_sync_codes():
    db = SessionLocal()
    try:
        # 1. Limpiar y crear datos iniciales
        db.query(Code).delete()
        c1 = Code(id=uuid.uuid4(), code="T1", activity="ACT1", description="DESC1", type="TYPE")
        c2 = Code(id=uuid.uuid4(), code="T2", activity="ACT1", description="DESC2", type="TYPE")
        db.add_all([c1, c2])
        db.commit()
        
        print(f"Inicializado con 2 códigos: {c1.id}, {c2.id}")
        
        # 2. Simular upload con sincronización
        # c1 se mantiene (actualizado), c2 desaparece (debe ser eliminado), c3 es nuevo
        c3_id = uuid.uuid4()
        upload_data = [
            {"id": str(c1.id), "code": "T1", "activity": "ACT1", "description": "DESC1 UPDATED"},
            {"code": "T3", "activity": "ACT1", "description": "DESC3", "type": "TYPE"}
        ]
        
        result = bulk_upload_codes(upload_data, db)
        print(f"Resultado upload: {result}")
        
        # 3. Verificar resultados
        remaining_codes = db.query(Code).all()
        print(f"Códigos restantes en BD: {[str(c.id) for c in remaining_codes]}")
        
        assert result["updated"] == 1
        assert result["created"] == 1
        assert result["deleted"] == 1
        assert len(remaining_codes) == 2
        
        processed_ids = [c.id for c in remaining_codes]
        assert c1.id in processed_ids
        assert c2.id not in processed_ids
        
        updated_c1 = db.query(Code).filter(Code.id == c1.id).first()
        assert updated_c1.description == "DESC1 UPDATED"
        
        print("✅ Test de sincronización de códigos pasó!")
        
    finally:
        db.close()

def test_sync_preparations():
    db = SessionLocal()
    try:
        # 1. Limpiar y crear datos iniciales
        db.query(Preparation).delete()
        p1 = Preparation(id=uuid.uuid4(), description="PREP1", minutes=10)
        p2 = Preparation(id=uuid.uuid4(), description="PREP2", minutes=20)
        db.add_all([p1, p2])
        db.commit()
        
        print(f"Inicializado con 2 preparaciones: {p1.id}, {p2.id}")
        
        # 2. Simular upload con sincronización
        # p1 se mantiene, p2 desaparece, p3 es nuevo
        upload_data = [
            {"id": str(p1.id), "description": "PREP1", "minutes": 15},
            {"description": "PREP3", "minutes": 30}
        ]
        
        result = bulk_upload_preparations(upload_data, db)
        print(f"Resultado upload: {result}")
        
        # 3. Verificar resultados
        remaining_preps = db.query(Preparation).all()
        print(f"Preparaciones restantes en BD: {[str(p.id) for p in remaining_preps]}")
        
        assert result["updated"] == 1
        assert result["created"] == 1
        assert result["deleted"] == 1
        assert len(remaining_preps) == 2
        
        processed_ids = [p.id for p in remaining_preps]
        assert p1.id in processed_ids
        assert p2.id not in processed_ids
        
        print("✅ Test de sincronización de preparaciones pasó!")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("Iniciando pruebas de verificación...")
    test_sync_codes()
    print("-" * 20)
    test_sync_preparations()
    print("Pruebas completadas.")
