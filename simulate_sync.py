
import sys
import os
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append(os.getcwd())

from app.shared.core.config import settings
from app.modules.orders.models.order import Order
from app.shared.utils.business.order_status_service import OrderStatusService

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    orders = db.query(Order).all()
    print(f"Syncing {len(orders)} orders...")
    for order in orders:
        OrderStatusService.sync_order_status_for_lote(db, str(order.lote))
    
    total_orders = db.query(Order).count()
    status_counts = db.execute(text("SELECT status, count(*) FROM public.\"order\" GROUP BY status")).fetchall()
    
    print(f"Total orders: {total_orders}")
    print("Counts by status after sync:")
    for status, count in status_counts:
        print(f"  - {status}: {count}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
