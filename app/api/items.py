"""app/api/items.py"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional

from app.db.session import get_db
from app.models.item import Item
from app.models.project import Project
from app.schemas.item import ItemCreate, ItemOut, ItemUpdate, ItemWithProject

router = APIRouter()

@router.get("/search", response_model=List[ItemWithProject])
def search_items(
    q: str = Query(None, description="Search term for item description"),
    state: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    unit: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Search for items with various filters:
    - Item description keyword
    - State
    - Year range
    - Unit type
    - Price range
    """
    query = db.query(Item).join(Item.project)

    # Apply filters
    if q:
        query = query.filter(Item.item_description.ilike(f"%{q}%"))

    if state:
        query = query.filter(Project.state == state)

    if year_start:
        query = query.filter(Project.year >= year_start)

    if year_end:
        query = query.filter(Project.year <= year_end)

    if unit:
        query = query.filter(Item.unit == unit)

    if min_price is not None:
        query = query.filter(Item.unit_price >= min_price)

    if max_price is not None:
        query = query.filter(Item.unit_price <= max_price)

    # Return results with pagination
    return query.offset(skip).limit(limit).all()

@router.get("/{item_id}", response_model=ItemWithProject)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific item by ID with its project details.
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    return item

@router.post("/", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """
    Create a new item.
    """
    # Verify the project exists
    project = db.query(Project).filter(Project.id == item.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {item.project_id} not found"
        )

    db_item = Item(
        project_id=item.project_id,
        item_description=item.item_description,
        unit=item.unit,
        unit_price=item.unit_price
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, item: ItemUpdate, db: Session = Depends(get_db)):
    """
    Update an existing item.
    """
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )

    # If project_id is being updated, verify the new project exists
    if item.project_id is not None and item.project_id != db_item.project_id:
        project = db.query(Project).filter(Project.id == item.project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {item.project_id} not found"
            )

    # Update item attributes
    for key, value in item.dict(exclude_unset=True).items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """
    Delete an item.
    """
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )

    db.delete(db_item)
    db.commit()
    return None

@router.get("/units/distinct", response_model=List[str])
def get_distinct_units(db: Session = Depends(get_db)):
    """
    Get a list of all distinct unit types in the database.
    Useful for populating dropdown filters in the UI.
    """
    result = db.query(Item.unit).distinct().all()
    return [unit[0] for unit in result]

@router.get("/stats/price-range", response_model=dict)
def get_price_range(item_query: str = None, db: Session = Depends(get_db)):
    """
    Get the min and max price for items matching the query.
    Useful for setting price range filters in the UI.
    """
    query = db.query(Item)

    if item_query:
        query = query.filter(Item.item_description.ilike(f"%{item_query}%"))

    min_price = query.order_by(Item.unit_price.asc()).first()
    max_price = query.order_by(Item.unit_price.desc()).first()

    return {
        "min_price": min_price.unit_price if min_price else 0,
        "max_price": max_price.unit_price if max_price else 0
    }
