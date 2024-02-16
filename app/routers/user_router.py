from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from utils.parsers import get_optional_user_id
from db.database import get_db
from sqlalchemy.orm import Session
from db import crud, schemas
from utils.api import openai_client

router = APIRouter()


@router.post("/users", response_model=schemas.SafeUser)
def create_user(
    response: Response,
    user: Optional[schemas.UserCreate] = None,
    user_id: str = Depends(get_optional_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a new user.
    Args:
    - user (Optional[schemas.UserCreate]): The new user's details.
    Headers:
    - auth (Optional[str]): Bearer <USER_ID>
    Returns:
    - Response: A response with the 'auth' header set to 'Bearer {user_id}'
      and the created user in the body.
    """
    if user_id:
        db_user = crud.get_user(db=db, user_id=user_id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        db_user = crud.find_user(db=db, email=user.email)
        if not db_user:
            db_user = crud.create_user(db=db, user=user)

    response.headers["auth"] = f"Bearer {db_user.id}"

    return schemas.SafeUser(
        id=db_user.id,
        email=db_user.email,
        name=db_user.name,
        profile_image=db_user.profile_image,
    )


@router.get("/users", response_model=List[schemas.User])
def get_users(db: Session = Depends(get_db)):
    """
    Get a list of all users.

    Returns:
    - List[schemas.User]: The list of users.
    """
    db_users = crud.get_users(db)
    return db_users


@router.delete("/users", response_model=List[schemas.User])
def delete_all_users(db: Session = Depends(get_db)):
    """
    Delete all users.

    Returns:
    - List[schemas.User]: The deleted users.
    """
    crud.delete_all_threads(db)
    for gpt in openai_client.beta.assistants.list().data:
        openai_client.beta.assistants.delete(gpt.id)
    crud.delete_all_gpts(db)
    db_users = crud.delete_all_users(db)
    return db_users
