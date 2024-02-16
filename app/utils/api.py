import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Optional
from openai.types.beta.threads.runs import RunStep

load_dotenv()

ASSISTANTS_URL = os.environ.get("ASSISTANTS_URL")

openai_client = OpenAI(
    base_url=ASSISTANTS_URL if ASSISTANTS_URL else None,
    api_key=os.environ.get("OPENAI_API_KEY"),
)


# TODO: may want to add user message to run steps for consistency
def get_run_steps(
    openai_client: OpenAI,
    thread_id: str,
    run_id: str,
    step_callback: Optional[callable] = None,
) -> List[RunStep]:
    run_steps = openai_client.beta.threads.runs.steps.list(
        thread_id=thread_id,
        run_id=run_id,
    )
    run_steps_list: List[RunStep] = []

    # Iterate over the data in run_steps
    for step in run_steps:
        step_callback(step) if step_callback else None
        # TODO: inefficient, could be fetchin messages that are not finished

        run_steps_list.append(step)

    return run_steps_list
