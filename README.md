# assistants-api
![image](https://github.com/OpenGPTs-platform/assistants-api/assets/37946988/c5eac63b-b1bb-4504-ab02-4c8814d81e8d)
[_View full Figma spec_](https://www.figma.com/file/RBobTMUNS6EtelpTDyYqnA/Open-GPTs?type=whiteboard&node-id=0%3A1&t=Ga2G6MUOUiNjqe3l-1)

Immitate the OpenAI Assistants API in FastAPI using the official [OpenAI OpenAPI specification](https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml).

The [OpenAI OpenAPI specification](https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml) is the source of truth for this API.

# Quickstart

1. Create a copy of [`.env.example`](./.env.example) and name it `.env`. Fill in necessary values.
2. Run the dev environment with [`rundev.sh`](./rundev.sh) script.
3. Simply edit the host for your OpenAI client and you can use this API in the same way:

```python
client_to_oai = OpenAI(api_key="sk-...") # works the same way
client_to_local = OpenAI(base_url="http://localhost:8000", api_key="test")
a1 = client_to_local.beta.assistants.create(model="gpt-3.5-turbo", name="test")
a2 = client_to_local.beta.assistants.create(model="gpt-3.5-turbo", instruction="You are real-human")
for assistant in client_to_local.beta.assistants.list().data:
    print(client_to_local)
    client_to_local.beta.assistants.delete(assistant.id)
```


# Development
## Quickstart
1. Create a copy of [`.env.example`](./.env.example) and name it `.env`. Fill in necessary values.
2. Create a virtual environment and install dependencies `python -m venv .venv`. Activate it.
3. Install dependencies `pip install -r requirements.txt`.
4. Install pre-commit hooks `pre-commit install`.
5. Run the dev environment with [`rundev.sh`](./rundev.sh) script.
6. Run tests to verify everything is working `pytest`.

## Helper ["Assistants API" Dev Assistant GPT](https://chat.openai.com/g/g-VxH4qXfuJ-assistants-api-assistant)
Helper assistant for developing the "Assistants API". Normally conversation will flow like so:
```txt
Human: Lets work on /assistants GET endpoint, begin with a test. Here is an example of what I have so far:
<GIVE IT A BRIEF EXAMPLE OF CURRENT CODE>

Assistant: <RESPONDS WITH TEST CODE>

Human: Ok lets move on to the endpoint. Here is what I have so far:
<GIVE IT A BRIEF EXAMPLE OF CURRENT ROUTES CODE>
<GIVE IT A BRIEF EXAMPLE OF CURRENT CRUD CODE>
<GIVE IT A BRIEF EXAMPLE OF CURRENT SCHEMA CODE>

Assistant: <RESPONDS WITH RELEVANT CODE>

THEN WHEN YOU REPEAT WITH THE CURRENT CHAT YOU SHOULD NOT NEED ALL THE EXAMPLES
```

### Instruction

The user has the goal to build a FastAPI python server according to the OpenAPI specification in your knowledge "openai-openapi-dereferenced.json". This server will consist of a postgres server with the ORM sqlalchemy for storage, minio for file storage, and redis for caching.

Your objective is to facilitate the development of the server for the user by following these steps, ALWAYS FOLLOW THESE STEPS IN THE CORRESPONDING ORDER:

1. Using code_interpreter tool download "openai-openapi-dereferenced.json" from your knowledge to find the relevant specifications according to the user's query. Programmatically navigate the JSON. DO NOT RECALL FROM YOUR KNOWLEDGE, INSTEAD DOWNLOAD THE FILE IN A PYTHON SCRIPT AND NAVIGATE PROGRAMATICALLY.
2. Asking the user questions if more information is needed
3. Following Test Driven Development methodology create a e2e test using pytest and the OpenAI client. You will learn how to use openai assistants API by visiting this link to their documentation https://platform.openai.com/docs/assistants/overview with web browsing tool. YOU MUST VISIT THE LINK, IF YOU CANNOT BACKUP YOUR CODE WITH CODE FROM THE SITE YOU MUST ASK THE USER FOR CLARIFICATION. (The OpenAI client sends a request to the server which will handle the logic and return a response). YOU MUST WRITE THE TEST.
4. Asking the user questions if more information is needed.
5. Creating a plan for execution and providing the code.

### Knowledge

Add [openai-openapi-dereferenced.json](./assets/openai-openapi-dereferenced.json)
