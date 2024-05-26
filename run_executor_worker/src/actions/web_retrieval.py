from utils.ops_api_handler import create_web_retrieval_runstep
from utils.openai_clients import litellm_client
from data_models import run
import os
import requests
import urllib.parse
from agents import coala


class WebRetrieval:
    def __init__(
        self,
        coala_class: "coala.CoALA",
        amt_documents: int = 1,
    ):
        self.coala_class = coala_class
        self.amt_documents = amt_documents

    def query_rag(self, topic, query):
        url = f"http://api.rag.pro/getModel/{topic}/{urllib.parse.quote(query)}?top_k={self.amt_documents}"  # noqa
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                "API request failed with status code: {}".format(
                    response.status_code
                )
            )

    def generate(
        self,
    ) -> run.RunStep:
        # get relevant retrieval query
        user_instruction = self.coala_class.compose_user_instruction()
        instructions = f"""{user_instruction}Your role is generate a query for semantic search according to current working memory.
Even if there is no relevant information in the working memory, you should still generate a query to retrieve the most relevant information from the University of Florida (UF).
Only respond with the query iteself NOTHING ELSE.

"""  # noqa

        messages = [
            {
                "role": "user",
                "content": instructions + self.compose_query_system_prompt(),
            },
        ]
        response = litellm_client.chat.completions.create(
            model=os.getenv("LITELLM_MODEL"),
            messages=messages,
            max_tokens=200,
        )
        query = response.choices[0].message.content

        # Retrieve documents based on the query
        retrieved_content = self.query_rag("UFL", query)

        run_step = create_web_retrieval_runstep(
            self.coala_class.thread_id,
            self.coala_class.run_id,
            self.coala_class.assistant_id,
            retrieved_content,
            site="UFL",
        )
        return run_step

    def compose_query_system_prompt(self) -> str:
        trace = self.coala_class.compose_react_trace()

        composed_instruction = f"""Current working memory:
{trace}"""
        return composed_instruction
