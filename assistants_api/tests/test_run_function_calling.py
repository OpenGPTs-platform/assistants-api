import pytest
from openai import OpenAI


from openai.types.beta.function_tool import FunctionTool
from openai.types.beta.threads.required_action_function_tool_call import (
    RequiredActionFunctionToolCall,
)
from openai.types.beta.threads.runs.run_step import RunStep
from openai.types.beta.threads.runs.tool_calls_step_details import (
    ToolCallsStepDetails,
)
from openai.types.beta.threads.runs.message_creation_step_details import (
    MessageCreationStepDetails,
)

# from openai.types.beta.threads.runs import RunStep
import os
import json

api_key = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else None
use_openai = True if os.getenv("USE_OPENAI") else False
base_url = "http://localhost:8000"

current_dir = os.path.dirname(__file__)
code_reference_file_path = os.path.join(
    current_dir, '..', 'assets', 'code-reference.txt'
)


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
    response = openai_client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "What's the weather in San Francisco today?",  # noqa
            }
        ],
    )
    return response.id


get_current_temperature_sig = {
    "name": "get_current_temperature",
    "description": "Get the current temperature for a specific location",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state, e.g., San Francisco, CA",
            },
            "unit": {
                "type": "string",
                "enum": ["Celsius", "Fahrenheit"],
                "description": "The temperature unit to use. Infer this from the user's location.",  # noqa
            },
        },
        "required": ["location", "unit"],
    },
}


@pytest.fixture
def assistant_id(openai_client: OpenAI):
    response = openai_client.beta.assistants.create(
        name="Tool Assistant",
        model="gpt-3.5-turbo",
        tools=[
            {
                "type": "function",
                "function": get_current_temperature_sig,
            },
        ],
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
def test_create_asst_with_fc(openai_client: OpenAI):
    response = openai_client.beta.assistants.create(
        name="Tool Assistant",
        model="gpt-3.5-turbo",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_current_temperature",
                    "description": "Get the current temperature for a specific location",  # noqa
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g., San Francisco, CA",  # noqa
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["Celsius", "Fahrenheit"],
                                "description": "The temperature unit to use. Infer this from the user's location.",  # noqa
                            },
                        },
                        "required": ["location", "unit"],
                    },
                },
            },
        ],
    )
    asst = openai_client.beta.assistants.retrieve(assistant_id=response.id)
    assert asst.tools[0].type == "function"
    assert isinstance(asst.tools[0], FunctionTool)
    assert asst.tools[0].function.name == get_current_temperature_sig["name"]


@pytest.mark.dependency(depends=["test_create_asst_with_fc"])
def test_execute_fc_run_to_tool_call(
    openai_client: OpenAI, assistant_id: str, thread_id: str
):
    run = openai_client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    assert run.status == "requires_action"
    assert isinstance(
        run.required_action.submit_tool_outputs.tool_calls[0],
        RequiredActionFunctionToolCall,
    )
    assert (
        run.required_action.submit_tool_outputs.tool_calls[0].function.name
        == "get_current_temperature"
    )
    json_args = json.loads(
        run.required_action.submit_tool_outputs.tool_calls[
            0
        ].function.arguments
    )
    for param in get_current_temperature_sig["parameters"]["properties"]:
        assert param in json_args

    # test run_steps
    run_steps = openai_client.beta.threads.runs.steps.list(
        run_id=run.id,
        thread_id=thread_id,
    )
    assert len(run_steps.data) >= 1
    latest_step: RunStep = run_steps.data[0]
    assert latest_step.status == "in_progress"
    assert isinstance(latest_step.step_details, ToolCallsStepDetails)


# @pytest.mark.dependency(depends=["test_execute_fc_run_to_tool_call"])
def test_execute_fc_to_submit_tool_output(
    openai_client: OpenAI, assistant_id: str, thread_id: str
):
    run = openai_client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    assert run.status == "requires_action"

    tool_outputs = [
        {
            "tool_call_id": run.required_action.submit_tool_outputs.tool_calls[
                0
            ].id,
            "output": "57",
        }
    ]

    run = openai_client.beta.threads.runs.submit_tool_outputs(
        thread_id=thread_id, run_id=run.id, tool_outputs=tool_outputs
    )

    assert run.status == "queued"
    assert run.required_action is None

    run_steps = openai_client.beta.threads.runs.steps.list(
        run_id=run.id,
        thread_id=thread_id,
    )
    tool_call_step: RunStep = run_steps.data[0]
    assert tool_call_step.status == "completed"
    assert isinstance(tool_call_step.step_details, ToolCallsStepDetails)
    assert tool_call_step.step_details.tool_calls[0].function.output == "57"


