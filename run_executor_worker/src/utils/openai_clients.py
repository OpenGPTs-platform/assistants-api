from openai import OpenAI
import os

litellm_client = None
if os.getenv("LITELLM_API_URL"):
    litellm_client = OpenAI(
        api_key=os.getenv("LITELLM_API_KEY"),
        base_url=os.getenv("LITELLM_API_URL", None),
    )
else:
    litellm_client = OpenAI(
        api_key=os.getenv("LITELLM_API_KEY"),
    )

assistants_client = OpenAI(
    base_url=os.getenv("ASSISTANTS_API_URL"),
)
