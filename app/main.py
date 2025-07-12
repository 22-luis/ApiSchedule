from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware

from app.db.session import engine
from app.db.database import Base
from app.models import order
from app.utils.exception_handlers import http_exception_handler, validation_exception_handler, generic_exception_handler
from app.api.v1.routes_auth import router as auth_router
from app.api.v1.routes_user import router as user_router
from app.api.v1.routes_team import router as team_router
from app.api.v1.routes_order import router as order_router
from app.api.v1.routes_task import router as task_router

app = FastAPI()

# Configuracion CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #Permite todos los origenes
    allow_credentials=True,
    allow_methods=["*"], #Permite todos los metodos
    allow_headers=["*"], #Permite todos los headers
)

# Registro los handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Registro los routers
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(user_router, prefix="/api/v1", tags=["users"])
app.include_router(team_router, prefix="/api/v1", tags=["teams"])
app.include_router(order_router, prefix="/api/v1", tags=["orders"])
app.include_router(task_router, prefix="/api/v1", tags=["tasks"])

Base.metadata.create_all(bind=engine)