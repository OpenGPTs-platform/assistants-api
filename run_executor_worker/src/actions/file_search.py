from typing import List
from utils.weaviate_utils import retrieve_file_chunks
from utils.ops_api_handler import create_retrieval_runstep
from utils.openai_clients import litellm_client, assistants_client
from openai.types.beta.vector_store import VectorStore
from data_models import run
import json
import os

# import coala
from agents import coala


class FileSearch:
    def __init__(
        self,
        coala_class: "coala.CoALA",
    ):
        self.coala_class = coala_class
        self.vector_stores: List[VectorStore] = []

    def retrieve_vector_stores(self):
        vector_store_ids = (
            self.coala_class.assistant.tool_resources.file_search.vector_store_ids
        )
        for vector_store_id in vector_store_ids:
            vector_store = assistants_client.beta.vector_stores.retrieve(
                vector_store_id
            )
            self.vector_stores.append(vector_store)

    def generate(
        self,
    ) -> run.RunStep:
        # get relevant retrieval query
        user_instruction = self.coala_class.compose_user_instruction()
        instruction = f"""{user_instruction}Your role is generate a query for semantic search to retrieve important according to current working memory and the available files.
Even if there is no relevant information in the working memory, you should still generate a query to retrieve the most relevant information from the available files.
Only respond with the query iteself NOTHING ELSE.

"""  # noqa
        if not len(self.vector_stores):
            self.retrieve_vector_stores()

        messages = [
            {
                "role": "user",
                "content": instruction + self.compose_query_system_prompt(),
            },
        ]
        response = litellm_client.chat.completions.create(
            model=os.getenv(
                "LITELLM_MODEL"
            ),  # Replace with your model of choice
            messages=messages,
            max_tokens=200,  # You may adjust the token limit as necessary
        )
        query = response.choices[0].message.content
        # TODO: retrieve from db, and delete mock retrieval document
        vector_store_ids = (
            self.coala_class.assistant.tool_resources.file_search.vector_store_ids
        )
        retrieved_documents = retrieve_file_chunks(
            vector_store_ids,
            query,
        )

        run_step = create_retrieval_runstep(
            self.coala_class.thread_id,
            self.coala_class.run_id,
            self.coala_class.assistant_id,
            retrieved_documents,
        )
        return run_step

    def compose_file_list(
        self,
    ) -> str:
        files_names = []

        print

        file_ids = (
            []
        )  # NOTE: this only work natively with OpenGPTs-platform/assistants-api otherwise you need to make sure to manually manage the metadata["_file_ids"] inside the vector stores # noqa

        for vector_store in self.vector_stores:
            vector_store_file_ids = (
                json.loads(vector_store.metadata["_file_ids"])
                if "_file_ids" in vector_store.metadata
                else []
            )
            file_ids.extend(vector_store_file_ids)

        if not file_ids:
            print("\n\nNO FILES AVAILABLE: ", file_ids)
            return ""
        for file_id in file_ids:
            file = assistants_client.files.retrieve(file_id)
            files_names.append(f"- {file.filename}")
        return "\n".join(files_names)

    def compose_query_system_prompt(self) -> str:
        composed_instruction = ""
        trace = self.coala_class.compose_react_trace()

        file_list_str = self.compose_file_list()
        if file_list_str:
            composed_instruction += f"""The files currently available to you are:
{self.compose_file_list()}

"""

        composed_instruction += f"""Current working memory:
{trace}"""
        return composed_instruction
