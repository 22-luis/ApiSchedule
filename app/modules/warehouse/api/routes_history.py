from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.shared.db.session import get_db
from app.modules.organization.models.role import UserRole
from app.shared.utils.core.dependencies import require_roles
from app.modules.warehouse.models.history import WarehouseHistoryType
from app.modules.warehouse.schemas.history import WarehouseHistoryOut
from app.modules.organization.models.user import User
from app.modules.warehouse.services import history_service

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
    """
    Get warehouse history with optional filters.
    """
    return history_service.get_history(
        db, 
        lote=lote, 
        code=code, 
        user=user, 
        history_type=type, 
        date_str=date, 
        skip=skip, 
        limit=limit
    )

@router.get("/{identifier}", response_model=List[WarehouseHistoryOut])
def get_history_by_identifier(
    identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    """
    Get history entries filtered by lote or code.
    """
    return history_service.get_history_by_identifier(db, identifier)
