from sqlalchemy.orm import Session
import time
from sqlalchemy import desc, asc
from . import models, schemas
import uuid


# ASSISTANT
def create_assistant(db: Session, assistant: schemas.AssistantCreate):
    tools = [tool.dict() for tool in assistant.tools]
    print("tools", tools)
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
        metadata=assistant.metadata,
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
