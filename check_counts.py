
import sys
import os
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append(os.getcwd())

from app.shared.core.config import settings
from app.modules.orders.models.order import Order

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    total_orders = db.query(Order).count()
    status_counts = db.execute(text("SELECT status, count(*) FROM public.\"order\" GROUP BY status")).fetchall()
    
    print(f"Total orders in table 'order' (according to settings.SQLALCHEMY_DATABASE_URI): {total_orders}")
    print(f"DATABASE_URI used: {settings.SQLALCHEMY_DATABASE_URI}")
    print("Counts by status:")
    for status, count in status_counts:
        print(f"  - {status}: {count}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
