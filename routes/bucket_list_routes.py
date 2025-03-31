from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Annotated, List, Optional
import uuid
from pydantic import BaseModel, Field
from datetime import datetime

from database import get_db
from models.bucket_list import BucketList, BucketListCollaborator
from routes.account_routes import oauth2_scheme, SECRET_KEY, ALGORITHM
import jwt

# Create the router
router = APIRouter(
    prefix="/api/bucket-lists",
    tags=["bucket-lists"],
    responses={404: {"description": "Not found"}}
)


# Pydantic models for request/response validation
class BucketItemResponse(BaseModel):
    id: int
    bucket_list_id: int
    content: str
    is_completed: bool
    last_modified_by: int
    date_last_modified: Optional[datetime] = None

    class Config:
        from_attributes = True


class BucketListCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class BucketListUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_private: Optional[bool] = None


class BucketListResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    created_by: int
    date_created: datetime
    is_private: bool
    share_token: Optional[str] = None
    items: List[BucketItemResponse] = []

    class Config:
        from_attributes = True


# Helper Functions
def get_current_user_id(token: str) -> int:
    """Get the user ID from the JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


def generate_share_token():
    """Generate a unique token for sharing bucket lists."""
    return uuid.uuid4().hex


def verify_bucket_list_access(bucket_list_id: int, user_id: int, db: Session):
    """Verify that the user either owns or collaborates on the bucket list."""
    # First check if user is the owner
    bucket_list = db.query(BucketList).filter(
        BucketList.id == bucket_list_id,
        BucketList.created_by == user_id
    ).first()

    if bucket_list:
        return bucket_list, True  # Return bucket list and is_owner=True

    # If not the owner, check if user is a collaborator
    collaborator = db.query(BucketListCollaborator).filter(
        BucketListCollaborator.bucket_list_id == bucket_list_id,
        BucketListCollaborator.collaborator_id == user_id
    ).first()

    # If user is a collaborator, get the bucket list
    if collaborator:
        bucket_list = db.query(BucketList).filter(
            BucketList.id == bucket_list_id
        ).first()

        if bucket_list:
            return bucket_list, False  # Return bucket list and is_owner=False

    # If neither owner nor collaborator
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Bucket list not found or you don't have access"
    )


# Routes
@router.post("", response_model=BucketListResponse, status_code=status.HTTP_201_CREATED)
def create_bucket_list(
        bucket_list: BucketListCreate,
        token: Annotated[str, Depends(oauth2_scheme)],
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    db_bucket_list = BucketList(
        title=bucket_list.title,
        description=bucket_list.description,
        created_by=user_id,
    )

    db.add(db_bucket_list)
    db.commit()
    db.refresh(db_bucket_list)

    return db_bucket_list


@router.get("", response_model=List[BucketListResponse])
def get_bucket_lists(
        token: Annotated[str, Depends(oauth2_scheme)],
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    # Get bucket lists created by the user
    owned_bucket_lists = db.query(BucketList).filter(
        BucketList.created_by == user_id
    ).all()

    all_bucket_lists = owned_bucket_lists

    # Apply pagination (simple approach)
    paginated_lists = all_bucket_lists[skip:skip + limit]

    return paginated_lists

@router.get("/collaborated", response_model=List[BucketListResponse])
def get_collaborated_bucket_lists(
        token: Annotated[str, Depends(oauth2_scheme)],
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    # Get bucket lists the user collaborates on
    collaborated_lists = db.query(BucketList).join(
        BucketListCollaborator,
        BucketListCollaborator.bucket_list_id == BucketList.id
    ).filter(
        BucketListCollaborator.collaborator_id == user_id
    ).all()

    # Apply pagination (simple approach)
    paginated_lists = collaborated_lists[skip:skip + limit]

    return paginated_lists


@router.get("/{bucket_list_id}", response_model=BucketListResponse)
def get_bucket_list(
        token: Annotated[str, Depends(oauth2_scheme)],
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    # Verify access (returns bucket list or raises exception)
    bucket_list, _ = verify_bucket_list_access(bucket_list_id, user_id, db)

    return bucket_list


@router.put("/{bucket_list_id}", response_model=BucketListResponse)
def update_bucket_list(
        token: Annotated[str, Depends(oauth2_scheme)],
        bucket_list_update: BucketListUpdate,
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    # Verify access (returns bucket list or raises exception)
    bucket_list, is_owner = verify_bucket_list_access(bucket_list_id, user_id, db)

    # Only allow is_private updates for owners
    if bucket_list_update.is_private is not None and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can change privacy settings"
        )

    # Update fields if provided
    if bucket_list_update.title is not None:
        bucket_list.title = bucket_list_update.title
    if bucket_list_update.description is not None:
        bucket_list.description = bucket_list_update.description
    if bucket_list_update.is_private is not None and is_owner:
        bucket_list.is_private = bucket_list_update.is_private

    db.commit()
    db.refresh(bucket_list)

    return bucket_list


@router.delete("/{bucket_list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bucket_list(
        token: Annotated[str, Depends(oauth2_scheme)],
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    # Only the creator can delete a bucket list
    bucket_list = db.query(BucketList).filter(
        BucketList.id == bucket_list_id,
        BucketList.created_by == user_id
    ).first()

    if bucket_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bucket list not found or you are not the owner"
        )

    db.delete(bucket_list)
    db.commit()

    return None


@router.post("/{bucket_list_id}/share", response_model=BucketListResponse)
def share_bucket_list(
        token: Annotated[str, Depends(oauth2_scheme)],
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    # Only the creator can share a bucket list
    bucket_list = db.query(BucketList).filter(
        BucketList.id == bucket_list_id,
        BucketList.created_by == user_id
    ).first()

    if bucket_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bucket list not found or you are not the owner"
        )

    # Generate a share token if one doesn't exist
    if not bucket_list.share_token:
        bucket_list.share_token = generate_share_token()
        bucket_list.is_private = False
        db.commit()
        db.refresh(bucket_list)

    return bucket_list


@router.post("/{bucket_list_id}/unshare", response_model=BucketListResponse)
def unshare_bucket_list(
        token: Annotated[str, Depends(oauth2_scheme)],
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    # Only the creator can unshare a bucket list
    bucket_list = db.query(BucketList).filter(
        BucketList.id == bucket_list_id,
        BucketList.created_by == user_id
    ).first()

    if bucket_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bucket list not found or you are not the owner"
        )

    # Remove share token and make private
    bucket_list.share_token = None
    bucket_list.is_private = True
    db.commit()
    db.refresh(bucket_list)

    return bucket_list


@router.get("/shared/{share_token}", response_model=BucketListResponse)
def get_shared_bucket_list(
        token: Annotated[str, Depends(oauth2_scheme)],
        share_token: str = Path(...),
        db: Session = Depends(get_db)
):
    # Check if the user is authenticated
    user_id = get_current_user_id(token)

    # First get the shared bucket list
    bucket_list = db.query(BucketList).filter(
        BucketList.share_token == share_token,
        BucketList.is_private == False
    ).first()

    if bucket_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared bucket list not found or no longer available"
        )

    # Add or update the user as a collaborator
    try:
        # Check if the user is already a collaborator
        collaborator = db.query(BucketListCollaborator).filter(
            BucketListCollaborator.bucket_list_id == bucket_list.id,
            BucketListCollaborator.collaborator_id == user_id
        ).first()

        if collaborator is None:
            # Add as a new collaborator
            db_collaborator = BucketListCollaborator(
                bucket_list_id=bucket_list.id,
                collaborator_id=user_id,
                is_owner=False,
                access_date=func.now()  # Set current timestamp
            )
            db.add(db_collaborator)
        else:
            # Update access date for existing collaborator
            collaborator.access_date = func.now()

        db.commit()

    except Exception as e:
        # Log the error but don't fail the request
        print(f"Error adding collaborator: {str(e)}")
        db.rollback()
        # Continue to return the bucket list even if adding collaborator fails

    return bucket_list


@router.get("/{bucket_list_id}/collaborators", response_model=List[dict])
def get_bucket_list_collaborators(
        token: Annotated[str, Depends(oauth2_scheme)],
        bucket_list_id: int = Path(...),
        db: Session = Depends(get_db)
):
    user_id = get_current_user_id(token)

    # Verify access
    bucket_list, _ = verify_bucket_list_access(bucket_list_id, user_id, db)

    # Get collaborators
    collaborators = db.query(BucketListCollaborator).filter(
        BucketListCollaborator.bucket_list_id == bucket_list_id
    ).all()

    # Transform to response format
    result = []
    for collab in collaborators:
        result.append({
            "collaborator_id": collab.collaborator_id,
            "is_owner": collab.is_owner,
            "access_date": collab.access_date
        })

    return result