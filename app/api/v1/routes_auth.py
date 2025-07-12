from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.utils.dependencies import get_current_user
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.models.user import User
from app.utils.jwt import create_access_token
from app.utils.security import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    # Puedes incluir más datos en el token si lo deseas
    access_token = create_access_token(data={"sub": str(user.id), "username": user.username, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(current_user=Depends(get_current_user)):
    return 