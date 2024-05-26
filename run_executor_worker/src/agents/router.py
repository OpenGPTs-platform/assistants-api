from constants import PromptKeys
from utils.context import context_trimmer
from utils.openai_clients import litellm_client
import os
from run_executor import main


class RouterAgent:
    def __init__(
        self,
        execute_run_class: "main.ExecuteRun",
    ):
        self.execute_run_class = execute_run_class

        self.role_instructions = f"""Your role is to determine whether tools will be absolutely necessary to complete the task at hand.
If tools are not necessary, generate a normal response.
Otherwise if you will need to use tools, respond with '{PromptKeys.TRANSITION.value}'."""  # noqa

    def compose_system_prompt(self) -> str:
        tools_list = "\n".join(
            [
                f"- {tool.type}: {tool.description}"
                for _, tool in self.execute_run_class.tools_map.items()
            ]
        )
        return f"""SYSTEM INSTRUCTION
```{self.role_instructions}

The tools available to you are:
{tools_list}```

ADDITIONAL INSTRUCTION
```{self.execute_run_class.assistant.instructions}```"""

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
        messages = [
            {
                "role": "system",
                "content": self.compose_system_prompt(),
            }
        ]
        print("\n\nSYSTEM PROMPT: ", messages[0]["content"])
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
        # print trimmed messages length vs cleaned messages length
        messages += trimmed_messages

        response = litellm_client.chat.completions.create(
            model=os.getenv("LITELLM_MODEL"),
            messages=messages,
            max_tokens=500,
        )

        print("GENERATION: ", response.choices[0].message.content)
        if PromptKeys.TRANSITION.value in response.choices[0].message.content:
            return PromptKeys.TRANSITION.value
        else:
            return response.choices[0].message.content
