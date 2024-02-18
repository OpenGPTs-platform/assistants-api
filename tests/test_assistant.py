import pytest
from openai import OpenAI
from openai.pagination import SyncCursorPage
from openai.types.beta.assistant import Assistant, ToolCodeInterpreter


@pytest.fixture
def openai_client():
    # Replace "your_api_key_here" with your actual OpenAI API key
    return OpenAI(
        base_url="http://localhost:8000",
    )


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


@pytest.mark.dependency(depends=["test_create_assistant"])
def test_list_assistants_after_creation(openai_client: OpenAI):
    response = openai_client.beta.assistants.list()
    assert isinstance(response, SyncCursorPage)
    assert len(response.data) > 0
    assert all(isinstance(item, Assistant) for item in response.data)


@pytest.mark.dependency(depends=["test_create_assistant"])
def test_list_assistants_limit(openai_client: OpenAI):
    limit = 1
    response = openai_client.beta.assistants.list(limit=limit)
    assert isinstance(response, SyncCursorPage)
    assert len(response.data) <= limit
    assert all(isinstance(item, Assistant) for item in response.data)


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
