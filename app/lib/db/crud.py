from sqlalchemy.orm import Session
import time
from sqlalchemy import desc, asc

from lib.fs.schemas import FileObject
from . import models, schemas
import uuid


# ASSISTANT
def create_assistant(db: Session, assistant: schemas.AssistantCreate):
    tools = [tool.model_dump() for tool in assistant.tools]
    # Generate a unique ID for the new assistant
    db_assistant = models.Assistant(
        id=str(uuid.uuid4()),
        object="assistant",
        name=assistant.name,
        description=assistant.description,
        model=assistant.model,
        instructions=assistant.instructions,
        tools=tools,  # Ensure your model and schema correctly handle serialization/deserialization # noqa
        file_ids=assistant.file_ids,
        _metadata=assistant.metadata,
        created_at=int(time.time()),  # Assuming UNIX timestamp for created_at
        # Include other fields as necessary
    )
    db.add(db_assistant)
    db.commit()
    db.refresh(db_assistant)
    return db_assistant


def get_assistants(
    db: Session, limit: int, order: str, after: str = None, before: str = None
):
    query = db.query(models.Assistant)

    # Apply ordering
    if order == "desc":
        query = query.order_by(desc(models.Assistant.created_at))
    else:
        query = query.order_by(asc(models.Assistant.created_at))

    # Apply pagination using 'after' and 'before' cursors
    if after:
        query = query.filter(models.Assistant.id > after)
    if before:
        query = query.filter(models.Assistant.id < before)

    return query.limit(limit).all()


def get_assistant_by_id(db: Session, assistant_id: str):
    """
    Retrieve an assistant by its ID from the database.
    """
    return (
        db.query(models.Assistant)
        .filter(models.Assistant.id == assistant_id)
        .first()
    )


def update_assistant(db: Session, assistant_id: str, assistant_update: dict):
    db_assistant = (
        db.query(models.Assistant)
        .filter(models.Assistant.id == assistant_id)
        .first()
    )
    if db_assistant:
        for key, value in assistant_update.items():
            if value:
                if key == "metadata":
                    setattr(db_assistant, "_metadata", value)
                else:
                    setattr(db_assistant, key, value)
        db.commit()
        db.refresh(db_assistant)
        return db_assistant
    return None


def delete_assistant(db: Session, assistant_id: str) -> bool:
    assistant = (
        db.query(models.Assistant)
        .filter(models.Assistant.id == assistant_id)
        .first()
    )
    if not assistant:
        return False
    db.delete(assistant)
    db.commit()
    return True


# FILE
def create_file(db: Session, file: FileObject):
    # save to db
    db_file = models.File(**file.model_dump())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file


def get_file(db: Session, file_id: str):
    return db.query(models.File).filter(models.File.id == file_id).first()


def delete_file(db: Session, file_id: str) -> bool:
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        return False
    db.delete(file)
    db.commit()
    return True


# THREAD
def create_thread(db: Session, thread_data: schemas.ThreadCreate):
    # Assume the ThreadCreate schema and Thread model are properly defined
    new_thread = models.Thread(
        id=str(uuid.uuid4()),
        _metadata=thread_data.metadata,
        created_at=int(time.time()),  # Using UNIX timestamp for created_at
    )
    # If your thread includes messages, you should handle their creation here
    db.add(new_thread)
    db.commit()
    db.refresh(new_thread)
    return new_thread


def get_thread(db: Session, thread_id: str):
    return (
        db.query(models.Thread).filter(models.Thread.id == thread_id).first()
    )


def update_thread(db: Session, thread_id: str, thread_data: dict):
    db_thread = (
        db.query(models.Thread).filter(models.Thread.id == thread_id).first()
    )
    if db_thread:
        for key, value in thread_data.items():
            if value:
                if key == "metadata":
                    setattr(db_thread, "_metadata", value)
                else:
                    setattr(db_thread, key, value)
        db.commit()
        db.refresh(db_thread)
        return db_thread
    return None


def delete_thread(db: Session, thread_id: str) -> bool:
    thread = (
        db.query(models.Thread).filter(models.Thread.id == thread_id).first()
    )
    print("thread in DB", thread, thread_id)
    if not thread:
        return False
    db.delete(thread)
    db.commit()
    return True


# MESSAGE
def create_message(
    db: Session, thread_id: str, message: schemas.ThreadMessageCreate
):
    # Create a new Message object
    db_message = models.Message(
        id=str(uuid.uuid4()),
        thread_id=thread_id,
        object="thread.message",
        role=message.role,
        content=[
            {
                "type": "text",
                "text": {"annotations": [], "value": message.content},
            }
        ],  # TODO: no idea what annotations does
        created_at=int(time.time()),
        file_ids=message.file_ids or [],
        _metadata=message.metadata or {},
    )

    # Add the new message to the session and commit
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    return db_message
