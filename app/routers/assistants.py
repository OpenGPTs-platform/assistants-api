import json
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile
from utils.auth import validate_user_gpt

from utils.parsers import get_user_id
from models.gpt import (
    GptMain,
    GptStaging,
    UpsertGpt,
)
from db.database import get_db

from sqlalchemy.orm import Session
from db import crud, schemas
from openai.types import FileObject
from utils.api import openai_client


router = APIRouter()

openai_client.beta.assistants.create(
    
)

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