from datetime import datetime, date, time, timedelta
import sys
import os

# Añadir el path de la aplicación para poder importar BusinessCalculations
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.shared.utils.business.business_calculations import BusinessCalculations

def test_lunch_adjustment():
    print("--- Probando ajuste de almuerzo ---")
    
    # Caso 1: Antes del almuerzo (8:00 AM, 60 min)
    start1 = datetime.combine(date.today(), time(8, 0))
    end1 = start1 + timedelta(minutes=60)
    adj1 = BusinessCalculations.apply_lunch_break_adjustment(start1, end1)
    print(f"8:00 + 60m = {adj1.time()} (Esperado: 09:00:00)")
    assert adj1.time() == time(9, 0)
    
    # Caso 2: Cruzando almuerzo (11:30 AM, 60 min)
    start2 = datetime.combine(date.today(), time(11, 30))
    end2 = start2 + timedelta(minutes=60)
    adj2 = BusinessCalculations.apply_lunch_break_adjustment(start2, end2)
    print(f"11:30 + 60m = {adj2.time()} (Esperado: 13:30:00)")
    assert adj2.time() == time(13, 30)
    
    # Caso 3: Empezando en almuerzo (12:30 PM, 30 min)
    start3 = datetime.combine(date.today(), time(12, 30))
    end3 = start3 + timedelta(minutes=30)
    adj3 = BusinessCalculations.apply_lunch_break_adjustment(start3, end3)
    print(f"12:30 + 30m = {adj3.time()} (Esperado: 13:30:00)")
    assert adj3.time() == time(13, 30)
    
    # Caso 4: Después del almuerzo (1:30 PM, 30 min)
    start4 = datetime.combine(date.today(), time(13, 30))
    end4 = start4 + timedelta(minutes=30)
    adj4 = BusinessCalculations.apply_lunch_break_adjustment(start4, end4)
    print(f"13:30 + 30m = {adj4.time()} (Esperado: 14:00:00)")
    assert adj4.time() == time(14, 0)

def test_sequential_times():
    print("\n--- Probando tiempos secuenciales ---")
    tasks = [
        {'id': '1', 'description': 'T1', 'minutes': 30}, # 8:00 - 8:30
        {'id': '2', 'description': 'T2', 'minutes': 120}, # 8:30 - 10:30
        {'id': '3', 'description': 'T3', 'minutes': 120}, # 10:30 - 12:30 -> 13:30
        {'id': '4', 'description': 'T4', 'minutes': 30}, # 13:30 - 14:00
    ]
    
    res = BusinessCalculations.calculate_sequential_times(date.today(), tasks, base_time="08:00")
    
    for r in res:
        print(f"{r['description']}: {r['start_time']} -> {r['end_time']}")
    
    # T3 debería terminar a las 13:30
    t3_end = datetime.fromisoformat(res[2]['end_time']).time()
    print(f"T3 fin: {t3_end} (Esperado: 13:30:00)")
    assert t3_end == time(13, 30)
    
    # T4 debería empezar a las 13:30
    t4_start = datetime.fromisoformat(res[3]['start_time']).time()
    print(f"T4 inicio: {t4_start} (Esperado: 13:30:00)")
    assert t4_start == time(13, 30)

if __name__ == "__main__":
    try:
        test_lunch_adjustment()
        test_sequential_times()
        print("\n✅ Todas las pruebas pasaron correctamente.")
    except Exception as e:
        print(f"\n❌ Prueba fallida: {e}")
        import traceback
        traceback.print_exc()
