from typing import Dict, Any, Optional
from constants import PromptKeys
from utils.weaviate_utils import get_web_retrieval_description
from utils.tools import ActionItem, Actions, tools_to_map
from utils.ops_api_handler import create_message_runstep, update_run
from data_models import run
from openai.types.beta.threads.message import Message
from utils.openai_clients import assistants_client
from openai.types.beta.thread import Thread
from openai.types.beta import Assistant
from openai.pagination import SyncCursorPage
from agents import router, coala
from actions import function_calling_tool
import json
import datetime

# TODO: add assistant and base tools off of assistant


class ExecuteRun:
    def __init__(
        self, thread_id: str, run_id: str, run_config: Dict[str, Any] = {}
    ):
        self.run_id = run_id
        self.thread_id = thread_id
        self.assistant_id: Optional[str] = None
        self.run_config = run_config

        self.run: Optional[run.Run] = None
        self.messages: Optional[SyncCursorPage(Message)] = None
        self.thread: Optional[Thread] = None
        self.assistant: Optional[Assistant] = None
        self.tools_map: Optional[dict[str, ActionItem]] = None
        self.runsteps: Optional[SyncCursorPage[run.RunStep]] = None
        self.web_retrieval_description: Optional[str] = None
        # TODO: add assistant and base tools off of assistant

    def execute(self):
        # Create an instance of the RunUpdate schema with the new status
        run_update = run.RunUpdate(status=run.RunStatus.IN_PROGRESS.value)

        # Call the API handler to update the run status
        updated_run = update_run(self.thread_id, self.run_id, run_update)

        if not updated_run:
            print(
                f"Error updating run status for {self.run_id}. Aborting execution."
            )
            return

        try:
            self.run = updated_run
            self.runsteps = assistants_client.beta.threads.runs.steps.list(
                run_id=self.run_id, thread_id=self.thread_id, order="desc"
            )
            print("\n\nExecuting run: ", self.run, "\n\n")

            # Get the thread messages
            # TODO: should only populate these entities once
            thread = assistants_client.beta.threads.retrieve(
                thread_id=self.thread_id,
            )
            self.thread = thread

            assistant = assistants_client.beta.assistants.retrieve(
                assistant_id=self.run.assistant_id,
            )
            self.assistant_id = assistant.id
            self.assistant = assistant

            self.web_retrieval_description = get_web_retrieval_description()
            self.tools_map = tools_to_map(
                self.assistant.tools, self.web_retrieval_description
            )

            messages = assistants_client.beta.threads.messages.list(
                thread_id=self.thread_id, order="asc"
            )
            self.messages = messages

            if (
                len(self.runsteps.data)
                and self.runsteps.data[0].status == "completed"
                and self.runsteps.data[0].type == "tool_calls"
                and self.runsteps.data[0].step_details.tool_calls[0].type
                == "function"
            ):
                router_response = "tool_response"
            else:
                router_agent = router.RouterAgent(self)  # semantic router
                router_response = router_agent.generate()

            if (
                router_response != PromptKeys.TRANSITION.value
                and router_response != "tool_response"
            ):
                create_message_runstep(
                    self.thread_id,
                    self.run_id,
                    self.run.assistant_id,
                    router_response,
                )
                print(f"\n\nFinal response:\n{router_response}")
                update_run(
                    self.thread_id,
                    self.run_id,
                    run.RunUpdate(
                        status=run.RunStatus.COMPLETED.value,
                        completed_at=int(datetime.datetime.now().timestamp()),
                    ),
                )
                print(
                    f"""\n\nFinished executing run with status {run.RunStatus.COMPLETED.value}."""  # noqa
                )
                return
            print("\n\nTRANSITIONING TO COALA\n\n")

            coala_class = coala.CoALA(
                self.run_id, self.thread_id, self.assistant_id, self
            )
            self.run = coala_class.retrieve_run()
            self.assistant = coala_class.retrieve_assistant()
            self.messages = coala_class.retrieve_messages()
            self.runsteps = coala_class.retrieve_runsteps()
            coala_class.set_assistant_tools()

            if router_response == PromptKeys.TRANSITION.value:
                coala_class.generate_question()

            if router_response == "tool_response":
                coala_class.load_trace()

            max_steps = 8
            curr_step = 0

            requires_action = False
            while (
                coala_class.react_steps[-1].step_type
                != coala.ReactStepType.FINAL_ANSWER
            ):
                if router_response == "tool_response":
                    router_response = PromptKeys.TRANSITION.value
                    fc_tool = function_calling_tool.FunctionCallingTool(
                        coala_class
                    )
                    fc_tool.generate_tool_summary(self.runsteps.data[-1])
                    continue

                self.messages = coala_class.retrieve_messages()
                self.runsteps = coala_class.retrieve_runsteps()
                if (
                    coala_class.react_steps[-1].step_type
                    != coala.ReactStepType.THOUGHT
                ):
                    coala_class.generate_thought()
                coala_class.generate_action()
                current_action = Actions(coala_class.react_steps[-1].content)
                coala_class.execute_action(current_action)

                print(
                    f"""\n\nStep {curr_step} completed.
    with react steps:
    {json.dumps([step.model_dump() for step in coala_class.react_steps], indent=2)}"""
                )
                curr_step += 1

                if current_action == Actions.FUNCTION:
                    requires_action = True
                    break
                if curr_step >= max_steps:
                    break
            # if while completes from the if statement, then print("success") else if it breaks from the while loop, print("failure") # noqa
            if (
                coala_class.react_steps[-1].step_type
                == coala.ReactStepType.FINAL_ANSWER
            ):
                run_update = run.RunUpdate(
                    status=run.RunStatus.COMPLETED.value,
                    completed_at=int(datetime.datetime.now().timestamp()),
                )
            elif requires_action:
                latest_react_step = coala_class.react_steps[-1]
                run_update = run.RunUpdate(
                    status=run.RunStatus.REQUIRES_ACTION.value,
                    required_action=run.RequiredAction.model_validate(
                        {
                            "submit_tool_outputs": {
                                "tool_calls": [
                                    json.loads(latest_react_step.content)
                                ]
                            },
                            "type": "submit_tool_outputs",
                        }
                    ),
                )
            else:
                run_update = run.RunUpdate(
                    status=run.RunStatus.FAILED.value,
                    completed_at=int(datetime.datetime.now().timestamp()),
                )
            updated_run = update_run(self.thread_id, self.run_id, run_update)

            print(
                f"""\n\nFinished executing run with status {run_update.status} after {curr_step} steps."""  # noqa
            )
        except Exception as e:
            print(f"Error executing run: {e}")
            run_update = run.RunUpdate(
                status=run.RunStatus.FAILED.value,
                failed_at=int(datetime.datetime.now().timestamp()),
            )
            updated_run = update_run(self.thread_id, self.run_id, run_update)
            print(f"Run failed: {updated_run}")
            return
