import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Annotated
import bcrypt
import jwt
from pydantic import BaseModel, EmailStr, Field
from database import get_db
from models.account import Account

# Create the router
router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts"],
    responses={404: {"description": "Not found"}}
)


# Pydantic models for request/response validation
class AccountCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = EmailStr
    password: str = Field(..., min_length=8)


class AccountLogin(BaseModel):
    email_or_username: str
    password: str


class AccountResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    date_created: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountUpdate(BaseModel):
    username: str = None
    email: EmailStr = None
    password: str = None


# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"


# Helper functions
def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(data: dict):
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# OAuth2 scheme for token authentication
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/accounts/login")


# Routes
@router.post("/register", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def register_account(account: AccountCreate, db: Session = Depends(get_db)):
    try:
        hashed_password = get_password_hash(account.password)
        db_account = Account(
            username=account.username,
            email=account.email,
            password_hash=hashed_password
        )
        db.add(db_account)
        db.commit()
        db.refresh(db_account)
        return db_account
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )


@router.post("/login", response_model=TokenResponse)
def login(login_data: AccountLogin, db: Session = Depends(get_db)):
    # Try to find user by email or username
    account = db.query(Account).filter(
        (Account.email == login_data.email_or_username) |
        (Account.username == login_data.email_or_username)
    ).first()

    if not account or not verify_password(login_data.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token without expiration
    access_token = create_access_token(data={"sub": str(account.id)})

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=AccountResponse)
def get_account_me(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        account_id = int(payload.get("sub"))
        if account_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    account = db.query(Account).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    return account


@router.put("/me", response_model=AccountResponse)
def update_account(
        account_update: AccountUpdate,
        token: Annotated[str, Depends(oauth2_scheme)],
        db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        account_id = int(payload.get("sub"))
        if account_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    account = db.query(Account).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    # Update fields if provided
    if account_update.username is not None:
        account.username = account_update.username
    if account_update.email is not None:
        account.email = account_update.email
    if account_update.password is not None:
        account.password_hash = get_password_hash(account_update.password)

    try:
        db.commit()
        db.refresh(account)
        return account
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )