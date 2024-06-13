from enum import Enum
from typing import List
from openai.types.beta.web_retrieval_tool import WebRetrievalTool
from openai.types.beta.assistant_tool import AssistantTool
from openai.types.beta.file_search_tool import FileSearchTool
from openai.types.beta.code_interpreter_tool import CodeInterpreterTool
from openai.types.beta.function_tool import FunctionTool
from pydantic import BaseModel


class Actions(Enum):
    # function, retrieval, code_interpreter, text_generation, completion
    FUNCTION = "function"
    WEB_RETRIEVAL = "web_retrieval"
    FILE_SEARCH = "file_search"
    CODE_INTERPRETER = "code_interpreter"
    TEXT_GENERATION = "text_generation"
    COMPLETION = "completion"
    FAILURE = "failure"


class ActionItem(BaseModel):
    type: str
    description: str


def actions_to_map(actions: List[str]) -> dict[str, ActionItem]:
    """
    Converts a list of AssistantTool objects to a dictionary.
    """
    actions_map = {}
    for action in actions:
        if action == Actions.TEXT_GENERATION.value:
            actions_map[action] = ActionItem(
                type=Actions.TEXT_GENERATION.value,
                description="Communicate to the user either to summarize or express the next tasks to be executed.",  # noqa
            )
        elif action == Actions.COMPLETION.value:
            actions_map[action] = ActionItem(
                type=Actions.COMPLETION.value,
                description="Finish the process, generate the final answer",
            )
    return actions_map


def tools_to_map(
    tools: List[AssistantTool], web_retrieval_description: str
) -> dict[str, ActionItem]:
    """
    Converts a list of AssistantTool objects to a dictionary.
    """
    tools_map: dict[str, ActionItem] = {}
    for tool in tools:
        if isinstance(tool, FunctionTool):
            if not tools_map.get(tool.type):
                tools_map[tool.type] = ActionItem(
                    type=tool.type,
                    description="Function calls available to you are: ",
                )
            tools_map[tool.type].description += f"{tool.function.model_dump()}"

        elif isinstance(tool, FileSearchTool):
            tools_map[tool.type] = ActionItem(
                type=tool.type,
                description="Retrieves information from files provided.",
            )
        elif isinstance(tool, WebRetrievalTool):
            tools_map[tool.type] = ActionItem(
                type=tool.type,
                description=web_retrieval_description,
            )
        elif isinstance(tool, CodeInterpreterTool):
            tools_map[tool.type] = ActionItem(
                type=tool.type,
                description="Interprets and executes code.",
            )
    return tools_map


text_generation_tool = ActionItem(
    type="text_generation",
    description="General text response.",
)

completion_tool = ActionItem(
    type="completion",
    description="Completes the task.",
)
