from fastapi.responses import RedirectResponse
from jose import jwt
from datetime import datetime, timedelta
from datetime import timezone
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from fastapi import APIRouter
from utils.parsers import get_user_id
from db import crud, models, schemas
from db.database import get_db
import requests
import os
import dotenv

dotenv.load_dotenv()


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Replace these with your own values from the Google Developer Console
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
JWT_SECRET = os.getenv("JWT_SECRET")
CLIENT_LOGIN_REDIRECT_URI = os.getenv('CLIENT_LOGIN_REDIRECT_URI')


# This is the URL of your domain name plus /login/google


@router.get("/login", response_model=schemas.SafeUser)
def get_users(
    db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """
    Get authenticated user.

    Returns:
    - SafeUser: The authenticated user.
    """
    db_user = crud.get_user(db=db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return schemas.SafeUser(**db_user.__dict__)


@router.get("/login/google")
async def login_google():
    """
    Redirects the user to the Google login page.
    """

    redirect_to = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"  # noqa
    return RedirectResponse(url=redirect_to)


@router.get("/auth/google")
async def auth_google(code: str, db: Session = Depends(get_db)):
    """
        Async function for authenticating with Google using the provided code.
    Parameters:
    - code: str, the authentication code
    - db: Session, the database session
    Returns:
    - dict: containing the access token, token type, and user information
           or containing an error message if an authentication error occurs.
    Raises:
    - requests.exceptions.RequestException: if an error occurs during the
        authentication process.
    """
    try:
        token_url = "https://accounts.google.com/o/oauth2/token"
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        access_token = response.json().get("access_token")
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_info.raise_for_status()
        user_info = user_info.json()
        user_info["profile_image"] = user_info["picture"]

        print("user_info", user_info)

        user = get_or_create_user(db, schemas.UserCreate(**user_info))
        access_token = generate_access_token(user)

        redirect_to = f"{CLIENT_LOGIN_REDIRECT_URI}?token={access_token}"
        return RedirectResponse(
            url=redirect_to, headers={"auth": f"Bearer {access_token}"}
        )
    except requests.exceptions.RequestException:
        return {
            "error": "An error occurred during the authentication process."
        }


def get_or_create_user(
    db: Session, user_info: schemas.UserCreate
) -> models.User:
    """
    Function to get or create a user in the database.
    Parameters:
    - db: Session, the database session
    - user_info: dict, the user information
    Returns:
    - models.User: the user object
    """
    print("user_info", user_info)
    db_user = crud.find_user(db=db, email=user_info.email)
    if not db_user:
        db_user = crud.create_user(db=db, user=user_info)

    return db_user


def generate_access_token(user: models.User) -> str:
    """
    Function to generate an access token for the user.
    Parameters:
    - user: models.User, the user object
    Returns:
    - str: the access token
    """

    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    return create_access_token(
        data={"id": user.id}, expires_delta=access_token_expires
    )


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Function to create an access token for the user.
    Parameters:
    - data: dict, the data to be encoded in the token
    - expires_delta: timedelta, the expiration time of the token
    Returns:
    - str: the access token
    """

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
