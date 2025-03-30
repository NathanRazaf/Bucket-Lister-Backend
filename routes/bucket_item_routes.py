from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import Annotated, List
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models.bucket_list import BucketList, BucketItem
from routes.bucket_list_routes import get_current_user_id, BucketItemResponse
from routes.account_routes import oauth2_scheme

# Create the router
router = APIRouter(
    prefix="/api/bucket-lists/{bucket_list_id}/items",
    tags=["bucket-items"],
    responses={404: {"description": "Not found"}}
)

class BucketItemCreate(BaseModel):
    content: str


class BucketItemUpdate(BaseModel):
    content: str = None
    is_completed: bool = None


# Helper Functions
def verify_bucket_list_ownership(bucket_list_id: int, user_id: int, db: Session):
    """Verify that the user owns the bucket list."""
    bucket_list = db.query(BucketList).filter(
        BucketList.id == bucket_list_id,
        BucketList.created_by == user_id
    ).first()

    if bucket_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bucket list not found or you don't have access"
        )

    return bucket_list


def return_item(user_id, item_id, bucket_list_id, db):
    # Verify ownership
    verify_bucket_list_ownership(bucket_list_id, user_id, db)

    # Get item
    item = db.query(BucketItem).filter(
        BucketItem.id == item_id,
        BucketItem.bucket_list_id == bucket_list_id
    ).first()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bucket item not found"
        )

    return item

# Routes
@router.post("", response_model=BucketItemResponse, status_code=status.HTTP_201_CREATED)
def create_bucket_item(
        token: Annotated[str, Depends(oauth2_scheme)],
        bucket_item: BucketItemCreate,
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    # Verify ownership
    verify_bucket_list_ownership(bucket_list_id, user_id, db)

    # Create bucket item
    db_bucket_item = BucketItem(
        bucket_list_id=bucket_list_id,
        content=bucket_item.content,
        last_modified_by=user_id
    )

    db.add(db_bucket_item)
    db.commit()
    db.refresh(db_bucket_item)

    return db_bucket_item


@router.get("", response_model=List[BucketItemResponse])
def get_bucket_items(
        token: Annotated[str, Depends(oauth2_scheme)],
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    # Verify ownership
    verify_bucket_list_ownership(bucket_list_id, user_id, db)

    # Get items
    items = db.query(BucketItem).filter(
        BucketItem.bucket_list_id == bucket_list_id
    ).all()

    return items


@router.put("/{item_id}", response_model=BucketItemResponse)
def update_bucket_item(
        token: Annotated[str, Depends(oauth2_scheme)],
        bucket_item_update: BucketItemUpdate,
        item_id: int = Path(...),
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    item = return_item(user_id, item_id, bucket_list_id, db)

    # Update fields if provided
    if bucket_item_update.content is not None:
        item.content = bucket_item_update.content
    if bucket_item_update.is_completed is not None:
        item.is_completed = bucket_item_update.is_completed

    # Update last_modified fields
    item.last_modified_by = user_id
    item.date_last_modified = datetime.now()

    db.commit()
    db.refresh(item)

    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bucket_item(
        token: Annotated[str, Depends(oauth2_scheme)],
        item_id: int = Path(...),
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    item = return_item(user_id, item_id, bucket_list_id, db)

    db.delete(item)
    db.commit()

    return None


@router.put("/{item_id}/toggle", response_model=BucketItemResponse)
def toggle_bucket_item_completion(
        token: Annotated[str, Depends(oauth2_scheme)],
        item_id: int = Path(...),
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    item = return_item(user_id, item_id, bucket_list_id, db)

    # Toggle completion status
    item.is_completed = not item.is_completed

    # Update last_modified fields
    item.last_modified_by = user_id
    item.date_last_modified = datetime.now()

    db.commit()
    db.refresh(item)

    return item


