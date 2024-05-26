import pytest
from openai import OpenAI

from openai.types.beta.threads.runs import FileSearchToolCall

from openai.types.beta.threads.runs.web_retrieval_tool_call import (
    WebRetrievalToolCall,
)

# from openai.types.beta.threads.runs import RunStep
import os

import time

api_key = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else None
use_openai = True if os.getenv("USE_OPENAI") else False
base_url = "http://localhost:8000"


@pytest.fixture
def openai_client():
    if use_openai:
        return OpenAI(
            api_key=api_key,
        )
    else:
        return OpenAI(
            base_url=base_url,
        )


# # TODO: cleanup are causing issues with the tests, uncomment when fixed or using OpenAI API # noqa
# @pytest.fixture(scope="session", autouse=True)
# def cleanup(request):
#     openai_client = OpenAI(
#         base_url="http://localhost:8000",
#         api_key=api_key,
#     )

#     def remove_all_assistants():
#         for assistant in openai_client.beta.assistants.list().data:
#             openai_client.beta.assistants.delete(assistant.id)

#     request.addfinalizer(remove_all_assistants)


@pytest.fixture
def thread_id(openai_client: OpenAI):
    thread_metadata = {"example_key": "example_value"}
    response = openai_client.beta.threads.create(
        metadata=thread_metadata,
        messages=[
            {
                "role": "user",
                "content": "show me an example of a test I have created, if there is a list in its metadata make sure to explicitly write it out.",  # noqa
            }
        ],
    )
    return response.id


@pytest.fixture
def assistant_id(openai_client: OpenAI):
    response = openai_client.beta.assistants.create(
        instructions="Your job is to first execute tools as needed, and finally summarize the exchange.",  # noqa
        name="Tool Assistant",
        model="gpt-3.5-turbo",
    )
    return response.id


@pytest.fixture
def run_id(openai_client: OpenAI, thread_id: str, assistant_id: str):
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    return response.id


@pytest.mark.dependency()
def test_no_tool_run_execution(openai_client: OpenAI, assistant_id: str):
    file = openai_client.files.create(
        file=open("./assets/code-reference.txt", "rb"), purpose='assistants'
    )
    vs = openai_client.beta.vector_stores.create(name="my code")
    openai_client.beta.vector_stores.file_batches.create(
        vector_store_id=vs.id, file_ids=[file.id]
    )
    openai_client.beta.assistants.update(
        assistant_id=assistant_id,
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vs.id]}},
    )

    thread_response = openai_client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "when did ww2 happen (answer concisely)",  # noqa
            }
        ],
    )
    thread_id = thread_response.id
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    assert response.status == "queued"
    # sleep for 10 seconds while the run is in progress
    time.sleep(0.1)
    response = openai_client.beta.threads.runs.retrieve(
        thread_id=thread_id, run_id=response.id
    )
    assert response.status == "in_progress"
    time.sleep(4)

    response = openai_client.beta.threads.runs.retrieve(
        thread_id=thread_id, run_id=response.id
    )
    assert response.status == "completed"
    response = openai_client.beta.threads.runs.steps.list(
        run_id=response.id,
        thread_id=thread_id,
        order="asc",  # newest at the end
    )
    assert len(response.data) >= 1
    # assert that at least one of the steps is a retrieval tool call
    assert response.data[-1].step_details.type == "message_creation"


@pytest.mark.dependency(depends=["test_no_tool_run_execution"])
def test_file_search_run_executor(openai_client: OpenAI, assistant_id: str):
    file = openai_client.files.create(
        file=open("./assets/code-reference.txt", "rb"), purpose='assistants'
    )
    vs = openai_client.beta.vector_stores.create(name="my code")
    openai_client.beta.vector_stores.file_batches.create(
        vector_store_id=vs.id, file_ids=[file.id]
    )
    openai_client.beta.assistants.update(
        assistant_id=assistant_id,
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vs.id]}},
    )
    thread_response = openai_client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "when did ww2 happen",  # noqa
            },
            {
                "role": "assistant",
                "content": "WW2 happened from 1939-1945",  # noqa
            },
            {
                "role": "user",
                "content": "Please retrieve code my code reference for a test called test_create_assistant and once retrieved describe each of its configuration details to me.",  # noqa
            },
        ],
    )
    thread_id = thread_response.id
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    assert response.status == "queued"
    # Check every 4 seconds, up to 5 times
    max_checks = 12
    check_interval = 2
    for _ in range(max_checks):
        time.sleep(check_interval)
        response = openai_client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=response.id
        )

        assert response.status in ["in_progress", "completed"]

        if response.status == "completed":
            break
    else:
        # If the loop completes without breaking, assert failure due to timeout
        assert False, "Run did not complete within the expected time."

    # Once completed, retrieve steps and perform final assertions
    steps_response = openai_client.beta.threads.runs.steps.list(
        run_id=response.id,
        thread_id=thread_id,
        order="asc",
    )
    assert len(steps_response.data) > 1

    # Ensure there is at least one tool call of type WebRetrievalToolCall
    assert any(
        step.step_details.type == "tool_calls"
        and any(
            isinstance(tool_call, FileSearchToolCall)
            for tool_call in step.step_details.tool_calls
        )
        for step in steps_response.data
    )


@pytest.mark.skipif(
    use_openai, reason="OpenAI API does not support web retrieval"
)
@pytest.mark.dependency(depends=["test_no_tool_run_execution"])
def test_web_retrieval_run_executor(openai_client: OpenAI, assistant_id: str):
    file = openai_client.files.create(
        file=open("./assets/code-reference.txt", "rb"), purpose='assistants'
    )
    vs = openai_client.beta.vector_stores.create(name="my code")
    openai_client.beta.vector_stores.file_batches.create(
        vector_store_id=vs.id, file_ids=[file.id]
    )
    openai_client.beta.assistants.update(
        assistant_id=assistant_id,
        tools=[{"type": "file_search"}, {"type": "web_retrieval"}],
        tool_resources={"file_search": {"vector_store_ids": [vs.id]}},
    )
    thread_response = openai_client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "when did ww2 happen",  # noqa
            },
            {
                "role": "assistant",
                "content": "WW2 happened from 1939-1945",  # noqa
            },
            {
                "role": "user",
                "content": "What scholarships can I obtain if I transfer from an in-state college to UF",  # noqa
            },
        ],
    )
    thread_id = thread_response.id
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    assert response.status == "queued"
    # Check every 4 seconds, up to 5 times
    max_checks = 12
    check_interval = 2
    for _ in range(max_checks):
        time.sleep(check_interval)
        response = openai_client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=response.id
        )

        assert response.status in ["in_progress", "completed"]

        if response.status == "completed":
            break
    else:
        # If the loop completes without breaking, assert failure due to timeout
        assert False, "Run did not complete within the expected time."

    # Once completed, retrieve steps and perform final assertions
    steps_response = openai_client.beta.threads.runs.steps.list(
        run_id=response.id,
        thread_id=thread_id,
        order="asc",
    )
    assert len(steps_response.data) > 1

    # Ensure there is at least one tool call of type WebRetrievalToolCall
    assert any(
        step.step_details.type == "tool_calls"
        and any(
            isinstance(tool_call, WebRetrievalToolCall)
            for tool_call in step.step_details.tool_calls
        )
        for step in steps_response.data
    )
