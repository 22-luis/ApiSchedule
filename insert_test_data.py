#!/usr/bin/env python3
"""
Script simple para insertar datos de prueba
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.code import Code
from app.core.config import settings

def insert_test_data():
    # Crear engine y sesión
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Crear código de prueba F136-B
        test_code = Code(
            code="F136-B",
            description="ANTIMOHO/PROPIONATO CALCIO 1K*",
            unit="KG",
            type="M2",
            activity="EMPAQUE MANUAL GRUPO",
            quantity="1",
            time=60.0,
            people=2,
            performance=0.035,
            material="BOLSA KG TRASP/BOLSA CORRIENTE 3 LB/ ETIQUETA ROJA S/IMPRESION /BOLSA PAPEL GRANDE S/IM",
            presentation="25 X 1 KG EXPORTACION",
            fabricationCode="FAB001",
            usefulLife="Ver Materia Prima",
            related_code_team="TEAM001"
        )
        
        # Verificar si ya existe
        existing = db.query(Code).filter(
            Code.code == "F136-B",
            Code.activity == "EMPAQUE MANUAL GRUPO"
        ).first()
        
        if not existing:
            db.add(test_code)
            db.commit()
            print("Código F136-B insertado correctamente")
        else:
            print("Código F136-B ya existe")
        
        # Crear segundo código F136-B con diferente actividad
        test_code2 = Code(
            code="F136-B",
            description="ANTIMOHO/PROPIONATO CALCIO 1K*",
            unit="KG",
            type="M2",
            activity="EMPAQUE AUTOMATICO",
            quantity="1",
            time=45.0,
            people=1,
            performance=0.050,
            material="BOLSA KG TRASP/BOLSA CORRIENTE 3 LB/ ETIQUETA ROJA S/IMPRESION",
            presentation="25 X 1 KG EXPORTACION",
            fabricationCode="FAB001",
            usefulLife="Ver Materia Prima",
            related_code_team="TEAM002"
        )
        
        existing2 = db.query(Code).filter(
            Code.code == "F136-B",
            Code.activity == "EMPAQUE AUTOMATICO"
        ).first()
        
        if not existing2:
            db.add(test_code2)
            db.commit()
            print("Código F136-B (EMPAQUE AUTOMATICO) insertado correctamente")
        else:
            print("Código F136-B (EMPAQUE AUTOMATICO) ya existe")
        
        # Verificar que se insertaron correctamente
        codes = db.query(Code).filter(Code.code == "F136-B").all()
        print(f"Total códigos F136-B en la base de datos: {len(codes)}")
        for code in codes:
            print(f"  - {code.code}: {code.activity}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    insert_test_data() 