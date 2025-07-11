from fastapi import FastAPI
from app.db.session import engine
from app.db.database import Base
from app.models import order
from app.utils.exception_handlers import http_exception_handler, validation_exception_handler, generic_exception_handler

app = FastAPI()

# Registro los handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

Base.metadata.create_all(bind=engine)