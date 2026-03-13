from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.organization.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return AuthService.login(db, form_data.username, form_data.password)

@router.post("/logout")
def logout(_current_user=Depends(get_current_user)):
    return {"message": "Logout successful"}