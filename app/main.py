from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware

from app.db.session import engine
from app.db.database import Base
from app.utils.exception_handlers import http_exception_handler, validation_exception_handler, generic_exception_handler
from app.api.v1.routes_auth import router as auth_router
from app.api.v1.routes_user import router as user_router
from app.api.v1.routes_team import router as team_router
from app.api.v1.routes_order import router as order_router
from app.api.v1.routes_task import router as task_router, nested_router as task_nested_router
from app.api.v1.routes_preparation import router as preparation_router
from app.models import user, team, task, order, preparation, programming

app = FastAPI()

# Configuracion CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhst:9002"], #Permite todos los origenes
    allow_credentials=True,
    allow_methods=["*"], #Permite todos los metodos
    allow_headers=["*"], #Permite todos los headers
)

# Registro los handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Registro los routers
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(user_router, tags=["users"])
api_router.include_router(team_router, tags=["teams"])
api_router.include_router(order_router, tags=["orders"])
api_router.include_router(task_router, tags=["tasks"])
api_router.include_router(task_nested_router, tags=["tasks"])
api_router.include_router(preparation_router, tags=["preparations"])

# Incluir el router principal en la app
app.include_router(api_router)

Base.metadata.create_all(bind=engine)