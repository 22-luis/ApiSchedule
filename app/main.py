from fastapi import FastAPI
from app.db.session import engine
from app.db.database import Base
from app.models import order


app = FastAPI()

Base.metadata.create_all(bind=engine)