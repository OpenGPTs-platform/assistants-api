from utils.ops_api_handler import (
    create_function_runstep,
)
from utils.openai_clients import fc_chat_completions_create
from openai.types.beta.threads.runs.function_tool_call import Function
from data_models import run
import os
from agents import coala


class FunctionCallingTool:
    def __init__(
        self,
        coala_class: "coala.CoALA",
    ):
        self.coala_class = coala_class

    def generate_tool_call(self) -> run.RunStep:
        # get all tools of type function
        instructions = """Your role is to call one of the function that are provided to provided to you.\n"""  # noqa
        function_tools = [
            tool.model_dump()
            for tool in self.coala_class.assistant.tools
            if tool.type == "function"
        ]
        tool_call = fc_chat_completions_create(
            messages=[
                {
                    "role": "user",
                    "content": instructions
                    + self.compose_query_system_prompt(),
                }
            ],
            model=os.getenv("FC_MODEL"),
            tools=function_tools,
        )
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

    # TODO: create generate_summary

    def compose_query_system_prompt(self) -> str:
        trace = self.coala_class.compose_react_trace()

        composed_instruction = f"""Current working memory:
{trace}"""
        return composed_instruction
