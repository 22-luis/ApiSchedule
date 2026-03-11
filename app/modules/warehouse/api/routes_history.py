from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from app.shared.db.session import get_db
from app.modules.organization.models.role import UserRole
from app.shared.utils.core.dependencies import require_roles
from app.modules.warehouse.models.history import WarehouseHistory, WarehouseHistoryType
from app.modules.warehouse.schemas.history import WarehouseHistoryOut
from app.modules.organization.models.user import User

router = APIRouter(prefix="/warehouse/history", tags=["warehouse"])

@router.get("/", response_model=List[WarehouseHistoryOut])
def get_warehouse_history(
    lote: Optional[int] = Query(None),
    code: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    type: Optional[WarehouseHistoryType] = Query(None),
    date: Optional[str] = Query(None, description="Fecha en formato YYYY-MM-DD"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    query = db.query(WarehouseHistory)
    
    if lote is not None:
        query = query.filter(WarehouseHistory.lote == lote)
    if code:
        query = query.filter(WarehouseHistory.code.ilike(f"%{code}%"))
    if user:
        query = query.filter(WarehouseHistory.user == user)
    if type:
        query = query.filter(WarehouseHistory.type == type)
    if date:
        from datetime import datetime
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            from sqlalchemy import func
            query = query.filter(func.date(WarehouseHistory.timestamp) == target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
        
    return query.order_by(WarehouseHistory.timestamp.desc()).offset(skip).limit(limit).all()

@router.get("/{identifier}", response_model=List[WarehouseHistoryOut])
def get_history_by_identifier(
    identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    query = db.query(WarehouseHistory)
    
    if identifier.isdigit():
        lote_val = int(identifier)
        query = query.filter(WarehouseHistory.lote == lote_val)
    else:
        query = query.filter(WarehouseHistory.code == identifier)
        
    results = query.order_by(WarehouseHistory.timestamp.desc()).all()
    if not results:
        # If no results as code, try partial match if it was a string
        if not identifier.isdigit():
             query_partial = db.query(WarehouseHistory).filter(WarehouseHistory.code.ilike(f"%{identifier}%"))
             results = query_partial.order_by(WarehouseHistory.timestamp.desc()).all()
             
    return results
