from enum import Enum
from typing import Optional, List
from openai.types.beta.threads.message import Message
from openai.pagination import SyncCursorPage
from pydantic import BaseModel
from utils.context import context_trimmer
from utils.tools import ActionItem, Actions, actions_to_map, tools_to_map
from utils.ops_api_handler import create_message_runstep
from actions import web_retrieval, file_search, function_calling_tool
from utils.openai_clients import (
    litellm_client,
    assistants_client,
    fc_client,
    ChatCompletion,
)
from data_models import run
import os
from openai.types.beta import Assistant
import json


class ReactStepType(str, Enum):
    ACTION = "Action"
    THOUGHT = "Thought"
    OBSERVATION = "Observation"
    QUESTION = "Question"
    FINAL_ANSWER = "Final Answer"


class ReactStep(BaseModel):
    step_type: ReactStepType
    content: str


class CoALA:
    def __init__(
        self,
        run_id: str,
        thread_id: str,
        assistant_id: str,
        verbose: bool = True,
    ):
        self.verbose = verbose

        self.run_id = run_id
        self.thread_id = thread_id
        self.assistant_id = assistant_id

        self.run: Optional[run.Run] = None
        self.assistant: Optional[Assistant] = None
        self.messages: SyncCursorPage[Message] = SyncCursorPage(
            data=[]
        )  # in ascending order
        self.runsteps: SyncCursorPage[run.RunStep] = SyncCursorPage(
            data=[]
        )  # in ascending order

        self.tool_items: dict[str, ActionItem] = {}
        self.action_items = actions_to_map(
            [
                Actions.TEXT_GENERATION.value,
                Actions.COMPLETION.value,
            ]
        )

        self.react_steps: List[ReactStep] = []

    def generate_question(self) -> ReactStep:
        coala_prompt = self.compose_coala_prompt()
        tools_list_prompt = "[" + ", ".join(list(self.tool_items.keys())) + "]"
        orchestrator_instruction = f"""Summarize the objective of the latest message using any conversation context as needed.
Ensure that the summary includes all relevant details needed for effective use of the following tools: {tools_list_prompt}.
You must always begin with "{ReactStepType.QUESTION.value}: " ."""  # noqa

        # message history (episodic memory)
        generator_messages = [
            {"role": message.role, "content": message.content[0].text.value}
            for message in self.messages.data
        ]
        # final instruction to generate question
        generator_messages.append(
            {
                "role": "user",
                "content": orchestrator_instruction + coala_prompt,
            }
        )
        response = litellm_client.chat.completions.create(
            model=os.getenv("LITELLM_MODEL"),
            messages=generator_messages,
            max_tokens=500,
        )
        content = response.choices[0].message.content
        stripped_content = self.strip_generated_react_step(
            content,
            ReactStepType.QUESTION.value + ":",
            ReactStepType.THOUGHT.value,
        )

        react_step = ReactStep(
            step_type=ReactStepType.QUESTION, content=stripped_content
        )
        self.react_steps.append(react_step)

        return react_step

    def generate_thought(self) -> ReactStep:
        coala_prompt = self.compose_coala_prompt()
        orchestrator_instruction = f"""Your role is to think (outloud) about what to do next.
You must always begin with "{ReactStepType.THOUGHT.value}: " ."""  # noqa
        generator_messages = [
            {
                "role": "user",
                "content": orchestrator_instruction + coala_prompt,
            }
        ]
        response = litellm_client.chat.completions.create(
            model=os.getenv("LITELLM_MODEL"),
            messages=generator_messages,
            max_tokens=500,
        )
        content = response.choices[0].message.content
        stripped_content = self.strip_generated_react_step(
            content,
            ReactStepType.THOUGHT.value + ":",
            ReactStepType.ACTION.value,
        )

        # save run step
        create_message_runstep(
            self.thread_id, self.run_id, self.assistant_id, stripped_content
        )

        react_step = ReactStep(
            step_type=ReactStepType.THOUGHT, content=stripped_content
        )
        self.react_steps.append(react_step)

        return react_step

    def generate_action(
        self,
    ) -> ReactStep:
        coala_prompt = self.compose_coala_prompt(action_fc=True)

        generator_messages = [
            {
                "role": "user",
                "content": coala_prompt,
            }
        ]
        actions_prompt = "\n\n".join(
            f"- {tool.type} ({tool.description})"
            for _, tool in self.tool_items.items()
        )
        actions_list = list(self.tool_items.keys())

        response: ChatCompletion = fc_client.chat.completions.create(
            model=os.getenv("FC_MODEL"),
            messages=generator_messages,
            tools=[
                {
                    'type': 'function',
                    'function': {
                        'name': 'determine_next_action',
                        'description': f"""The actions are available to you:```{actions_prompt}```
Determine which action to perform next. You should only use an action once, DO NOT repeat actions nor functions.""",  # noqa
                        'parameters': {
                            'type': 'object',
                            'properties': {
                                'next_action': {
                                    'type': 'string',
                                    'enum': actions_list,
                                    'description': 'Next action to perform.',  # noqa
                                }
                            },
                            'required': ['next_action'],
                        },
                    },
                }
            ],
            max_tokens=35,
            tool_choice={
                "type": "function",
                "function": {"name": "determine_next_action"},
            },
        )
        print(
            "\n\nNext action response:\n",
            response.choices[0].message.tool_calls[0].function,
        )
        response_args = json.loads(
            response.choices[0].message.tool_calls[0].function.arguments
        )
        for key in self.tool_items.keys():
            if key == response_args["next_action"]:
                react_step = ReactStep(
                    step_type=ReactStepType.ACTION, content=Actions(key).value
                )
                self.react_steps.append(react_step)
                return react_step

        # raise error if no action is found
        raise ValueError(f"No action found in response: {response}")

    def execute_action(self, action: Actions) -> ReactStep:
        if action == Actions.COMPLETION:
            return self.generate_final_answer()
        elif action == Actions.FILE_SEARCH:
            retrieval_class = file_search.FileSearch(self)
            run_step = retrieval_class.generate()
            react_step = ReactStep(
                step_type=ReactStepType.OBSERVATION,
                content=json.dumps(
                    run_step.step_details.tool_calls[0].model_dump()
                ),
            )
            self.react_steps.append(react_step)
            return react_step
        elif action == Actions.WEB_RETRIEVAL:
            web_retrieval_class = web_retrieval.WebRetrieval(self)
            run_step = web_retrieval_class.generate()
            react_step = ReactStep(
                step_type=ReactStepType.OBSERVATION,
                content=json.dumps(
                    run_step.step_details.tool_calls[0].model_dump()
                ),
            )
            self.react_steps.append(react_step)
            return react_step
        elif action == Actions.FUNCTION:
            fct = function_calling_tool.FunctionCallingTool(self)
            run_step = fct.generate_tool_call()
            react_step = ReactStep(
                step_type=ReactStepType.OBSERVATION,
                content=json.dumps(
                    run_step.step_details.tool_calls[0].model_dump()
                ),
            )
            self.react_steps.append(react_step)

        else:
            raise ValueError(f"Action {action} not supported")

    def generate_final_answer(self) -> ReactStep:
        coala_prompt = self.compose_coala_prompt()
        orchestrator_instruction = f"""Your role is to provide the user with a single comprehensive "Final Answer" to conclude the run.
You must always begin with "{ReactStepType.FINAL_ANSWER.value}: " ."""  # noqa
        generator_messages = [
            {
                "role": "user",
                "content": orchestrator_instruction + coala_prompt,
            }
        ]
        response = litellm_client.chat.completions.create(
            model=os.getenv("LITELLM_MODEL"),
            messages=generator_messages,
            max_tokens=500,
        )
        content = response.choices[0].message.content
        stripped_content = self.strip_generated_react_step(
            content,
            ReactStepType.FINAL_ANSWER.value + ":",
            ReactStepType.THOUGHT.value,
        )

        # save run step
        create_message_runstep(
            self.thread_id, self.run_id, self.assistant_id, stripped_content
        )

        react_step = ReactStep(
            step_type=ReactStepType.FINAL_ANSWER, content=stripped_content
        )
        self.react_steps.append(react_step)

        return react_step

    def compose_coala_prompt(
        self,
        action_fc: bool = False,
    ) -> str:
        few_shot_instruction = self.compose_few_shot_instruction()
        react_trace_prompt = self.compose_react_trace()
        tools_prompt = "\n".join(
            f"- {tool.type} ({tool.description})"
            for _, tool in self.tool_items.items()
        )
        user_instruction = (
            self.compose_user_instruction()
        )  # TODO: the user instruction should not be appended here

        if action_fc:
            examples = """User input '...I have retrieved the information needed.'; Assistant response '[{{"name": "determine_next_action", "arguments": {{"next_action": "{}"}}}}]'""".format(  # noqa
                Actions.COMPLETION.value
            )
            for _, tool in self.tool_items.items():
                if tool.type == Actions.FILE_SEARCH.value:
                    examples += """\nUser input '...I need to retrieve information from...'; Assistant response '[{{"name": "determine_next_action", "arguments": {{"next_action": "{}"}}}}]'""".format(  # noqa
                        Actions.FILE_SEARCH.value
                    )

            return f"""{user_instruction}You will observe that there may already be steps after "Begin!".
The actions available to you are:
{tools_prompt}

Description of the reasoning and acting format:
{few_shot_instruction}

Reasoning and acting trace so far:
{react_trace_prompt}

Examples:```{examples}```"""  # noqa

        return f"""{user_instruction}You will observe that there may already be steps after "Begin!".
The actions available to you are:

{tools_prompt}


Continue the generation.
Only reply with the single next step.
Do respond with more than the immediate next step.
Use the following format:

{few_shot_instruction}

Begin!

{react_trace_prompt}"""  # noqa

    def compose_few_shot_instruction(self) -> str:
        tools_list_prompt = "[" + ", ".join(list(self.tool_items.keys())) + "]"
        return f"""Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of {tools_list_prompt}
Observation: the result of the action
... (this Thought/Action/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question"""

    def compose_user_instruction(self) -> str:
        if self.assistant.instructions:
            return f"""ADDITIONAL INSTRUCTION
```{self.assistant.instructions}```

"""
        return ""

    def compose_react_trace(
        self,
    ) -> str:
        trimmed_react_steps = self.react_steps
        if self.run.max_prompt_tokens:
            trimmed_react_steps = context_trimmer(
                item_list=self.react_steps,
                max_length=self.run.max_prompt_tokens * 3,
                trim_start=True,
            )
        react_steps_str = "\n".join(
            f"{step.step_type}: {step.content}" for step in trimmed_react_steps
        )
        return react_steps_str

    def parse_generation(self, generation: str) -> None:
        # Example code to parse generation output and extract steps
        lines = generation.split("\n")
        for line in lines:
            if (
                line.startswith("Action:")
                or line.startswith("Thought:")
                or line.startswith("Observation:")
            ):
                step_type, content = line.split(":", 1)
                self.react_steps.append(
                    ReactStep(
                        step_type=ReactStepType(step_type.strip()),
                        content=content.strip(),
                    )
                )

    def load_trace(self) -> List[ReactStep]:
        new_trace = []
        for step in self.runsteps:
            if step.type == "tool_calls":
                new_trace.append(
                    ReactStep(
                        step_type=ReactStepType.ACTION,
                        content=step.step_details.tool_calls[0].type,
                    )
                )
                new_trace.append(
                    ReactStep(
                        step_type=ReactStepType.OBSERVATION,
                        content=step.step_details.tool_calls[
                            0
                        ].model_dump_json(),
                    )
                )
            if step.type == "message_creation":
                message = next(
                    (
                        msg.content[0].text.value
                        for msg in self.messages.data
                        if msg.id
                        == step.step_details.message_creation.message_id
                    ),
                    None,
                )
                new_trace.append(
                    ReactStep(
                        step_type=ReactStepType.THOUGHT,
                        content=message,
                    )
                )

        self.react_steps = new_trace
        return self.react_steps

    def retrieve_assistant(self) -> Assistant:
        assistant = assistants_client.beta.assistants.retrieve(
            assistant_id=self.assistant_id
        )
        self.assistant = assistant
        return assistant

    def retrieve_messages(self) -> SyncCursorPage[Message]:
        messages = assistants_client.beta.threads.messages.list(
            thread_id=self.thread_id, order="asc"
        )
        self.messages = messages
        return messages

    def retrieve_run(self) -> run.Run:
        run = assistants_client.beta.threads.runs.retrieve(
            thread_id=self.thread_id, run_id=self.run_id
        )
        self.run = run
        return run

    def retrieve_runsteps(self) -> SyncCursorPage[run.RunStep]:
        runsteps = assistants_client.beta.threads.runs.steps.list(
            thread_id=self.thread_id, run_id=self.run_id, order="asc"
        )
        self.runsteps = runsteps
        return runsteps

    def set_assistant_tools(self) -> None:
        self.tool_items = {
            **tools_to_map(self.assistant.tools),
            **actions_to_map(
                [
                    Actions.COMPLETION.value,
                ]
            ),
        }

    def strip_generated_react_step(
        self, generation, start_key: str, runon_str: Optional[str] = None
    ) -> str:
        # TODO: deprecate this once there is no run on step generation
        try:
            stripped_generation = generation.split(start_key, 1)[1].strip()
        except IndexError:
            raise ValueError(
                "Generation did not follow ReAct format:\n"
                + generation
                + "\n"
                + start_key
            )

        for step_type in ReactStepType:
            stripped_generation = stripped_generation.split(
                step_type.value + ":", 1
            )[0].strip()

        return stripped_generation
