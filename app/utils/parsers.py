from fastapi import HTTPException, Header
from typing import Optional
from utils.auth import get_token


def get_user_id(auth: str = Header(None)):
    try:
        user_id = None
        scheme, _, param = auth.partition(' ')
        decoded = get_token(param)
        user_id = decoded["id"]
        if not user_id:
            raise Exception
        return user_id
    except Exception:
        raise HTTPException(
            status_code=400, detail='Invalid authorization header'
        )


def get_optional_user_id(auth: Optional[str] = Header(None)):
    try:
        return get_user_id(auth)
    except HTTPException:
        return None
