import pytest
from openai import OpenAI
from openai.types.beta.threads import Run
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


@pytest.fixture
def thread_id(openai_client: OpenAI):
    thread_metadata = {"example_key": "example_value"}
    response = openai_client.beta.threads.create(metadata=thread_metadata)
    return response.id


@pytest.fixture
def assistant_id(openai_client: OpenAI):
    response = openai_client.beta.assistants.create(
        instructions="Always begin your response with the word 'banana'.",
        name="Example Assistant",
        tools=[{"type": "code_interpreter"}],
        model="gpt-3.5-turbo",
    )
    return response.id


@pytest.mark.dependency()
def test_create_run(openai_client: OpenAI, thread_id: str, assistant_id: str):
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    assert isinstance(response, Run)
    assert response.id is not None

    assert response.thread_id == thread_id
    assert response.assistant_id == assistant_id
    # Additional assertions can be added based on the expected response


@pytest.mark.dependency(depends=["test_create_run"])
def test_create_run_with_modified_instruction(
    openai_client: OpenAI, thread_id: str, assistant_id: str
):
    instructions = "You are a human."
    additional_instructions = "Your job is to be useless."
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions=instructions,
        additional_instructions=additional_instructions,
    )

    assert isinstance(response, Run)
    assert response.id is not None
    assert response.thread_id == thread_id
    assert response.assistant_id == assistant_id
    assert (
        response.instructions == instructions + " " + additional_instructions
    )
    # Additional assertions can be added based on the expected response


@pytest.fixture
def run_id_and_thread_id(
    openai_client: OpenAI, thread_id: str, assistant_id: str
):
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    return (response.id, thread_id)


@pytest.mark.dependency(depends=["test_create_run"])
def test_get_run(openai_client: OpenAI, run_id_and_thread_id: tuple):
    response = openai_client.beta.threads.runs.retrieve(
        run_id=run_id_and_thread_id[0], thread_id=run_id_and_thread_id[1]
    )

    # Validate the response structure and data (simplified example)
    assert response.id == run_id_and_thread_id[0]
    assert response.object == "thread.run"
    assert response.thread_id == run_id_and_thread_id[1]
    assert response.assistant_id is not None
    assert response.status in [
        "queued",
        "in_progress",
        "requires_action",
        "cancelling",
        "cancelled",
        "failed",
        "completed",
        "expired",
    ]


@pytest.mark.dependency(depends=["test_create_run", "test_get_run"])
def test_cancel_run(openai_client: OpenAI, run_id_and_thread_id: tuple):
    progress_run_response = openai_client.beta.threads.runs.retrieve(
        run_id=run_id_and_thread_id[0], thread_id=run_id_and_thread_id[1]
    )

    assert progress_run_response.status in [
        "queued",
        "in_progress",
        "requires_action",
    ]

    # Test Execution
    response = openai_client.beta.threads.runs.cancel(
        run_id=run_id_and_thread_id[0], thread_id=run_id_and_thread_id[1]
    )

    # Assertions
    assert response.id == run_id_and_thread_id[0]
    assert response.status in ["cancelling", "cancelled"]

    post_cancel_run_response = openai_client.beta.threads.runs.retrieve(
        run_id=run_id_and_thread_id[0], thread_id=run_id_and_thread_id[1]
    )

    assert post_cancel_run_response.id == run_id_and_thread_id[0]
    assert post_cancel_run_response.status in ["cancelling", "cancelled"]


@pytest.mark.dependency(depends=["test_create_run", "test_get_run"])
def test_run_execution(
    openai_client: OpenAI, assistant_id: str, thread_id: str
):
    openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content="What year was the Apollo 11 moon landing (answer concisely)",  # 1969
    )
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

        assert response.status in ["queued", "in_progress", "completed"]

        if response.status == "completed":
            break
    else:
        # If the loop completes without breaking, assert failure due to timeout
        assert False, "Run did not complete within the expected time."

    # once completed check the messages for correct generation
    messages = openai_client.beta.threads.messages.list(
        thread_id=thread_id, order="desc"
    )
    assert len(messages.data) == 2
    assert messages.data[0].role == "assistant"
    assert "1969" in messages.data[0].content[0].text.value