# @pytest.mark.dependency(depends=["test_execute_fc_to_submit_tool_output"])
def test_execute_full_fc_run(
    openai_client: OpenAI, assistant_id: str, thread_id: str
):
    run = openai_client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    assert run.status == "requires_action"

    tool_outputs = [
        {
            "tool_call_id": run.required_action.submit_tool_outputs.tool_calls[
                0
            ].id,
            "output": "57",
        }
    ]

    run = openai_client.beta.threads.runs.submit_tool_outputs_and_poll(
        thread_id=thread_id, run_id=run.id, tool_outputs=tool_outputs
    )

    assert run.status == "completed"

    run_steps = openai_client.beta.threads.runs.steps.list(
        run_id=run.id,
        thread_id=thread_id,
    )
    assert len(run_steps.data) > 1
    message_step: RunStep = run_steps.data[0]
    tool_call_step: RunStep = run_steps.data[1]
    assert tool_call_step.status == "completed"
    assert isinstance(message_step.step_details, MessageCreationStepDetails)
    assert isinstance(tool_call_step.step_details, ToolCallsStepDetails)


# example run response
#  {
#   "id": "run_NVSMGgDKzgCgwEF7Zzdz8k6y",
#   "assistant_id": "asst_E1kTZTy6CYfC6ORcNjzOiy7m",
#   "cancelled_at": null,
#   "completed_at": null,
#   "created_at": 1717623841,
#   "expires_at": 1717624441,
#   "failed_at": null,
#   "incomplete_details": null,
#   "instructions": "You are a weather bot",
#   "last_error": null,
#   "max_completion_tokens": null,
#   "max_prompt_tokens": null,
#   "metadata": {},
#   "model": "gpt-3.5-turbo",
#   "object": "thread.run",
#   "required_action": {
#     "submit_tool_outputs": {
#       "tool_calls": [
#         {
#           "id": "call_jQZJcllUJddBMgrVoG7vCz5T",
#           "function": {
#             "arguments": "{\"location\":\"San Francisco, CA\",\"unit\":\"Celsius\"}",
#             "name": "get_current_temperature"
#           },
#           "type": "function"
#         }
#       ]
#     },
#     "type": "submit_tool_outputs"
#   },
#   "response_format": "auto",
#   "started_at": 1717623841,
#   "status": "requires_action",
#   "thread_id": "thread_FpjpMLPArzthx9OJEVCVy6s0",
#   "tool_choice": "auto",
#   "tools": [
#     {
#       "function": {
#         "name": "get_current_temperature",
#         "description": "Get the current temperature for a specific location",
#         "parameters": {
#           "type": "object",
#           "properties": {
#             "location": {
#               "type": "string",
#               "description": "The city and state, e.g., San Francisco, CA"
#             },
#             "unit": {
#               "type": "string",
#               "enum": [
#                 "Celsius",
#                 "Fahrenheit"
#               ],
#               "description": "The temperature unit to use. Infer this from the user's location." # noqa
#             }
#           },
#           "required": [
#             "location",
#             "unit"
#           ]
#         }
#       },
#       "type": "function"
#     }
#   ],
#   "truncation_strategy": {
#     "type": "auto",
#     "last_messages": null
#   },
#   "usage": null,
#   "temperature": 1.0,
#   "top_p": 1.0,
#   "tool_resources": {}
# }


# Example run step response
# {
#     "id": "step_I1VoVmk6xgaRRSmwUmK4jeqS",
#     "assistant_id": "asst_n9OeD7LxXHOAqwntzE4GQA0q",
#     "cancelled_at": null,
#     "completed_at": null,
#     "created_at": 1717650165,
#     "expired_at": null,
#     "failed_at": null,
#     "last_error": null,
#     "metadata": null,
#     "object": "thread.run.step",
#     "run_id": "run_r5BUD3mknzLHNjuKaHKiGI9r",
#     "status": "in_progress",
#     "step_details": {
#     "tool_calls": [
#         {
#         "id": "call_9GzmopsuKPVfmHWGqNotTDu5",
#         "function": {
#             "arguments": "{\"location\":\"San Francisco\",\"unit\":\"Celsius\"}",
#             "name": "get_current_temperature",
#             "output": null
#         },
#         "type": "function"
#         }
#     ],
#     "type": "tool_calls"
#     },
#     "thread_id": "thread_8vqZzH15vzPSI5dGKS1Nx28e",
#     "type": "tool_calls",
#     "usage": null,
#     "expires_at": 1717650764
# }
