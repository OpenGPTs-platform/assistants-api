from typing import List, Optional
from sqlalchemy.orm import Session
import time
from sqlalchemy import desc, asc

from lib.fs.schemas import FileObject
from . import models, schemas
import uuid
import json


# ASSISTANT
def create_assistant(db: Session, assistant: schemas.AssistantCreate):
    # Serialize tools if they are provided
    tools = [tool.model_dump() for tool in assistant.tools]

    # Serialize tool_resources if provided
    tool_resources_json = (
        assistant.tool_resources.__dict__ if assistant.tool_resources else None
    )

    # Generate a unique ID for the new assistant
    db_assistant = models.Assistant(
        id=str(uuid.uuid4()),
        object="assistant",
        name=assistant.name,
        description=assistant.description,
        model=assistant.model,
        instructions=assistant.instructions,
        tools=tools,
        _metadata=assistant.metadata,
        response_format=assistant.response_format,
        temperature=assistant.temperature,
        tool_resources=tool_resources_json,
        top_p=assistant.top_p,
        created_at=int(time.time()),  # Assuming UNIX timestamp for created_at
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
        query = query.order_by(
            desc(models.Assistant.created_at), desc(models.Assistant.id)
        )
    else:
        query = query.order_by(
            asc(models.Assistant.created_at), asc(models.Assistant.id)
        )

    # Apply pagination using 'after' and 'before' cursors
    if after:
        last_seen_assistant = (
            db.query(models.Assistant)
            .filter(models.Assistant.id == after)
            .first()
        )
        if last_seen_assistant:
            query = query.filter(
                models.Assistant.created_at >= last_seen_assistant.created_at
            )

    if before:
        first_seen_assistant = (
            db.query(models.Assistant)
            .filter(models.Assistant.id == before)
            .first()
        )
        if first_seen_assistant:
            query = query.filter(
                models.Assistant.created_at <= first_seen_assistant.created_at
            )

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
                    updated_metadata = {**db_assistant._metadata, **value}
                    setattr(db_assistant, "_metadata", updated_metadata)
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
    if thread_data.messages:
        for idx, message in enumerate(thread_data.messages):
            create_message(db, new_thread.id, message, time_shift=idx)
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
                    updated_metadata = {**db_thread._metadata, **value}
                    setattr(db_thread, "_metadata", updated_metadata)
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
    if not thread:
        return False
    db.delete(thread)
    db.commit()
    return True


# MESSAGE
def create_message(
    db: Session,
    thread_id: str,
    message_inp: schemas.MessageInput,
    time_shift=0,
):
    # Create a new Message object
    message_content = schemas.TextContentBlock(
        text=schemas.Text(annotations=[], value=message_inp.content),
        type="text",
    )  # TODO: will need to update this for
    db_message = models.Message(
        id=str(uuid.uuid4()),
        thread_id=thread_id,
        object="thread.message",
        role=message_inp.role,
        content=[message_content.model_dump()],
        created_at=int(time.time()) + time_shift,
        attachments=message_inp.attachments if message_inp.attachments else [],
        assistant_id=None,  # Assuming this needs to be set in some other part of your application # noqa
        run_id=None,  # Same as above
        _metadata=message_inp.metadata if message_inp.metadata else {},
        status='completed',  # TODO: the status should be updated over time
    )

    # Add the new message to the session and commit
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    return db_message


def get_messages(
    db: Session,
    thread_id: str,
    limit: int,
    order: str,
    after: str,
    before: str,
):  # TODO: before and after work in a strange way
    query = db.query(models.Message).filter(
        models.Message.thread_id == thread_id
    )

    if order == "asc":
        query = query.order_by(
            asc(models.Message.created_at), asc(models.Message.id)
        )
    else:
        query = query.order_by(
            desc(models.Message.created_at), desc(models.Message.id)
        )

    if after:
        last_seen_message = (
            db.query(models.Message).filter(models.Message.id == after).first()
        )
        if last_seen_message:
            query = query.filter(
                models.Message.created_at >= last_seen_message.created_at
            )

    if before:
        first_seen_message = (
            db.query(models.Message)
            .filter(models.Message.id == before)
            .first()
        )
        if first_seen_message:
            query = query.filter(
                models.Message.created_at <= first_seen_message.created_at
            )

    return query.limit(limit).all()


def get_message_by_id(db: Session, thread_id: str, message_id: str):
    return (
        db.query(models.Message)
        .filter(
            models.Message.id == message_id,
            models.Message.thread_id == thread_id,
        )
        .first()
    )


def update_message(
    db: Session, thread_id: str, message_id: str, message_update: dict
):
    db_message = (
        db.query(models.Message)
        .filter(
            models.Message.id == message_id,
            models.Message.thread_id == thread_id,
        )
        .first()
    )
    if db_message:
        for key, value in message_update.items():
            if (
                value is not None
            ):  # Allowing updates with falsy values like 0 or False
                if key == "metadata":
                    updated_metadata = {**db_message._metadata, **value}
                    setattr(db_message, "_metadata", updated_metadata)
                else:
                    setattr(db_message, key, value)
        db.commit()
        db.refresh(db_message)
        return db_message
    return None


# RUNS
def create_run(db: Session, thread_id: str, run: schemas.RunContent):
    # Check if the thread exists
    db_thread = get_thread(db, thread_id)
    if not db_thread:
        raise ValueError(f"Thread with ID {thread_id} does not exist")

    # Check if the assistant exists
    db_assistant = get_assistant_by_id(db, run.assistant_id)
    if not db_assistant:
        raise ValueError(
            f"Assistant with ID {run.assistant_id} does not exist"
        )

    # Set fields from run or fallback to assistant's values
    instructions = (
        run.instructions if run.instructions else db_assistant.instructions
    )
    model = run.model if run.model else db_assistant.model
    tools = run.tools if run.tools else db_assistant.tools
    metadata = run.metadata if run.metadata else db_assistant._metadata

    # Create the Run instance
    db_run = models.Run(
        id=str(uuid.uuid4()),
        thread_id=thread_id,
        assistant_id=run.assistant_id,
        created_at=int(time.time()),
        expires_at=int(time.time()) + 3600,  # Assuming 1-hour expiration
        instructions=instructions
        + " "
        + run.additional_instructions,  # Assuming this is how OpenAI handles additional instructions # noqa
        model=model,
        tools=tools,
        _metadata=metadata,
        status=schemas.RunStatus.QUEUED.value,
    )

    # Add and commit the new Run to the database
    db.add(db_run)
    db.commit()
    db.refresh(db_run)

    return db_run


def get_run(db: Session, thread_id: str, run_id: str):
    return (
        db.query(models.Run)
        .filter(models.Run.id == run_id, models.Run.thread_id == thread_id)
        .first()
    )


def cancel_run(db: Session, thread_id: str, run_id: str):
    db_run = (
        db.query(models.Run)
        .filter(models.Run.id == run_id, models.Run.thread_id == thread_id)
        .first()
    )
    if db_run:
        db_run.status = schemas.RunStatus.CANCELLING.value
        db.commit()
        db.refresh(db_run)
        return db_run
    return None


def get_run_steps(
    db: Session,
    thread_id: str,
    run_id: str,
    limit: int,
    order: str,
    after: str = None,
    before: str = None,
):  # TODO: before and after work in a strange way
    query = db.query(models.RunStep).filter(
        models.RunStep.thread_id == thread_id, models.RunStep.run_id == run_id
    )
    if order == "asc":
        query = query.order_by(asc(models.RunStep.created_at))
    else:
        query = query.order_by(desc(models.RunStep.created_at))
    if after:
        query = query.filter(models.RunStep.id > after)
    if before:
        query = query.filter(models.RunStep.id < before)
    return query.limit(limit).all()


###########################################################
#                        OPS                              #
###########################################################
def update_run(db: Session, thread_id: str, run_id: str, run_update: dict):
    db_run = (
        db.query(models.Run)
        .filter(models.Run.id == run_id, models.Run.thread_id == thread_id)
        .first()
    )
    if db_run:
        for key, value in run_update.items():
            if (
                value is not None
            ):  # Allowing updates with falsy values like 0 or False
                if key == "metadata":
                    setattr(db_run, "_metadata", value)
                else:
                    setattr(db_run, key, value)

        db.add(db_run)
        db.commit()
        db.refresh(db_run)
        return db_run
    return None


def create_run_step(
    db: Session, thread_id: str, run_id: str, run_step: schemas.RunStepCreate
):
    new_run_step = models.RunStep(
        id=str(uuid.uuid4()),
        assistant_id=run_step.assistant_id,
        step_details=run_step.step_details.model_dump(),
        type=run_step.type,
        status=run_step.status,
        run_id=run_id,
        thread_id=thread_id,
        created_at=int(time.time()),
        object="thread.run.step",  # Default value for the object field
    )

    db.add(new_run_step)
    db.commit()
    db.refresh(new_run_step)
    return new_run_step


def update_run_step(
    db: Session,
    thread_id: str,
    run_id: str,
    step_id: str,
    run_step_update: dict,
):
    db_run_step = (
        db.query(models.RunStep)
        .filter(
            models.RunStep.id == step_id,
            models.RunStep.run_id == run_id,
            models.RunStep.thread_id == thread_id,
        )
        .first()
    )

    if db_run_step:
        for key, value in run_step_update.items():
            if (
                value is not None
            ):  # Allow updates with falsy values like 0 or False
                # Check if the attribute exists within the model before updating
                if hasattr(db_run_step, key):
                    setattr(db_run_step, key, value)
                elif key == "metadata":  # Special handling for metadata
                    setattr(db_run_step, "_metadata", value)

        db.add(db_run_step)
        db.commit()
        db.refresh(db_run_step)
        return db_run_step

    return None


def create_vector_store(db: Session, vector_store: schemas.VectorStoreCreate):
    # Convert expiration details to JSON if necessary
    expiration_after = (
        vector_store.expires_after if vector_store.expires_after else None
    )
    file_counts = schemas.FileCounts(
        cancelled=0,
        completed=0,
        failed=0,
        in_progress=len(vector_store.file_ids),
        total=0,
    )

    # if in FileCounts in progress then status is in_progress else status is completed
    status = "in_progress" if (file_counts.in_progress > 0) else "completed"

    db_vector_store = models.VectorStore(
        id="vs_" + str(uuid.uuid4()),
        name=vector_store.name,
        expires_after=expiration_after,
        file_counts=file_counts.model_dump(),
        status=status,
        usage_bytes=0,
        _metadata={**vector_store.metadata, "_file_ids": json.dumps([])},
        created_at=int(time.time()),
    )
    db.add(db_vector_store)
    db.commit()
    db.refresh(db_vector_store)
    return db_vector_store


def update_vector_store(db: Session, vector_store_id: str, updates: dict):
    db_vector_store = (
        db.query(models.VectorStore)
        .filter(models.VectorStore.id == vector_store_id)
        .first()
    )
    if db_vector_store:
        for key, value in updates.items():
            if value:
                if key == "metadata":
                    setattr(db_vector_store, "_metadata", value)
                else:
                    setattr(db_vector_store, key, value)
        db.commit()
        db.refresh(db_vector_store)
        return db_vector_store
    return None


def get_vector_store(db: Session, vector_store_id: str):
    return (
        db.query(models.VectorStore)
        .filter(models.VectorStore.id == vector_store_id)
        .first()
    )


def get_vector_stores(
    db: Session,
    limit: int,
    order: str,
    after: Optional[str] = None,
    before: Optional[str] = None,
):
    query = db.query(models.VectorStore)

    # Order the query based on the created_at timestamp and ID
    if order == "asc":
        query = query.order_by(
            asc(models.VectorStore.created_at), asc(models.VectorStore.id)
        )
    else:
        query = query.order_by(
            desc(models.VectorStore.created_at), desc(models.VectorStore.id)
        )

    # Apply pagination filters
    if after:
        # Get the 'after' vector store to determine the pagination start
        last_seen_store = (
            db.query(models.VectorStore)
            .filter(models.VectorStore.id == after)
            .first()
        )
        if last_seen_store:
            query = query.filter(
                (models.VectorStore.created_at, models.VectorStore.id)
                > (last_seen_store.created_at, last_seen_store.id)
            )

    if before:
        # Get the 'before' vector store to determine the pagination end
        first_seen_store = (
            db.query(models.VectorStore)
            .filter(models.VectorStore.id == before)
            .first()
        )
        if first_seen_store:
            query = query.filter(
                (models.VectorStore.created_at, models.VectorStore.id)
                < (first_seen_store.created_at, first_seen_store.id)
            )

    return query.limit(limit).all()


def create_file_batch(db: Session, vector_store_id: str, file_ids: List[str]):
    file_counts = schemas.FileCounts(
        cancelled=0,
        completed=0,
        failed=0,
        in_progress=len(file_ids),
        total=0,
    )
    new_batch = models.VectorStoreFileBatch(
        id="vsfb_" + str(uuid.uuid4()),
        created_at=int(time.time()),
        vector_store_id=vector_store_id,
        status="in_progress",
        file_counts=file_counts.model_dump(),
        object="vector_store.files_batch",
    )
    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)
    return new_batch


def update_file_batch(db: Session, file_batch_id: str, updates: dict):
    db_vector_store = (
        db.query(models.VectorStoreFileBatch)
        .filter(models.VectorStoreFileBatch.id == file_batch_id)
        .first()
    )
    if db_vector_store:
        for key, value in updates.items():
            if value:
                setattr(db_vector_store, key, value)
        db.commit()
        db.refresh(db_vector_store)
        return db_vector_store
    return None
