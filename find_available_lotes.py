#!/usr/bin/env python3
"""
Script para encontrar lotes disponibles para pruebas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import get_db
from app.models.order import Order

def find_available_lotes():
    """Encuentra lotes disponibles para pruebas"""
    db = next(get_db())
    
    print("🔍 BUSCANDO LOTES DISPONIBLES PARA PRUEBAS")
    print("=" * 50)
    
    # Obtener todos los lotes existentes
    existing_orders = db.query(Order).all()
    existing_lotes = {order.lote for order in existing_orders}
    
    print(f"📊 Total de órdenes existentes: {len(existing_orders)}")
    print(f"📊 Lotes únicos existentes: {len(existing_lotes)}")
    
    # Encontrar lotes disponibles
    print("\n🔍 LOTES DISPONIBLES:")
    print("-" * 30)
    
    available_lotes = []
    for i in range(100000, 100010):  # Probar lotes del 100000 al 100009
        if i not in existing_lotes:
            available_lotes.append(i)
            print(f"   ✅ Lote {i} disponible")
        else:
            print(f"   ❌ Lote {i} ya existe")
    
    # También probar algunos lotes más altos
    print("\n🔍 LOTES ALTOS DISPONIBLES:")
    print("-" * 35)
    
    for i in range(200000, 200010):  # Probar lotes del 200000 al 200009
        if i not in existing_lotes:
            available_lotes.append(i)
            print(f"   ✅ Lote {i} disponible")
        else:
            print(f"   ❌ Lote {i} ya existe")
    
    print(f"\n📋 LOTES RECOMENDADOS PARA PRUEBAS:")
    print("-" * 40)
    if available_lotes:
        for lote in available_lotes[:5]:  # Mostrar solo los primeros 5
            print(f"   🎯 Lote {lote}")
    else:
        print("   ❌ No se encontraron lotes disponibles")
    
    db.close()
    return available_lotes

if __name__ == "__main__":
    find_available_lotes()
