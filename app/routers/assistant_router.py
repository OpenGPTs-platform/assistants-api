import json
from fastapi import APIRouter, Depends

from utils.parsers import get_user_id
from models.gpt import (
    GptStaging,
    UpsertGpt,
)
from db.database import get_db

from sqlalchemy.orm import Session
from db import crud, schemas
from utils.api import openai_client


router = APIRouter()


@router.post("/assistants", response_model=schemas.Assistant)
def create_assistant(
    assistant: schemas.AssistantCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new assistant.
    - **model**: ID of the model to use.
    - **name**: The name of the assistant.
    - **description**: The description of the assistant.
    - **instructions**: The system instructions that the assistant uses.
    - **tools**: A list of tools enabled on the assistant.
    - **file_ids**: A list of file IDs attached to this assistant.
    - **metadata**: Set of 16 key-value pairs that can be attached to the assistant.
    """
    db_assistant = crud.create_assistant(db=db, assistant=assistant)
    print("db_assistant", db_assistant)
    return db_assistant


@router.post("/gpt", response_model=GptStaging)
def create_gpt(
    request: UpsertGpt,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a GPT instance and a corresponding staging GPT instance.

    Args:
    - request (UpsertGpt): The updated GPT data.

    Headers:
    - auth (str): Bearer <JWT_TOKEN>

    Returns:
    - Gpt: The staging GPT instance.
    """
    print("request", json.dumps(request.model_dump(), indent=2))

    # Create Main GPT Instance
    main_gpt_dict = dict(request)
    main_gpt_dict["metadata"] = dict(request.metadata)
    main_gpt = openai_client.beta.assistants.create(**request.model_dump())

    # Create Staging GPT Instance
    staging_gpt_dict = dict(request)
    staging_gpt_dict["metadata"] = {
        **dict(request.metadata),
        "is_staging": "true",
        "ref": main_gpt.id,
    }
    staging_gpt = openai_client.beta.assistants.create(**staging_gpt_dict)
    crud.create_user_gpt(
        db=db,
        user_gpt=schemas.UserGpt(user_id=user_id, gpt_id=staging_gpt.id),
    )

    return GptStaging(**staging_gpt.model_dump())
