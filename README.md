# assistants-api
### [DISCORD](https://discord.gg/jZSVhtwTz6)
### [Video Demo](https://youtu.be/yPdIEKb3jWc)

Replicate and improve the OpenAI Assistants API
Note: currently support client `openai==1.26.0` (excluding custom tools like `web_retriever`) or use our fork by `pip install git+https://github.com/OpenGPTs-platform/openai-python.git`


### [Video Demo (full OpenGPTs-platform)](https://youtu.be/yPdIEKb3jWc)

Architecture
![image](https://github.com/OpenGPTs-platform/assistants-api/assets/37946988/faa5a4b2-1186-49b8-a80b-39c4fc00b772)

### Quickstart
0. Clone the repo `git clone https://github.com/OpenGPTs-platform/assistants-api.git` and navigate into `assistants-api`directory
1. Create a copy of [`.env.example`](./.env.example) and name it `.env`. Fill in necessary values.
2. Start docker-compose `docker-compose -f .\docker-compose.dev.yml up`
3. Its running 🥳!
4. In a new directory and environment, install the `openai` client fork with `pip install IPython git+https://github.com/OpenGPTs-platform/openai-python.git`, and try it with the following demo (NOTE: update `YOUR_FILE_PATH` with your file path that you want to test retrieval with). Also it may now
```py
from openai import OpenAI
client = OpenAI(
    base_url="http://localhost:8000",
    api_key="NO_KEY_NEEDED",
)

# Upload file to the server
file = client.files.create(
    file=open('YOUR_FILE_PATH', 'rb'), # Input your file path (currently accepts .txt and .pdf files)
    purpose='assistants'
)

# Create vector store with the file id
vs = client.beta.vector_stores.create(
    name='my_info',
    file_ids=[file.id]
)

# Create an assistant with the vector store passed in
asst = client.beta.assistants.create(
    name="Demo Assistant",
    instructions="Always start your responses for with the word 'APPLE'",
    model="gpt-4-turbo",
    tools=[{"type": "file_search"}, {"type": "web_retrieval"}],
    tool_resources={
        "file_search": {
            "vector_store_ids": [vs.id]
        }
    },
)

# Create a thread with or without messages
thr = client.beta.threads.create(
    messages=[
        {
            "role": "user",
            "content": "I am curious what is in the file I provided"
        }
    ],
)

# Execute the run (Adds run to RabbitMQ for to be dequeued and processed by run_executor_worker)
run = client.beta.threads.runs.create(
    thread_id=thr.id,
    assistant_id=asst.id
)

# Poll the response untill complete (streaming not yet supported)
from IPython.display import clear_output
import time
while run.status not in ['completed', 'failed']:
    time.sleep(1)
    clear_output(wait=True)
    run = client.beta.threads.runs.retrieve(thread_id=thr.id, run_id=run.id)
    print("RUN STATUS:\n",run.status)
    messages = client.beta.threads.messages.list(thread_id=thr.id, order='desc')
    print("THREAD MESSAGES:\n",messages.model_dump_json(indent=2))
``` 
## [assistants_api](./assistants_api)
![image](https://github.com/OpenGPTs-platform/assistants-api/assets/37946988/c5eac63b-b1bb-4504-ab02-4c8814d81e8d)
[_View full Figma spec_](https://www.figma.com/file/RBobTMUNS6EtelpTDyYqnA/Open-GPTs?type=whiteboard&node-id=0%3A1&t=Ga2G6MUOUiNjqe3l-1)

Handle the business logic (store and retrieve data, store files, enque runs) for the Assistants API according to the official [OpenAI OpenAPI specification](https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml).

The [OpenAI OpenAPI specification](https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml) is the source of truth for this API.

## [run_executor_worker](./run_executor_worker)
![image](https://github.com/OpenGPTs-platform/HexAmerous/assets/37946988/610c60fe-ad01-4231-aec2-84c9a295ed30)
[_View full Figma spec_](https://www.figma.com/file/RBobTMUNS6EtelpTDyYqnA/Open-GPTs?type=whiteboard&node-id=0%3A1&t=Ga2G6MUOUiNjqe3l-1)

Agent that executes runs according to CoALA architecture and ReAct prompting strategy.

## Major Objectives
1. Function calling for [run_executor_worker](./run_executor_worker) using [Mistral-7B-Instruct-v0.3](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3)
2. Connect [chat-ui](https://github.com/OpenGPTs-platform/chat-ui)
3. Optimize prompting in [run_executor_worker](./run_executor_worker)
4. Open-source `web_retrieval` and add `annotations` to messages for citation purposes

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
