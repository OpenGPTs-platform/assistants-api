from typing import List
from sqlalchemy.orm import Session

from . import models, schemas
import uuid


# THREAD
def delete_all_threads(db: Session) -> List[models.User_gpt_thread]:
    user_gpt_threads = db.query(models.User_gpt_thread).all()
    for thread in user_gpt_threads:
        db.delete(thread)
    db.commit()
    # return the deleted threads
    return user_gpt_threads


def create_thread(
    db: Session, user_gpt_thread: schemas.UserGptThread
) -> models.User_gpt_thread:
    db_user_gpt_thread = models.User_gpt_thread(
        user_id=user_gpt_thread.user_id,
        gpt_id=user_gpt_thread.gpt_id,
        thread_id=user_gpt_thread.thread_id,
    )
    db.add(db_user_gpt_thread)
    db.commit()
    db.refresh(db_user_gpt_thread)
    return db_user_gpt_thread


def get_user_threads(
    db: Session, user_id: str
) -> List[models.User_gpt_thread]:
    user_gpt_threads = (
        db.query(models.User_gpt_thread)
        .filter(models.User_gpt_thread.user_id == user_id)
        .all()
    )
    return user_gpt_threads


def get_user_gpt_thread(
    db: Session, user_id: str, gpt_id: str, thread_id: str
) -> models.User_gpt_thread:
    user_gpt_thread = (
        db.query(models.User_gpt_thread)
        .filter(models.User_gpt_thread.user_id == user_id)
        .filter(models.User_gpt_thread.gpt_id == gpt_id)
        .filter(models.User_gpt_thread.thread_id == thread_id)
        .first()
    )
    return user_gpt_thread


# def create_thread_message(
#     db: Session, thread_message: schemas.ThreadMessageCreate
# ) -> models.ThreadMessage:
#     pass


# USER
def delete_all_gpts(db: Session) -> List[models.User_gpt]:
    user_gpts = db.query(models.User_gpt).all()
    for gpt in user_gpts:
        db.delete(gpt)
    db.commit()
    # return the deleted gpts
    return user_gpts


def get_user(db: Session, user_id: str):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user


def find_user(db: Session, email: str):
    user = db.query(models.User).filter(models.User.email == email).first()
    return user


def get_users(db: Session):
    all_users = db.query(models.User).all()
    return all_users


def delete_all_users(db: Session) -> List[models.User]:
    users = db.query(models.User).all()
    for user in users:
        db.delete(user)
    db.commit()
    # return the deleted users
    return users


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        id=str(uuid.uuid4()),
        email=user.email,
        name=user.name,
        profile_image=user.profile_image,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# GPT
def create_user_gpt(db: Session, user_gpt: schemas.UserGpt):
    db_user_gpt = models.User_gpt(
        user_id=user_gpt.user_id, gpt_id=user_gpt.gpt_id
    )
    db.add(db_user_gpt)
    db.commit()
    db.refresh(db_user_gpt)
    return db_user_gpt


def delete_all_gpts_and_threads(db: Session) -> List[models.User_gpt]:
    user_gpts = db.query(models.User_gpt).all()
    for user_gpt in user_gpts:
        db.delete(user_gpt)
    user_gpt_thread = db.query(models.User_gpt_thread).all()
    for thread in user_gpt_thread:
        db.delete(thread)
    db.commit()
    # return the deleted gpts
    return user_gpts


def get_user_gpts(db: Session, user_id: str) -> list[models.User_gpt]:
    user_gpts = (
        db.query(models.User_gpt)
        .filter(models.User_gpt.user_id == user_id)
        .all()
    )
    return user_gpts


def get_user_gpt(db: Session, user_id: str, gpt_id: str) -> models.User_gpt:
    all_user_gpts = (
        db.query(models.User_gpt)
        .filter(models.User_gpt.user_id == user_id)
        .all()
    )
    print("all_user_gpts", [str(user_gpt) for user_gpt in all_user_gpts])
    user_gpt = (
        db.query(models.User_gpt)
        .filter(models.User_gpt.user_id == user_id)
        .filter(models.User_gpt.gpt_id == gpt_id)
        .first()
    )
    return user_gpt
