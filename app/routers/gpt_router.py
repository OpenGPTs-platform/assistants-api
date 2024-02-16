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


@router.get("/login/gpt", response_model=List[GptStaging])
def get_user_gpts(
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Get a list of all GPT assistants.

    Args:
    - query (str): The query to filter by.
    - user_id (str): The user ID to filter by.

    Returns:
    - List[Gpt]: The list of GPTs.
    """
    user_gpts = []
    all_user_gpts = crud.get_user_gpts(db=db, user_id=user_id)

    for user_gpt in all_user_gpts:
        assistant = openai_client.beta.assistants.retrieve(user_gpt.gpt_id)
        print("assistant", json.dumps(assistant.model_dump(), indent=2))
        try:
            user_gpts.append(GptStaging(**dict(assistant)))
        except Exception:
            print("Error parsing assistant to GptStaging", assistant)

    return user_gpts


@router.get("/gpt", response_model=List[GptMain])
def list_gpts(
    query: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get a list of all GPT assistants.

    Args:
    - query (str): The query to filter by.
    - user_id (str): The user ID to filter by.

    Returns:
    - List[Gpt]: The list of GPTs.
    """
    assistants = openai_client.beta.assistants.list()
    all_gpts = []
    for assistant in assistants.data:
        try:
            if "is_staging" in assistant.metadata:
                continue
            if assistant.metadata["visibility"] != "public":
                continue
            else:
                all_gpts.append(GptMain(**dict(assistant)))
        except Exception as e:
            print("Error parsing assistant to GptMain", assistant, e)

    if query:
        all_gpts = [
            gpt
            for gpt in all_gpts
            if (gpt.description and query in gpt.description)
        ]
    return all_gpts


@router.delete("/gpt")
def delete_all_gpts(db: Session = Depends(get_db)):
    for gpt in openai_client.beta.assistants.list().data:
        openai_client.beta.assistants.delete(gpt.id)
    crud.delete_all_gpts(db)
    crud.delete_all_threads(db)


@router.patch("/gpt/{assistant_id}/update", response_model=GptStaging)
def update_gpt(
    assistant_id,
    request: UpsertGpt,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Save your staging GPT.

    Args:
    - assistant_id (str): The ID of the assistant to update.
    - request (UpsertGpt): The updated GPT data.

    Headers:
    - auth (str): Bearer <JWT_TOKEN>

    Returns:
    - Gpt: The updated GPT instance.
    """

    validate_user_gpt(db, user_id, assistant_id)

    # Update the staging GPT Assistant
    updated_gpt = openai_client.beta.assistants.update(
        assistant_id, **request.model_dump()
    )

    return updated_gpt


@router.post(
    "/gpt/{assistant_id}/publish", response_model=tuple[GptStaging, GptMain]
)
def publish_gpt(
    assistant_id,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Publish your staging GPT to its corresponding main GPT.

    Args:
    - assistant_id (str): The ID of the assistant to update.

    Headers:
    - auth (str): Bearer <JWT_TOKEN>

    Returns:
    - tuple[Gpt, Gpt]: The updated staging then main GPT instances.
    """

    # this also verifies that the assistant is staging
    validate_user_gpt(db, user_id, assistant_id)

    request_assistant = openai_client.beta.assistants.retrieve(assistant_id)

    json_request_assistant = request_assistant.model_dump()
    del json_request_assistant["object"]
    del json_request_assistant["created_at"]
    staging_assistant = json.loads(json.dumps(json_request_assistant))
    del json_request_assistant["id"]
    main_assistant_id = json_request_assistant["metadata"]["ref"]
    del json_request_assistant["metadata"]["is_staging"]
    del json_request_assistant["metadata"]["ref"]

    openai_client.beta.assistants.update(
        main_assistant_id, **json_request_assistant
    )

    # # OBSERVABILITY: find assistant with id ==
    # # updated_gpt_dict["metadata"]["ref"]
    # all_assistants = client.beta.assistants.list()
    # main_gpt = [
    #     assistant
    #     for assistant in all_assistants.data
    #     if assistant.id == request_gpt.metadata["ref"]
    # ][0]

    return (GptStaging(**staging_assistant), GptMain(**staging_assistant))


@router.post("/gpt/file", response_model=FileObject)
async def upload_file(file: UploadFile, user_id: str = Depends(get_user_id)):
    """
    Upload a file to Assistants API.

    Args:
    - file (UploadFile): The file to upload.

    Headers:
    - auth (str): Bearer <JWT_TOKEN>

    Returns:
    - FileObject: Object containing file id and other details.
    """
    content = await file.read()
    assistant_file = openai_client.files.create(
        file=(file.filename, content),
        purpose='assistants',
        # metadata={
        #     "user_id": user_id,
        # },
    )
    return assistant_file


@router.get("/gpt/file/{file_id}", response_model=FileObject)
async def get_uploaded_file(file_id: str, user_id: str = Depends(get_user_id)):
    assistant_file = openai_client.files.retrieve(
        file_id=file_id,
    )
    # if assistant_file.metadata["user_id"] != user_id:
    #     raise HTTPException(
    #         status_code=404,
    #         detail="User does not have access to this file.",
    #     )
    return assistant_file
