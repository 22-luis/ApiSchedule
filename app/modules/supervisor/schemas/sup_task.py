from pydantic import BaseModel


class SupTask(BaseModel):
    name: str
    description: str

