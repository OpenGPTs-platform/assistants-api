from fastapi import HTTPException
from jose import jwt
import os
from db import crud
from sqlalchemy.orm import Session


def get_token(token: str):
    """
    Function to get the token.
    Parameters:
    - token: str, the token
    Returns:
    - str: the token
    """

    return jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])


def validate_user_gpt(db: Session, user_id: str, assistant_id: str):
    user_gpt = crud.get_user_gpt(db=db, user_id=user_id, gpt_id=assistant_id)

    if not user_gpt:
        raise HTTPException(
            status_code=404,
            detail="User does not have access to this GPT instance or assistant does not exist.",  # noqa
        )
