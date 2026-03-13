import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles, get_current_user
from app.modules.organization.models.user import User
from app.modules.organization.models.role import UserRole
from app.modules.available.schemas.available import AvailableCreate, Available, AvailableUpdate
from app.modules.available.service.available import (
    create_available,
    create_available_bulk,
    get_available,
    get_available_list,
    update_available,
    delete_available,
    delete_all_available,
)

router = APIRouter(prefix="/available", tags=["available"])


@router.post("/", response_model=List[Available])
def create_available_item(item: AvailableCreate | List[AvailableCreate], db: Session = Depends(get_db), _current_user: User = Depends(require_roles(UserRole.ADMIN))):
    # Accept either a single item or a list of items. Always return a list of created items.
    if isinstance(item, list):
        created = create_available_bulk(db, item)
        return created
    db_item = create_available(db, item)
    return [db_item]


@router.get("/", response_model=List[Available])
def list_available_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    items = get_available_list(db, skip, limit)
    return items


@router.get("/{item_id}", response_model=Available)
def get_available_item(item_id: uuid.UUID, db: Session = Depends(get_db), _current_user: User = Depends(get_current_user)):
    item = get_available(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Available item not found")
    return item


@router.patch("/{item_id}", response_model=Available)
def patch_available_item(item_id: uuid.UUID, item_update: AvailableUpdate, db: Session = Depends(get_db), _current_user: User = Depends(require_roles(UserRole.ADMIN))):
    updated = update_available(db, item_id, item_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Available item not found")
    return updated


@router.delete("/{item_id}")
def delete_available_item(item_id: uuid.UUID, db: Session = Depends(get_db), _current_user: User = Depends(require_roles(UserRole.ADMIN))):
    ok = delete_available(db, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Available item not found")
    return {"message": "Available item deleted successfully"}


@router.delete("/")
def delete_all_available_items(db: Session = Depends(get_db), _current_user: User = Depends(require_roles(UserRole.ADMIN))):
    """Delete all Available records. Requires ADMIN role."""
    deleted = delete_all_available(db)
    return {"message": f"{deleted} Available items deleted successfully"}
