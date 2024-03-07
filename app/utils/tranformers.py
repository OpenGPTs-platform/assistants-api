from lib.db import models
from lib.db import schemas


def db_to_pydantic_assistant(
    db_assistant: models.Assistant,
) -> schemas.Assistant:
    assistant_dict = db_assistant.__dict__
    del assistant_dict["_sa_instance_state"]
    return schemas.Assistant(**assistant_dict)


def db_to_pydantic_thread(
    db_thread: models.Thread,
) -> schemas.Thread:
    thread_dict = db_thread.__dict__
    del thread_dict["_sa_instance_state"]
    thread_dict["metadata"] = thread_dict["_metadata"]
    del thread_dict["_metadata"]
    return schemas.Thread(**thread_dict)
