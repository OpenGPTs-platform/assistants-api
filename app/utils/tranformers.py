from lib.db import models
from lib.db import schemas


def db_to_pydantic_assistant(
    db_assistant: models.Assistant,
) -> schemas.Assistant:
    assistant_dict = db_assistant.__dict__
    del assistant_dict["_sa_instance_state"]
    return schemas.Assistant(**assistant_dict)
