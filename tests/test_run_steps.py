import pytest
from openai import OpenAI
import requests
from openai.types.beta.threads.runs import RunStep
import os

# import time

api_key = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else None


@pytest.fixture
def openai_client():
    return OpenAI(
        base_url="http://localhost:8000",
        api_key=api_key,
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
    file = openai_client.files.create(
        file=open("./assets/code-reference.txt", "rb"), purpose='assistants'
    )
    response = openai_client.beta.assistants.create(
        instructions="Your job is to first execute tools as needed, and finally summarize the exchange.",  # noqa
        name="Tool Assistant",
        tools=[{"type": "retrieval"}],
        file_ids=[file.id],
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


# @pytest.mark.dependency()
# def test_read_run_steps_active_executor(
#     openai_client: OpenAI, thread_id: str, assistant_id: str
# ):
#     response = openai_client.beta.threads.runs.create(
#         thread_id=thread_id,
#         assistant_id=assistant_id,
#     )
#     # sleep for 10 seconds while the run is in progress
#     time.sleep(5)
#     response = openai_client.beta.threads.runs.steps.list(
#         thread_id=thread_id, run_id=response.id
#     )

#     assert len(response.data) > 0
#     assert isinstance(response.data[0], RunStep)
#     assert response.data[0].id is not None
#     assert response.data[0].step_details.type == "message_creation"
#     assert (
#         response.data[0].step_details.message_creation.message_id[:4] == "msg_"
#     )
#     assert response.data[1].id is not None
#     assert response.data[1].step_details.type == "tool_calls"
#     assert response.data[1].step_details.tool_calls[0].type == "retrieval"


# only works with access to steps (therefore does not work with OpenAI hosted Assistants API) # noqa
@pytest.mark.dependency()
def test_create_run_step(
    openai_client: OpenAI, assistant_id: str, thread_id: str, run_id: str
):
    create_url = (
        f"http://localhost:8000/ops/threads/{thread_id}/runs/{run_id}/steps"
    )
    step_data_tool = {
        "assistant_id": assistant_id,
        "type": "tool_calls",
        "status": "in_progress",
        "step_details": {"tool_calls": [], "type": "tool_calls"},
    }
    step_data_message = {
        "assistant_id": assistant_id,
        "type": "message_creation",
        "status": "in_progress",
        "step_details": {
            "message_creation": {"message_id": "msg_6iTjazdBj74xg3yVbjrZye9P"},
            "type": "message_creation",
        },
    }

    requests.post(create_url, json=step_data_tool)
    requests.post(create_url, json=step_data_message)

    response = openai_client.beta.threads.runs.steps.list(
        thread_id=thread_id, run_id=run_id
    )
    assert response is not None
    assert len(response.data) == 2
    assert isinstance(response.data[0], RunStep)
    assert response.data[0].id is not None
    assert response.data[0].step_details.type == "tool_calls"
    assert response.data[1].id is not None
    assert response.data[1].step_details.type == "message_creation"
    assert (
        response.data[1].step_details.message_creation.message_id
        == "msg_6iTjazdBj74xg3yVbjrZye9P"
    )
