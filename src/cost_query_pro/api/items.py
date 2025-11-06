"""src/cost_query_pro/api/items.py"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from cost_query_pro.api.auth import get_current_user
from cost_query_pro.db.session import get_db
from cost_query_pro.models import Item, Project
from cost_query_pro.models.user import User as DBUser
from cost_query_pro.schemas.item import ItemCreate, ItemOut, ItemUpdate, ItemWithProject

router = APIRouter(prefix="/items", tags=["items"])


class PriceRangeOut(BaseModel):
    min_price: Optional[Decimal]
    max_price: Optional[Decimal]


@router.get("/search", response_model=List[ItemWithProject])
def search_items(
    q: Optional[str] = Query(None, description="Search term for item description"),
    state: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    unit: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Search for items with various filters:
    - Item description keyword
    - State
    - Year range
    - Unit type
    - Price range
    """
    query = db.query(Item).options(joinedload(Item.project))

    if q:
        query = query.filter(Item.item_description.ilike(f"%{q}%"))
    if state:
        query = query.join(Item.project).filter(Project.state == state)
    if year_start:
        query = query.join(Item.project).filter(Project.year >= year_start)
    if year_end:
        query = query.join(Item.project).filter(Project.year <= year_end)
    if unit:
        query = query.filter(Item.unit == unit)
    if min_price is not None:
        query = query.filter(Item.unit_price >= min_price)
    if max_price is not None:
        query = query.filter(Item.unit_price <= max_price)

    return query.offset(skip).limit(limit).all()


@router.get("/{item_id}", response_model=ItemWithProject)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retrieve a specific item by ID with its project details.
    """
    item = (
        db.query(Item)
        .options(joinedload(Item.project))
        .filter(Item.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found.",
        )
    return item


@router.post("/", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new item.
    """
    project = db.query(Project).filter(Project.id == item.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {item.project_id} not found.",
        )

    db_item = Item(
        project_id=item.project_id,
        item_description=item.item_description,
        unit=item.unit,
        unit_price=item.unit_price,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{item_id}", response_model=ItemOut)
def update_item(
    item_id: int,
    item: ItemUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update an existing item.
    """
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found.",
        )

    if item.project_id is not None and item.project_id != db_item.project_id:
        project = db.query(Project).filter(Project.id == item.project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {item.project_id} not found.",
            )

    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete an item.
    """
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found.",
        )

    db.delete(db_item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/units/distinct", response_model=List[str])
def get_distinct_units(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get all distinct unit types in the DB.
    """
    result = db.query(Item.unit).distinct().all()
    return [unit[0] for unit in result]


@router.get("/stats/price-range", response_model=PriceRangeOut)
def get_price_range(
    item_query: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get min and max price for items matching the query.
    """
    query = db.query(Item)
    if item_query:
        query = query.filter(Item.item_description.ilike(f"%{item_query}%"))

    min_price_item = query.order_by(Item.unit_price.asc()).first()
    max_price_item = query.order_by(Item.unit_price.desc()).first()

    return PriceRangeOut(
        min_price=min_price_item.unit_price if min_price_item else None,
        max_price=max_price_item.unit_price if max_price_item else None,
    )


@router.get("/search")
def search_items(current_user: DBUser = Depends(get_current_user)):
    """
    Placeholder route to demonstrate authentication.

        - Requires a valid JWT token.
        - Returns a simple success message with current user info.
    """
    return {"message": f"Authenticated as {current_user.username}"}
