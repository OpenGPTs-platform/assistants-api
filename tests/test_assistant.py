import pytest
from openai import OpenAI
from openai.types.beta.assistant import Assistant, ToolCodeInterpreter


@pytest.fixture
def openai_client():
    # Replace "your_api_key_here" with your actual OpenAI API key
    return OpenAI(
        base_url="http://localhost:8000",
    )


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
    # assert that response.tools[0] is of type ToolCodeInterpreter
    assert isinstance(response.tools[0], ToolCodeInterpreter)
    assert response.model == "gpt-4"
    assert response.metadata == {
        "str": "string",
        "int": 1,
        "bool": True,
        "list": [1, 2, 3],
    }
