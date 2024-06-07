from constants import PromptKeys
from utils.context import context_trimmer
from utils.openai_clients import (
    fc_client,
    litellm_client,
    ChatCompletion,
)
import os
from run_executor import main
import json


class RouterAgent:
    def __init__(
        self,
        execute_run_class: "main.ExecuteRun",
    ):
        self.execute_run_class = execute_run_class

    def compose_system_prompt(self) -> str:
        return f"""USER_INSTRUCTION:```{self.execute_run_class.assistant.instructions}```"""  # noqa

    # TODO: add assistant and base tools off of assistant
    def generate(
        self,
    ) -> str:
        """
        Generates a response based on the chat history and role instructions.

        Args:
            tools (dict): The tools available to the agent.
            paginated_messages (SyncCursorPage[Message]): The chat history.

        Returns:
            str: It either returns `{PromptKeys.TRANSITION.value}` or a generated response.
        """  # noqa

        # Build messages to send to the model
        cleaned_messages = []
        for message in self.execute_run_class.messages.data:
            cleaned_messages.append(
                {
                    "role": message.role,
                    "content": message.content[0].text.value,
                }
            )

        trimmed_messages = cleaned_messages
        if self.execute_run_class.run.max_prompt_tokens:
            trimmed_messages = context_trimmer(
                item_list=cleaned_messages,
                max_length=self.execute_run_class.run.max_prompt_tokens * 3,
                trim_start=True,
            )

        messages = [
            {
                "role": "system",
                "content": self.compose_system_prompt(),
            }
        ] + trimmed_messages
        try:
            tools_list = "\n".join(
                [
                    f"- {tool.type}: {tool.description}"
                    for _, tool in self.execute_run_class.tools_map.items()
                ]
            )
            tools_needed_response: ChatCompletion = fc_client.chat.completions.create(
                model=os.getenv("FC_MODEL"),
                messages=messages,
                tools=[
                    {
                        'type': 'function',
                        'function': {
                            'name': 'determine_tools_needed',
                            'description': f"""The following tools are available to you:```{tools_list}```
Determine if those tools are needed to respond to the user's message.""",  # noqa
                            'parameters': {
                                'type': 'object',
                                'properties': {
                                    'tools_needed': {
                                        'type': 'boolean',
                                        'description': 'Are the tools necessary.',  # noqa
                                    }
                                },
                                'required': ['tools_needed'],
                            },
                        },
                    }
                ],
                max_tokens=28,
                tool_choice={
                    "type": "function",
                    "function": {"name": "determine_tools_needed"},
                },
            )

            # parse the response to get the arguments
            print("\n\nTool needed response:\n", tools_needed_response)
            tools_needed_args = json.loads(
                tools_needed_response.choices[0]
                .message.tool_calls[0]
                .function.arguments
            )
            if tools_needed_args["tools_needed"]:
                return PromptKeys.TRANSITION.value
            else:
                pass
        except Exception as e:
            print("Error with tools_needed_response:", e)

        response = litellm_client.chat.completions.create(
            model=os.getenv("LITELLM_MODEL"),
            messages=messages,
            max_tokens=2000,
        )

        print("GENERATION: ", response.choices[0].message.content)

        return response.choices[0].message.content
