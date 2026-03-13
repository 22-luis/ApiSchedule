from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.modules.warehouse.models.history import WarehouseHistory, WarehouseHistoryType

def find_all(
    db: Session,
    lote: Optional[int] = None,
    code: Optional[str] = None,
    user: Optional[str] = None,
    history_type: Optional[WarehouseHistoryType] = None,
    target_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100
) -> List[WarehouseHistory]:
    """
    Search warehouse history with multiple filters.
    """
    query = db.query(WarehouseHistory)
    
    if lote is not None:
        query = query.filter(WarehouseHistory.lote == lote)
    if code:
        query = query.filter(WarehouseHistory.code.ilike(f"%{code}%"))
    if user:
        query = query.filter(WarehouseHistory.user == user)
    if history_type:
        query = query.filter(WarehouseHistory.type == history_type)
    if target_date:
        query = query.filter(func.date(WarehouseHistory.timestamp) == target_date)
        
    return query.order_by(WarehouseHistory.timestamp.desc()).offset(skip).limit(limit).all()

def find_by_identifier(
    db: Session,
    identifier: str
) -> List[WarehouseHistory]:
    """
    Search history by lote (if identifier is numeric) or code (exact or partial match).
    """
    query = db.query(WarehouseHistory)
    
    if identifier.isdigit():
        lote_val = int(identifier)
        query = query.filter(WarehouseHistory.lote == lote_val)
        return query.order_by(WarehouseHistory.timestamp.desc()).all()
    else:
        # Try exact match first for code
        exact_results = query.filter(WarehouseHistory.code == identifier).order_by(WarehouseHistory.timestamp.desc()).all()
        if exact_results:
            return exact_results
            
def save(db: Session, history: WarehouseHistory) -> WarehouseHistory:
    """Guarda un registro de historial."""
    db.add(history)
    db.commit()
    db.refresh(history)
    return history
