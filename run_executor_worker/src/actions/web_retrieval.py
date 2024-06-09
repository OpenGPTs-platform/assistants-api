from typing import List
from utils.ops_api_handler import create_web_retrieval_runstep
from utils.openai_clients import litellm_client
from data_models import run
import os
from agents import coala
from pydantic import BaseModel
from utils.weaviate_utils import weaviate_client


class WebRetrievalResult(BaseModel):
    url: str
    content: str
    depth: int


class WebRetrieval:
    def __init__(
        self,
        coala_class: "coala.CoALA",
        amt_documents: int = 2,
    ):
        self.coala_class = coala_class
        self.amt_documents = amt_documents

    def query(self, query: str, site: str = None) -> List[WebRetrievalResult]:
        collection_name = "web_retrieval"
        if weaviate_client.collections.exists(name=collection_name):
            collection = weaviate_client.collections.get(name=collection_name)
        else:
            raise Exception(f"Collection {collection_name} does not exist.")

        query_result = collection.query.near_text(
            query=query,
            limit=self.amt_documents,
        )

        return [
            WebRetrievalResult(
                url=chunk.properties["url"],
                content=chunk.properties["content"],
                depth=chunk.properties["depth"],
            )
            for chunk in query_result.objects
        ]

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
        retrieved_items: List[WebRetrievalResult] = self.query(query)

        run_step = create_web_retrieval_runstep(
            self.coala_class.thread_id,
            self.coala_class.run_id,
            self.coala_class.assistant_id,
            [item.content for item in retrieved_items],
            site=", ".join([item.url for item in retrieved_items]),
        )
        return run_step

    def compose_query_system_prompt(self) -> str:
        trace = self.coala_class.compose_react_trace()

        composed_instruction = f"""Current working memory:
{trace}"""
        return composed_instruction
