from typing import Literal
from openai.pagination import SyncCursorPage
from data_models import run
from openai.types.beta.threads import ThreadMessage
from utils.tools import Actions
from utils.tools import ActionItem


class CoALA:
    def __init__(
        self,
        runsteps: SyncCursorPage[run.RunStep],
        messages: SyncCursorPage[ThreadMessage],
        job_summary: str,
        tools_map: dict[str, ActionItem],
    ):
        """
        CoALA class to setup the CoALA prompt
        messages: episodic memory
        runsteps: working memory
        job_summary: objective
        tools_map: external actions
        """
        self.runsteps = runsteps
        self.messages = messages
        self.job_summary = job_summary
        self.tools_map = tools_map

    def compose_trace(self):
        """
        Compose the trace prompt of the current task
        """
        trace_prompt = []
        for step in self.runsteps:
            if step.type == "tool_calls":
                trace_prompt.append(
                    f"Action: {step.step_details.tool_calls[0].type}"
                )
                trace_prompt.append(
                    f"Observation: {step.step_details.tool_calls[0].model_dump()}"
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
                trace_prompt.append(f"Thought: {message}")
        return "\n".join(trace_prompt)

    def compose_actions(self):
        """
        Compose the tools prompt for the CoALA task
        """
        action_prompts = []
        for tool in self.tools_map:
            action_prompts.append(
                f"- {tool} ({self.tools_map[tool].description})"
            )
        action_prompts.append(
            f"- {Actions.COMPLETION.value} (Finish the process, generate the final answer)"  # noqa
        )
        return "\n".join(action_prompts)

    def compose_prompt(
        self, type: Literal["action", "thought", "final_answer"]
    ):
        """
        Compose the prompt for the CoALA task
        """
        base_prompt = None
        if type == "action":
            base_prompt = """Your role is to determine which "Action" to use next.
You must always begin with "Action: ..." """
        elif type == "thought":
            base_prompt = """Your role is to provide a "Thought" response to the user.
You must always begin with "Thought: ..."  and finish with "Action: " """
        elif type == "final_answer":
            base_prompt = """Your role is to provide the "Final Answer" to the user.
You must always begin with "Final Answer: ..." """
        trace_prompt = self.compose_trace()
        actions_prompt = self.compose_actions()
        actions_list = list(self.tools_map.keys()) + [Actions.COMPLETION.value]

        coala_prompt = f"""{base_prompt}
You will observe that there are already steps after "Begin!".
The actions available to you are:

{actions_prompt}

Continue the generation.
Only reply with the single next step.
Do respond with more than the immediate next step.
Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of {actions_list}
Observation: the result of the action
... (this Thought/Action/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {self.job_summary}
{trace_prompt}"""

        return coala_prompt
