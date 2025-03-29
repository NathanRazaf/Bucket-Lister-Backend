from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import random
from uuid import uuid4

from database import get_db
from models.bucket_list import BucketList
from routes import account_routes

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


# Include the account router
app.include_router(account_routes.router)

@app.post("/bucket-list/test")
async def create_test_bucket_list(title: str, db: Session = Depends(get_db)):
    try:
        # Generate a random share token
        share_token = str(uuid4().hex)

        # Create a test bucket list with the given title and random parameters
        new_bucket_list = BucketList(
            title=title,
            description=f"This is a test bucket list for {title}",
            created_by=random.randint(1, 1000),  # Random user ID
            is_private=random.choice([True, False]),
            share_token=share_token
        )

        # Add to database and commit
        db.add(new_bucket_list)
        db.commit()
        db.refresh(new_bucket_list)

        return {
            "message": "Test bucket list created successfully",
            "bucket_list": {
                "id": new_bucket_list.id,
                "title": new_bucket_list.title,
                "description": new_bucket_list.description,
                "created_by": new_bucket_list.created_by,
                "date_created": new_bucket_list.date_created,
                "is_private": new_bucket_list.is_private,
                "share_token": new_bucket_list.share_token
            }
        }
    except Exception as e:
        # If something goes wrong, rollback the transaction
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating bucket list: {str(e)}")