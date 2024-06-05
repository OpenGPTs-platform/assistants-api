from openai import OpenAI
from openai.types.chat import (
    completion_create_params,
    chat_completion_tool_choice_option_param,
    ChatCompletionMessageParam,
)
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from openai._types import NOT_GIVEN
from typing import Iterable, Union, Optional, Dict, List, Literal

import requests
import os
import json
from dateutil.parser import isoparse
import re

# raise error if LITELLM_API_URL or ASSISTANTS_API_URL or FC_API_URL is not set
if not os.getenv("LITELLM_API_URL"):
    # print a warning message suggesting that it is defaulting to openai inference
    print("LITELLM_API_URL is not set. Defaulting to OpenAI inference.")
if not os.getenv("ASSISTANTS_API_URL"):
    raise ValueError("ASSISTANTS_API_URL is not set")
if not os.getenv("FC_API_URL"):
    raise ValueError("FC_API_URL is not set")

litellm_client = None
if os.getenv("LITELLM_API_URL"):
    litellm_client = OpenAI(
        api_key=os.getenv("LITELLM_API_KEY"),
        base_url=os.getenv("LITELLM_API_URL", None),
    )
else:
    litellm_client = OpenAI(
        api_key=os.getenv("LITELLM_API_KEY"),
    )

assistants_client = OpenAI(
    base_url=os.getenv("ASSISTANTS_API_URL"),
)


def chat_completion_inputs_to_prompt(
    messages: Iterable[ChatCompletionMessageParam],
    tools: Iterable[completion_create_params.ChatCompletionToolParam],
) -> str:
    # Convert messages to prompt format
    formatted_prompt = "<s>"
    # count the amount of non assistant messages at the end
    final_user_messages = 0
    for message in reversed(messages):
        if message["role"] == "user" or message["role"] == "system":
            final_user_messages -= 1
        else:
            break
    for idx, message in enumerate(messages[:final_user_messages]):
        if message["role"] == "user" or message["role"] == "system":
            if idx != 0 and (
                messages[idx - 1]["role"] == "user"
                or messages[idx - 1]["role"] == "system"
            ):
                formatted_prompt += f" {message['content']}"
            else:
                if idx != 0:
                    formatted_prompt += "<s>"
                formatted_prompt += f"[INST] {message['content']}"
        elif message["role"] == "assistant":
            formatted_prompt += f"[/INST]{message['content']}</s>"
        else:
            raise ValueError(f"Invalid message type: {type(message)}")

    # Convert tools to prompt format
    formatted_prompt += (
        f"[AVAILABLE_TOOLS] {json.dumps(tools)}[/AVAILABLE_TOOLS]"
    )
    for idx, message in enumerate(messages[final_user_messages:]):
        if idx != 0 and (
            messages[idx - 1]["role"] == "user"
            or messages[idx - 1]["role"] == "system"
        ):
            formatted_prompt += f" {message['content']}"
        else:
            formatted_prompt += f"[INST] {message['content']}"
    formatted_prompt += "[/INST]"

    return formatted_prompt


def find_and_parse_json_objects(text):
    # Regular expression to find JSON arrays in the string
    json_pattern = re.compile(r'\[.*?\]')
    json_objects = []

    match = json_pattern.search(text)
    if match:
        json_str = match.group()
        try:
            json_obj = json.loads(json_str)
            json_objects.append(json_obj)
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: {e} with string: {json_str}")

    return json_objects


def fc_chat_completions_create(
    messages: Iterable[ChatCompletionMessageParam],
    model: Union[str, completion_create_params.ChatModel],
    function_call: completion_create_params.FunctionCall = NOT_GIVEN,
    functions: Iterable[completion_create_params.Function] = NOT_GIVEN,
    logit_bias: Optional[Dict[str, int]] = NOT_GIVEN,
    logprobs: Optional[bool] = NOT_GIVEN,
    max_tokens: Optional[int] = NOT_GIVEN,
    n: Optional[int] = NOT_GIVEN,
    presence_penalty: Optional[float] = NOT_GIVEN,
    response_format: completion_create_params.ResponseFormat = NOT_GIVEN,
    seed: Optional[int] = NOT_GIVEN,
    stop: Union[Optional[str], List[str]] = NOT_GIVEN,
    stream: Optional[Literal[False]] = NOT_GIVEN,
    stream_options: Optional[
        completion_create_params.ChatCompletionStreamOptionsParam
    ] = NOT_GIVEN,
    temperature: Optional[float] = NOT_GIVEN,
    tool_choice: chat_completion_tool_choice_option_param.ChatCompletionToolChoiceOptionParam = NOT_GIVEN,  # noqa
    tools: Iterable[
        completion_create_params.ChatCompletionToolParam
    ] = NOT_GIVEN,
    top_logprobs: Optional[int] = NOT_GIVEN,
    top_p: Optional[float] = NOT_GIVEN,
    user: str = NOT_GIVEN,
    extra_headers: Dict[str, str] = None,
    extra_query: Dict[str, str] = None,
    extra_body: Dict[str, Union[str, int, float]] = None,
    timeout: float = None,
) -> ChatCompletion:
    function_signature_name = tools[0]["function"]['name']
    messages = messages + [
        {
            "role": "user",
            "content": f" YOU MUST REPLY STRICTLY FOLLOWING THE SPECIFIC JSON SCHEMA FORMAT FROM {function_signature_name} DO NOT RESPOND WITH ANYTHING ELSE.",  # noqa
        }
    ]
    # transform inputs to prompt
    prompt = chat_completion_inputs_to_prompt(messages, tools)
    # make request to mistral ollama raw endpoint
    body = {
        "model": os.getenv("FC_MODEL"),
        "prompt": prompt,
        "raw": True,
        "stream": False,
    }
    if max_tokens:
        body["options"] = {"num_predict": max_tokens}
    response = requests.post(
        os.getenv('FC_API_URL'),
        headers={
            "Authorization": f"Bearer {os.getenv('FC_API_KEY')}",
            "Content-Type": "application/json",
        },
        json=body,
    )
    response.raise_for_status()
    json_response = response.json()

    created_at_str = json_response["created_at"]
    created_at = int(isoparse(created_at_str).timestamp())

    text_response = json_response["response"]
    print("\n\nFunction calling response:\n", text_response)
    text_response_postfix = text_response.split("\n\n")[0]
    text_response_postfix = text_response_postfix.replace("'", '"')

    json_text_response = find_and_parse_json_objects(text_response_postfix)[0]

    chat_completion = ChatCompletion(
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            id="toolcall-1234567890abcdefg",
                            function=Function(
                                arguments=json.dumps(
                                    json_text_response[0]["arguments"]
                                ),
                                name=json_text_response[0]["name"],
                            ),
                            type="function",
                        )
                    ],
                    role="assistant",
                ),
            )
        ],
        created=created_at,
        id="chatcmpl-1234567890abcdefg",
        model=model,
        object="chat.completion",
    )
    return chat_completion
