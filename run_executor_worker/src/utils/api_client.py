# api_client.py
import os
from openai import OpenAI  # Assuming OpenAI is the base client library
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionToolParam,
    ChatCompletionMessageParam,
    ChatCompletionToolChoiceOptionParam,
)
from openai.types.chat.chat_completion import Choice
import instructor
from uuid import uuid4
import time
from openai._client import resources
from pydantic import BaseModel, create_model, Field
from typing import List, Optional, Type, Any


class APIClient(OpenAI):
    def __init__(self, api_key=None, base_url=None):
        api_key = api_key or os.getenv("FC_API_KEY")
        base_url = base_url or os.getenv("FC_API_URL")
        super().__init__(api_key=api_key)

        self.instructor_client: Optional[instructor.Instructor] = None

        if api_key == 'ollama':
            self.instructor_client = instructor.from_openai(
                client=self,
                mode=instructor.Mode.JSON,
            )
        self.chat = self.Chat(self)

    class Chat(resources.Chat):
        def __init__(self, client: 'APIClient'):
            super().__init__(client)
            self.completions = self.Completions(client)

        class Completions(resources.chat.completions.Completions):
            def __init__(self, client: 'APIClient'):
                self.client = client
                super().__init__(client)

            def create(
                self,
                model: str,
                messages: list,
                tools: List[ChatCompletionToolParam],
                max_tokens: int,
                tool_choice: ChatCompletionToolChoiceOptionParam,
            ) -> ChatCompletion:
                print("In create")
                if self.client.api_key == 'ollama':
                    print("In instructor")
                    res = self.client._instructor_chat_completion(
                        model, messages, tools, max_tokens, tool_choice
                    )
                    print(res)
                    return res
                else:
                    return super().create(
                        model=model,
                        messages=messages,
                        tools=tools,
                        max_tokens=max_tokens,
                        tool_choice=tool_choice,
                    )

    def _instructor_chat_completion(
        self,
        model: str,
        messages: List[ChatCompletionMessageParam],
        tools: List[ChatCompletionToolParam],
        max_tokens: int,
        tool_choice: ChatCompletionToolChoiceOptionParam,
    ) -> ChatCompletion:
        # Apply necessary transformations here
        tool = tools[0]
        DynamicModel = self._function_signature_to_pydantic_model(tool)
        assert isinstance(self.instructor_client, instructor.Instructor)
        messages = self._append_tool_description_to_messages(tool, messages)
        instructor_res = self.instructor_client.chat.completions.create(
            model=model,
            messages=messages,
            response_model=DynamicModel,
            max_retries=3,
        )
        chat_completion = self._create_chat_completion(
            instructor_res, tool, model
        )
        return chat_completion

    def _append_tool_description_to_messages(
        self,
        tool: ChatCompletionToolParam,
        messages: List[ChatCompletionMessageParam],
    ) -> List[ChatCompletionMessageParam]:
        tool_description = tool.get('function', {}).get('description', "")
        new_messages = messages.copy()
        if len(new_messages) and 'content' in new_messages[0]:
            new_messages[0][
                'content'
            ] = f"{new_messages[0]['content']}\n\ntool_description='''{tool_description}'''"  # noqa
        return messages

    def _create_chat_completion(
        self, instructor_res: Any, tool: ChatCompletionToolParam, model: str
    ) -> ChatCompletion:
        choice = {
            "finish_reason": "stop",
            "index": 0,
            "logprobs": None,
            "message": {
                "role": "assistant",
                "content": None,
                "function_call": None,
                "tool_calls": [
                    {
                        "id": f"call_{str(uuid4())}",
                        "function": {
                            "name": tool.get('function', {}).get('name'),
                            "arguments": instructor_res.model_dump_json(),
                        },
                        "type": "function",
                    }
                ],
            },
        }

        return ChatCompletion(
            id=str(uuid4()),
            object="chat.completion",
            created=int(time.time()),
            model=model,
            choices=[Choice(**choice)],
        )

    def _transform_messages(self, messages: list) -> list:
        # Implement your message transformations here
        return messages

    def _transform_tool(self, tools: list) -> list:
        # Implement your tool transformations here
        return tools

    def _function_signature_to_pydantic_model(
        self, fs: ChatCompletionToolParam
    ) -> Type[BaseModel]:
        function = fs.get('function', {})
        function_params = function.get('parameters', {})

        properties = function_params.get('properties', {})
        required_fields = function_params.get('required', [])

        fields = {}
        for field_name, field_info in properties.items():
            field_type = field_info.get('type')
            description = field_info.get('description', "")
            enum = field_info.get('enum', None)

            if field_type == 'string':
                field_type = str
            elif field_type == 'integer':
                field_type = int
            elif field_type == 'boolean':
                field_type = bool
            elif field_type == 'array':
                items_type = field_info.get('items', {}).get('type')
                if items_type == 'string':
                    field_type = List[str]
                else:
                    raise ValueError(f"Unsupported items type: {items_type}")
            else:
                raise ValueError(f"Unsupported field type: {field_type}")

            field_args = {}
            if description:
                field_args['description'] = description
            if enum:
                field_args['enum'] = enum

            if field_name in required_fields:
                fields[field_name] = (field_type, Field(..., **field_args))
            else:
                fields[field_name] = (
                    Optional[field_type],
                    Field(None, **field_args),
                )

        model_name = function.get('name', 'DynamicModel')

        model = create_model(model_name, **fields)

        return model
