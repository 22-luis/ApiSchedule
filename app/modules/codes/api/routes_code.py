import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.codes.schemas.code import CodeCreate, CodeOut, CodePageOut, CodeUpdate, CodeDetailsOut
from app.modules.codes.services import code_service
from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles

logger = logging.getLogger(__name__)

# Importar sistema de caché
try:
    from app.shared.utils.cache import cache_response, invalidate_cache

    CACHE_AVAILABLE = True
except ImportError:
    logger.info("Módulo de caché no encontrado. El caché estará deshabilitado.")
    CACHE_AVAILABLE = False

    def cache_response(*_args, **_kwargs):
        def decorator(fn):
            return fn
        return decorator

    def invalidate_cache(*_args, **_kwargs):
        def decorator(fn):
            return fn
        return decorator

router = APIRouter(prefix="/codes", tags=["codes"])


# --- Endpoints CRUD ---

@router.post("/", response_model=CodeOut)
@invalidate_cache(pattern="codes")
def create_code(
    code: CodeCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return code_service.create_code(db, code)


@router.get("/", response_model=CodePageOut)
@cache_response(ttl=300, key_fields=["skip", "limit", "search"])
def get_codes(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Cuántos registros omitir"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de registros a devolver"),
    search: str = Query(None, description="Buscar por código o descripción"),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER)
    ),
):
    return code_service.get_codes(db, skip=skip, limit=limit, search=search)


@router.get("/production", response_model=CodePageOut)
@cache_response(ttl=300, key_fields=["skip", "limit", "search"])
def get_production_codes(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Cuántos registros omitir"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de registros a devolver"),
    search: str = Query(None, description="Buscar por código o descripción"),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT)
    ),
):
    return code_service.get_production_codes(db, skip=skip, limit=limit, search=search)


@router.get("/{code_id}", response_model=CodeOut)
@cache_response(ttl=600, key_fields=["code_id"])
def get_code(
    code_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER)
    ),
):
    return code_service.get_code_by_id(db, code_id)


@router.patch("/{code_id}", response_model=CodeOut)
@invalidate_cache(pattern="codes")
def update_code(
    code_id: uuid.UUID,
    code_update: CodeUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return code_service.update_code(db, code_id, code_update)


@router.delete("/{code_id}")
@invalidate_cache(pattern="codes")
def delete_code(
    code_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return code_service.delete_code(db, code_id)


# --- Endpoints de Búsqueda y Específicos ---

@router.get("/by_code_and_activity", response_model=CodeOut)
@cache_response(ttl=600, key_fields=["code", "activity"])
def get_code_by_code_and_activity(
    code: str,
    activity: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER)
    ),
):
    return code_service.get_code_by_code_and_activity(db, code, activity)


@router.get("/by_code_and_activity_details", response_model=CodeDetailsOut)
@cache_response(ttl=600, key_fields=["code", "activity"])
def get_activity_details_by_code_and_activity(
    code: str,
    activity: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER)
    ),
):
    return code_service.get_activity_details(db, code, activity)


@router.get("/by_code/{code}/activity")
@cache_response(ttl=600, key_fields=["code"])
def get_code_activity(
    code: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER)
    ),
):
    return code_service.get_code_activities(db, code)


@router.get("/by_code/{code}/lotes")
@cache_response(ttl=300, key_fields=["code"])
def get_lotes_by_code(
    code: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER)
    ),
):
    return code_service.get_lotes_by_code(db, code)


@router.get("/by_code/{code}/services")
@cache_response(ttl=600, key_fields=["code"])
def get_services_for_code(
    code: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PLANNER)
    ),
):
    return code_service.get_services_for_code(db, code)


# --- Endpoint de Carga Masiva ---

@router.post("/bulk_upload")
@invalidate_cache(pattern="codes")
def bulk_upload_codes(
    codes: List[dict],
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(UserRole.ADMIN)),
):
    return code_service.bulk_upload_codes(db, codes)
