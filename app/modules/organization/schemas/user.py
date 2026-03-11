import base64
import binascii
import re
import uuid
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.modules.organization.models.role import UserRole
from app.modules.organization.models.state import UserState


class UserBase(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    cargo: Optional[str] = None
    role: Optional[UserRole] = None
    state: Optional[UserState] = None
    teamIds: Optional[List[uuid.UUID]] = None
    document_name: Optional[str] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if v is None:
            return v
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('El nombre de usuario solo puede contener letras, números y guiones bajos')
        if v.lower() in ['admin', 'root', 'system', 'test', 'guest']:
            raise ValueError('Nombre de usuario no permitido')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if v is None:
            return v
        if len(v) < 6:
            raise ValueError('La contraseña debe tener al menos 6 caracteres')
        common_passwords = [
            'password', '123456', 'qwerty', 'admin', 'letmein',
            'welcome', 'monkey', 'password123', 'admin123'
        ]
        if v.lower() in common_passwords:
            raise ValueError('La contraseña es demasiado común')
        return v

    @field_validator('teamIds')
    @classmethod
    def validate_team_ids(cls, v):
        if v is not None:
            unique_ids = list(set(v))
            if len(unique_ids) != len(v):
                raise ValueError('No se permiten IDs de equipo duplicados')
        return v

class UserCreate(UserBase):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = Field(default=UserRole.USER)
    state: UserState = Field(default=UserState.ACTIVE)
    teamIds: Optional[List[uuid.UUID]] = Field(default=[])

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "password": "mypassword123",
                "role": "USER",
                "state": "ACTIVE",
                "teamIds": [],
                "document_name": None
            }
        }
    )

class UserOut(BaseModel):
    id: uuid.UUID = Field(..., description="ID único del usuario")
    username: str = Field(..., description="Nombre de usuario")
    full_name: Optional[str] = Field(None, description="Nombre completo")
    cargo: Optional[str] = Field(None, description="Cargo o puesto")
    role: UserRole = Field(..., description="Rol del usuario")
    state: UserState = Field(default=UserState.ACTIVE, description="Estado del usuario")
    teamIds: Optional[List[uuid.UUID]] = Field(default=[], description="IDs de equipos")
    signature: Optional[str] = Field(None, description="Firma del usuario")
    document_name: Optional[str] = Field(None, description="Nombre del documento firmado")

    @field_validator('signature', mode='before')
    @classmethod
    def validate_signature(cls, v):
        if v is None:
            return None
        if isinstance(v, (bytes, bytearray, memoryview)):
            try:
                return base64.b64encode(bytes(v)).decode('utf-8')
            except (binascii.Error, ValueError):
                raise ValueError('La firma debe ser una cadena base64 valida')
        return v

    model_config = ConfigDict(
        from_attributes = True,
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john_doe",
                "role": "USER",
                "state": "ACTIVE",
                "teamIds": [],
                "signature": None,
                "document_name": None
            }
        }
    )

class UserUpdate(UserBase):
    signature: Optional[Union[str, bytes]] = Field(None, description="Firma del usuario")

    @field_validator('signature', mode='before')
    @classmethod
    def validate_signature(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip():
            try:
                return base64.b64decode(v)
            except Exception:
                raise ValueError('La firma debe ser una cadena base64 válida')
        if isinstance(v, (bytes, bytearray, memoryview)):
            return bytes(v)
        return v

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "password": "mypassword123",
                "role": "USER",
                "state": "ACTIVE",
                "teamIds": [],
                "signature": None
            }
        }
    )

class UserStateUpdate(BaseModel):
    state: UserState

class User(BaseModel):
    id: uuid.UUID = Field(..., description="ID único del usuario")
    username: str = Field(..., description="Nombre de usuario")
    role: UserRole = Field(..., description="Rol del usuario")
    state: UserState = Field(default=UserState.ACTIVE, description="Estado del usuario")

    model_config = ConfigDict(
        from_attributes = True
    )

class UsersPageOut(BaseModel):
    users: List[UserOut]
    total: int
