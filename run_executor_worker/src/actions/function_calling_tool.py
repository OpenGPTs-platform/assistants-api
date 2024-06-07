import json
from utils.ops_api_handler import (
    create_function_runstep,
    create_message_runstep,
)
from utils.openai_clients import fc_client
from openai.types.beta.threads.runs.function_tool_call import Function
from data_models import run
import os
from agents import coala
from openai.types.chat.chat_completion_message import (
    ChatCompletionMessage,
)


class FunctionCallingTool:
    def __init__(
        self,
        coala_class: "coala.CoALA",
    ):
        self.coala_class = coala_class
        self.function_tools = [
            tool.model_dump()
            for tool in self.coala_class.assistant.tools
            if tool.type == "function"
        ]

    def generate_tool_call(self) -> run.RunStep:
        # get all tools of type function
        instructions = """Your role is to call one of the function that are provided to provided to you.\n"""  # noqa
        tool_call = fc_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": instructions
                    + self.compose_query_system_prompt(),
                }
            ],
            model=os.getenv("FC_MODEL"),
            tools=self.function_tools,
        )
        print("\n\ntool_call:\n", tool_call)
        function = tool_call.choices[0].message.tool_calls[0].function
        # cast to run steps function
        function = Function(
            name=function.name,
            arguments=function.arguments,
        )
        # creat run step
        run_step = create_function_runstep(
            self.coala_class.thread_id,
            self.coala_class.run_id,
            self.coala_class.assistant_id,
            function,
        )

        return run_step

    def generate_tool_summary(self, function_step: run.RunStep) -> run.RunStep:
        generator_messages = [
            {"role": message.role, "content": message.content[0].text.value}
            for message in self.coala_class.messages.data
        ]
        # add function call and response to messages
        tool_calls = []
        tool_results = []
        for tool_call in function_step.step_details.tool_calls:
            tool_calls.append(
                ChatCompletionMessage(
                    role="assistant",
                    tool_calls=[
                        {
                            "id": tool_call.id,
                            "function": {
                                "arguments": tool_call.function.arguments,
                                "name": tool_call.function.name,
                            },
                            "type": tool_call.type,
                        }
                    ],
                )
            )
            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": tool_call.function.output,
                }
            )

        generator_messages += tool_calls + tool_results

        fc_summary = fc_client.chat.completions.create(
            messages=generator_messages,
            model=os.getenv("FC_MODEL"),
            tools=self.function_tools,
        )

        print("\n\nfc_summary:\n", fc_summary)

        message_rs = create_message_runstep(
            self.coala_class.thread_id,
            self.coala_class.run_id,
            self.coala_class.assistant_id,
            fc_summary.choices[0].message.content,
        )
        react_step = coala.ReactStep(
            step_type=coala.ReactStepType.THOUGHT,
            content=json.dumps(fc_summary.choices[0].message.content),
        )
        self.coala_class.react_steps.append(react_step)

        return message_rs

    def compose_query_system_prompt(self) -> str:
        trace = self.coala_class.compose_react_trace()

        composed_instruction = f"""Current working memory:
{trace}"""
        return composed_instruction
