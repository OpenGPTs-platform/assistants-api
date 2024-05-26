from lib.db import models
from lib.db import schemas


def db_to_pydantic_assistant(
    db_assistant: models.Assistant,
) -> schemas.Assistant:
    assistant_dict = db_assistant.__dict__
    assistant_dict = assistant_dict.copy()
    del assistant_dict["_sa_instance_state"]
    assistant_dict["metadata"] = assistant_dict["_metadata"]
    del assistant_dict["_metadata"]
    return schemas.Assistant(**assistant_dict)


def db_to_pydantic_thread(
    db_thread: models.Thread,
) -> schemas.Thread:
    thread_dict = db_thread.__dict__
    thread_dict = thread_dict.copy()
    del thread_dict["_sa_instance_state"]
    thread_dict["metadata"] = thread_dict["_metadata"]
    del thread_dict["_metadata"]
    return schemas.Thread(**thread_dict)


def db_to_pydantic_message(
    db_message: models.Message,
) -> schemas.Message:
    message_dict = db_message.__dict__
    message_dict = message_dict.copy()
    del message_dict["_sa_instance_state"]
    message_dict["metadata"] = message_dict["_metadata"]
    del message_dict["_metadata"]
    return schemas.Message(**message_dict)


def db_to_pydantic_run(
    db_run: models.Run,
) -> schemas.Run:
    run_dict = db_run.__dict__
    run_dict = run_dict.copy()
    del run_dict["_sa_instance_state"]
    run_dict["metadata"] = run_dict["_metadata"]
    del run_dict["_metadata"]
    return schemas.Run(**run_dict)


def db_to_pydantic_runstep(
    db_run_step: models.RunStep,
) -> schemas.RunStep:
    run_step_dict = db_run_step.__dict__
    run_step_dict = run_step_dict.copy()
    del run_step_dict["_sa_instance_state"]
    run_step_dict["metadata"] = run_step_dict["_metadata"]
    del run_step_dict["_metadata"]
    return schemas.RunStep(**run_step_dict)


def db_to_pydantic_vector_store(
    db_vector_store: models.VectorStore,
) -> schemas.VectorStore:
    vector_store_dict = db_vector_store.__dict__
    vector_store_dict = vector_store_dict.copy()
    del vector_store_dict["_sa_instance_state"]
    vector_store_dict["metadata"] = vector_store_dict["_metadata"]
    del vector_store_dict["_metadata"]
    return schemas.VectorStore(**vector_store_dict)


def db_to_pydantic_vector_store_file_batch(
    db_vector_store_file_batch: models.VectorStoreFileBatch,
) -> schemas.VectorStoreFileBatch:
    vector_store_file_batch_dict = db_vector_store_file_batch.__dict__
    vector_store_file_batch_dict = vector_store_file_batch_dict.copy()
    del vector_store_file_batch_dict["_sa_instance_state"]
    return schemas.VectorStoreFileBatch(**vector_store_file_batch_dict)
