from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.modules.codes.models.catalog_test import CatalogTest
from app.modules.codes.schemas import catalog_test
from app.modules.codes.schemas.catalog_test import CatalogTestBase, CatalogTestOut
from app.modules.core.models.role import UserRole
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles

router = APIRouter(prefix="/catalog-tests", tags=["catalog-tests"])

def get_catalog_test_or_404(db: Session, test_id: int) -> type[CatalogTest]:
    db_test = db.query(CatalogTest).filter(CatalogTest.id == test_id).first()
    if not db_test:
        raise HTTPException(status_code=404, detail="Catalog test not found")
    return db_test

@router.post("/",
             response_model=catalog_test,
             status_code=201,
             dependencies =[Depends(require_roles(UserRole.ADMIN,UserRole.QC_ENGINEER))])
def create(
        test_data: CatalogTestBase,
        db: Session = Depends(get_db),
):
    try:
        new_test = CatalogTest(
            test=test_data.test,
            type=test_data.type
        )
        db.add(new_test)
        db.commit()
        db.refresh(new_test)
        return new_test
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=list[CatalogTestOut])
def get_all(db: Session = Depends(get_db)):
    return db.query(CatalogTest).all()


@router.patch("/{test_id}", response_model=CatalogTestOut)
def update_catalog_test(test_id: int, test_data: CatalogTestBase, db: Session = Depends(get_db)):
    db_test = get_catalog_test_or_404(db, test_id)

    for key, value in test_data.model_dump().items():
        setattr(db_test, key, value)

    db.commit()
    db.refresh(db_test)
    return db_test

@router.delete("/{test_id}", status_code=204)
def delete_catalog_test(test_id: int, db: Session = Depends(get_db)):
    db_test = get_catalog_test_or_404(db, test_id)
    db.delete(db_test)
    db.commit()
    return None