@pytest.mark.dependency(depends=["test_create_run", "test_get_run"])
def test_run_instruction_following(
    openai_client: OpenAI, assistant_id: str, thread_id: str
):
    openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content="What year was the Apollo 11 moon landing (answer concisely), follow my instructions",  # noqa
    )
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

    # once completed check the messages for correct generation
    messages = openai_client.beta.threads.messages.list(
        thread_id=thread_id, order="desc"
    )
    assert len(messages.data) == 2
    assert messages.data[0].role == "assistant"
    assert "banana" in messages.data[0].content[0].text.value.lower()


@pytest.mark.dependency(depends=["test_create_run", "test_get_run"])
def test_run_with_context_truncation(
    openai_client: OpenAI,
):
    asst = openai_client.beta.assistants.create(
        name="Example Assistant",
        model="gpt-3.5-turbo",
    )
    assistant_id = asst.id

    # compose messages
    token_eq_100 = "lorem ipsum dolor sit amet, consectetur adipiscing elit. sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. except occaecat. "  # noqa
    message_eq_100_tokens = [
        {
            "role": "user",
            "content": token_eq_100,
        }
    ]
    thread_messages = [
        {
            "role": "user",
            "content": "My favorite fruit is Mangosteen",
        },
        {
            "role": "assistant",
            "content": "Great to hear that! I will remember that.",
        },
    ]
    thread_messages += message_eq_100_tokens * 4
    thread_messages.append(
        {
            "role": "user",
            "content": "What is my favorite fruit (answer concisely)",
        }
    )

    # create threads and runs with and without truncation
    thread_without_truncation = openai_client.beta.threads.create(
        messages=thread_messages
    )
    response_without_truncation = openai_client.beta.threads.runs.create(
        thread_id=thread_without_truncation.id, assistant_id=assistant_id
    )
    thread_with_truncation = openai_client.beta.threads.create(
        messages=thread_messages
    )
    response_with_truncation = openai_client.beta.threads.runs.create(
        thread_id=thread_with_truncation.id,
        assistant_id=assistant_id,
        max_prompt_tokens=300,
    )

    assert response_without_truncation.status == "queued"
    assert response_with_truncation.status == "queued"

    # Check every 4 seconds, up to 5 times
    max_checks = 12
    check_interval = 2
    for _ in range(max_checks):
        time.sleep(check_interval)
        response_with_truncation = openai_client.beta.threads.runs.retrieve(
            thread_id=thread_with_truncation.id,
            run_id=response_with_truncation.id,
        )
        response_without_truncation = openai_client.beta.threads.runs.retrieve(
            thread_id=thread_without_truncation.id,
            run_id=response_without_truncation.id,
        )
        print(
            response_with_truncation.status, response_without_truncation.status
        )

        assert response_with_truncation.status not in ["failed"]
        assert response_without_truncation.status not in ["failed"]

        if response_with_truncation.status in [
            "incomplete",
            "completed",
        ] and response_without_truncation.status in [
            "incomplete",
            "completed",
        ]:
            break
    else:
        # If the loop completes without breaking, assert failure due to timeout
        assert False, "Run did not complete within the expected time."

    # verify without truncation works
    messages = openai_client.beta.threads.messages.list(
        thread_id=thread_without_truncation.id, order="desc"
    )
    assert len(messages.data) >= 2
    assert messages.data[0].role == "assistant"
    assert "mangosteen" in messages.data[0].content[0].text.value.lower()

    # verify with truncation works
    messages = openai_client.beta.threads.messages.list(
        thread_id=thread_with_truncation.id, order="desc"
    )
    assert len(messages.data) >= 2
    assert messages.data[0].role == "assistant"
    assert "mangosteen" not in messages.data[0].content[0].text.value.lower()
