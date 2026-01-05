#!/usr/bin/env python3
"""
Script para probar directamente la base de datos sin autenticación.
"""
from app.shared.db.session import SessionLocal
from app.modules.programming.models.order import Order
from app.modules.core.models.state import OrderStatus

def test_manufactured_status_direct():
    """Prueba directamente en la base de datos"""
    db = SessionLocal()
    
    try:
        print("🔍 Probando conexión a la base de datos...")
        
        # Obtener la primera orden
        order = db.query(Order).first()
        
        if not order:
            print("❌ No hay órdenes en la base de datos")
            return False
        
        print(f"📋 Orden encontrada: {order.lote} (estado actual: {order.status})")
        
        # Guardar estado original
        original_status = order.status
        
        # Intentar cambiar a manufactured
        print("🔄 Intentando cambiar estado a 'manufactured'...")
        order.status = OrderStatus.manufactured
        db.commit()
        
        # Verificar el cambio
        db.refresh(order)
        print(f"✅ Estado actualizado a: {order.status}")
        
        # Restaurar estado original
        print(f"🔄 Restaurando estado original: {original_status}")
        order.status = original_status
        db.commit()
        
        print("✅ Prueba completada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    """Ejecuta la prueba"""
    print("🧪 PRUEBA DIRECTA DE BASE DE DATOS")
    print("=" * 40)
    
    success = test_manufactured_status_direct()
    
    print("\n" + "=" * 40)
    if success:
        print("🎯 ✅ El estado 'manufactured' funciona correctamente")
    else:
        print("🎯 ❌ Hay problemas con el estado 'manufactured'")

if __name__ == "__main__":
    main()