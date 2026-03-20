from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.available.models.availableModel import Available
from app.modules.available.schemas.available import AvailableCreate, AvailableUpdate
from app.modules.available.repositories.available_repository import AvailableRepository


class AvailableService:
    def __init__(self, available_repo: AvailableRepository):
        self.available_repo = available_repo

    def create(self, available_data: AvailableCreate) -> Available:
        return self.available_repo.create(available_data)

    def create_bulk(self, items: List[AvailableCreate]) -> List[Available]:
        return self.available_repo.create_bulk(items)

    def get_by_id(self, available_id) -> Optional[Available]:
        return self.available_repo.get_by_id(available_id)

    def get_list(self, skip: int = 0, limit: int = 100) -> List[Available]:
        return self.available_repo.get_list(skip, limit)

    def update(self, available_id, available_update: AvailableUpdate) -> Optional[Available]:
        return self.available_repo.update(available_id, available_update)

    def delete(self, available_id) -> bool:
        return self.available_repo.delete(available_id)

    def delete_all(self) -> int:
        return self.available_repo.delete_all()