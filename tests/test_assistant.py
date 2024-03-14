import pytest
from openai import OpenAI
from openai.pagination import SyncCursorPage
from openai.types.beta.assistant import Assistant, ToolCodeInterpreter
from datetime import datetime
import os

api_key = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else None


@pytest.fixture
def openai_client():
    return OpenAI(
        base_url="http://localhost:8000",
        api_key=api_key,
    )


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    openai_client = OpenAI(
        base_url="http://localhost:8000",
    )

    def remove_all_assistants():
        for assistant in openai_client.beta.assistants.list().data:
            openai_client.beta.assistants.delete(assistant.id)

    request.addfinalizer(remove_all_assistants)


# /assistants POST
@pytest.mark.dependency()
def test_create_assistant(openai_client: OpenAI):
    response = openai_client.beta.assistants.create(
        instructions="You are an AI designed to provide examples.",
        name="Example Assistant",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4",
        metadata={"str": "string", "int": 1, "bool": True, "list": [1, 2, 3]},
    )
    assert isinstance(response, Assistant)
    assert response.id is not None
    assert response.created_at is not None
    assert (
        response.instructions == "You are an AI designed to provide examples."
    )
    assert response.name == "Example Assistant"
    assert isinstance(response.tools[0], ToolCodeInterpreter)
    assert response.model == "gpt-4"
    assert response.metadata == {
        "str": "string",
        "int": 1,
        "bool": True,
        "list": [1, 2, 3],
    }


# /assistants GET
@pytest.mark.dependency(depends=["test_create_assistant"])
def test_list_assistants_after_creation(openai_client: OpenAI):
    response = openai_client.beta.assistants.list()
    assert isinstance(response, SyncCursorPage)
    assert len(response.data) > 0
    assert all(isinstance(item, Assistant) for item in response.data)


# /assistants GET
@pytest.mark.dependency(depends=["test_create_assistant"])
def test_list_assistants_limit(openai_client: OpenAI):
    limit = 1
    response = openai_client.beta.assistants.list(limit=limit)
    assert isinstance(response, SyncCursorPage)
    assert len(response.data) <= limit
    assert all(isinstance(item, Assistant) for item in response.data)


# /assistants GET
@pytest.mark.dependency(depends=["test_create_assistant"])
def test_list_assistants_order(openai_client: OpenAI):
    response_desc = openai_client.beta.assistants.list(order="desc")
    response_asc = openai_client.beta.assistants.list(order="asc")
    assert isinstance(response_desc, SyncCursorPage) and isinstance(
        response_asc, SyncCursorPage
    )
    assert len(response_desc.data) > 0 and len(response_asc.data) > 0
    desc_first_created_at = response_desc.data[0].created_at
    asc_first_created_at = response_asc.data[0].created_at
    assert (
        desc_first_created_at >= asc_first_created_at
    ), "Ordering does not match expected results"


# /assistants/{assistant_id} GET
@pytest.mark.dependency(depends=["test_create_assistant"])
def test_get_assistant(openai_client: OpenAI):
    # Assuming "test_create_assistant" creates an assistant and returns its ID
    template = {
        "model": "gpt-4",
        "name": "Example Assistant",
    }
    new_assistant = openai_client.beta.assistants.create(**template)

    response = openai_client.beta.assistants.retrieve(new_assistant.id)

    # Validate the response structure and data
    assert isinstance(response, Assistant)
    assert response.id == new_assistant.id
    assert response.model == template["model"]
    assert response.name == template["name"]
    assert response.object == "assistant"
    assert isinstance(response.created_at, int)
    assert datetime.utcfromtimestamp(
        response.created_at
    )  # Checks if `created_at` is a valid timestamp"


# /assistants/{assistant_id} POST
@pytest.mark.dependency(depends=["test_create_assistant"])
def test_modify_assistant(openai_client: OpenAI):
    template = {
        "model": "gpt-4",
        "name": "Example Assistant",
        "instructions": "You are an AI designed to provide examples.",
        "metadata": {"str": "string", "int": 1, "list": [1, 2, 3]},
    }
    new_assistant = openai_client.beta.assistants.create(**template)

    updated_template = {
        "instructions": "Updated instructions for the assistant.",
        "tools": [{"type": "code_interpreter"}],
        "metadata": {**template["metadata"], "bool": True},
    }
    # Perform the update operation
    response = openai_client.beta.assistants.update(
        new_assistant.id,
        **updated_template,
    )

    # Verify the response
    assert isinstance(response, Assistant)
    assert response.id == new_assistant.id
    assert response.instructions == updated_template["instructions"]
    assert isinstance(response.tools[0], ToolCodeInterpreter)
    assert response.name == template["name"]
    assert response.metadata["str"] == updated_template["metadata"]["str"]
    assert response.metadata["bool"] == updated_template["metadata"]["bool"]


@pytest.mark.dependency(depends=["test_create_assistant"])
def test_delete_assistant(openai_client: OpenAI):
    # Assuming an assistant has been created in a prior test and its ID is retrievable
    template = {
        "model": "gpt-4",
        "name": "Example Assistant",
        "instructions": "You are an AI designed to provide examples.",
        "metadata": {"str": "string", "int": 1, "list": [1, 2, 3]},
    }
    new_assistant = openai_client.beta.assistants.create(**template)

    # Perform the delete operation
    response = openai_client.beta.assistants.delete(new_assistant.id)

    # Verify the deletion response
    assert response.id == new_assistant.id
    assert response.deleted is True
    assert response.object == "assistant.deleted"

    # try and retrieve the assistant again
    try:
        openai_client.beta.assistants.retrieve(new_assistant.id)
    except Exception as e:
        assert e.status_code == 404
        assert "Assistant not found" in str(e)
    else:
        raise AssertionError("Assistant was not deleted")
