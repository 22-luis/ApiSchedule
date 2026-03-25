import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles, get_current_user
from app.modules.organization.models.user import User
from app.modules.organization.models.role import UserRole
from app.modules.available.schemas.available import AvailableCreate, Available, AvailableUpdate
from app.modules.available.repositories.available_repository import AvailableRepository
from app.modules.available.services.available import AvailableService

router = APIRouter(prefix="/available", tags=["available"])

def get_available_service(db: Session = Depends(get_db)) -> AvailableService:
    return AvailableService(AvailableRepository(db))

@router.post("/", response_model=List[Available])
def create_available_item(
    item: AvailableCreate | List[AvailableCreate], 
    db: Session = Depends(get_db), 
    available_service: AvailableService = Depends(get_available_service),
    _current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    # Accept either a single item or a list of items. Always return a list of created items.
    if isinstance(item, list):
        return available_service.create_bulk(item)
    db_item = available_service.create(item)
    return [db_item]

@router.get("/", response_model=List[Available])
def list_available_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    available_service: AvailableService = Depends(get_available_service),
    _current_user: User = Depends(get_current_user),
):
    return available_service.get_list(skip, limit)

@router.get("/{item_id}", response_model=Available)
def get_available_item(
    item_id: uuid.UUID, 
    available_service: AvailableService = Depends(get_available_service),
    _current_user: User = Depends(get_current_user)
):
    item = available_service.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Available item not found")
    return item

@router.patch("/{item_id}", response_model=Available)
def patch_available_item(
    item_id: uuid.UUID, 
    item_update: AvailableUpdate, 
    available_service: AvailableService = Depends(get_available_service),
    _current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    updated = available_service.update(item_id, item_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Available item not found")
    return updated

@router.delete("/{item_id}")
def delete_available_item(
    item_id: uuid.UUID, 
    available_service: AvailableService = Depends(get_available_service),
    _current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    ok = available_service.delete(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Available item not found")
    return {"message": "Available item deleted successfully"}

@router.delete("/")
def delete_all_available_items(
    available_service: AvailableService = Depends(get_available_service),
    _current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """Delete all Available records. Requires ADMIN role."""
    deleted = available_service.delete_all()
    return {"message": f"{deleted} Available items deleted successfully"}
