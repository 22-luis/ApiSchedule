#!/usr/bin/env python3
"""
Script para insertar datos de prueba en la base de datos.
Incluye el código F136-B que está causando el error 404.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.models.code import Code
from app.models.team import Team
from app.models.user import User
from app.models.role import UserRole
import uuid

def init_test_data():
    db = SessionLocal()
    try:
        # Crear algunos códigos de prueba
        test_codes = [
            {
                "code": "F136-B",
                "description": "ANTIMOHO/PROPIONATO CALCIO 1K*",
                "unit": "KG",
                "type": "M2",
                "activity": "EMPAQUE MANUAL GRUPO",
                "quantity": "1",
                "time": 60.0,
                "people": 2,
                "performance": 0.035,
                "material": "BOLSA KG TRASP/BOLSA CORRIENTE 3 LB/ ETIQUETA ROJA S/IMPRESION /BOLSA PAPEL GRANDE S/IM",
                "presentation": "25 X 1 KG EXPORTACION",
                "fabricationCode": "FAB001",
                "usefulLife": "Ver Materia Prima",
                "related_code_team": "TEAM001"
            },
            {
                "code": "F136-B",
                "description": "ANTIMOHO/PROPIONATO CALCIO 1K*",
                "unit": "KG",
                "type": "M2",
                "activity": "EMPAQUE AUTOMATICO",
                "quantity": "1",
                "time": 45.0,
                "people": 1,
                "performance": 0.050,
                "material": "BOLSA KG TRASP/BOLSA CORRIENTE 3 LB/ ETIQUETA ROJA S/IMPRESION",
                "presentation": "25 X 1 KG EXPORTACION",
                "fabricationCode": "FAB001",
                "usefulLife": "Ver Materia Prima",
                "related_code_team": "TEAM002"
            },
            {
                "code": "F137-A",
                "description": "PRODUCTO DE PRUEBA 2",
                "unit": "UN",
                "type": "M1",
                "activity": "PRODUCCION MANUAL",
                "quantity": "5",
                "time": 30.0,
                "people": 3,
                "performance": 0.025,
                "material": "MATERIAL DE PRUEBA",
                "presentation": "10 X 500G",
                "fabricationCode": "FAB002",
                "usefulLife": "6 meses",
                "related_code_team": "TEAM001"
            }
        ]
        
        # Verificar si los códigos ya existen
        for code_data in test_codes:
            existing_code = db.query(Code).filter(
                Code.code == code_data["code"],
                Code.activity == code_data["activity"]
            ).first()
            
            if not existing_code:
                new_code = Code(**code_data)
                db.add(new_code)
                print(f"Código {code_data['code']} - {code_data['activity']} agregado")
            else:
                print(f"Código {code_data['code']} - {code_data['activity']} ya existe")
        
        db.commit()
        print("Datos de prueba insertados correctamente")
        
    except Exception as e:
        print(f"Error insertando datos de prueba: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_test_data() 