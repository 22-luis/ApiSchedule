import sys
import os
from sqlalchemy import create_engine, text

# Add the current directory to sys.path to ensure app module is found
sys.path.append(os.getcwd())

try:
    # Corrected import path
    from app.shared.core.config import settings
    DATABASE_URL = str(settings.SQLALCHEMY_DATABASE_URI)
    print(f"Loaded configuration. Database host: {settings.POSTGRES_SERVER}")
except Exception as e:
    print(f"Error importing settings: {e}")
    sys.exit(1)

# Create engine
try:
    engine = create_engine(DATABASE_URL)
    print(f"Connected to database.") 
except Exception as e:
    print(f"Error connecting to database: {e}")
    sys.exit(1)

def check_order_bins(lotes):
    try:
        with engine.connect() as connection:
            # Check if orders exist and get their details
            query = text("SELECT lote, bin, code, status, quantity FROM \"order\" WHERE lote IN :lotes")
            result = connection.execute(query, {"lotes": tuple(lotes)})
            
            print(f"\n--- Checking Orders: {lotes} ---")
            found_lotes = []
            for row in result:
                found_lotes.append(row.lote)
                print(f"Lote: {row.lote}")
                print(f"  Bin: {row.bin} (Type: {type(row.bin)})")
                print(f"  Code: {row.code}")
                print(f"  Status: {row.status}")
                print(f"  Quantity: {row.quantity}")
                
                # Check programmability logic
                is_programmable = row.bin in [8, 10, 100]
                print(f"  Is Programmable (bin in [8, 10, 100]): {is_programmable}")
                print("-" * 30)
            
            missing_lotes = set(lotes) - set(found_lotes)
            if missing_lotes:
                print(f"\nOrders not found: {missing_lotes}")
                
    except Exception as e:
        print(f"Error executing query: {e}")

if __name__ == "__main__":
    # Lotes from the user's screenshot/summary
    lotes_to_check = [88535, 88536, 88236, 88336]
    check_order_bins(lotes_to_check)
