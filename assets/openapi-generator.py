import json
import jsonref
import requests
import yaml

url = 'https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml'
response = requests.get(url)
yaml_data = yaml.safe_load(response.text)

string_json_data = json.dumps(yaml_data)

dereferenced = jsonref.loads(string_json_data)

# save prettified in final dereferenced file
with open('openai-openapi-dereferenced.json', 'w') as f:
    f.write(json.dumps(dereferenced, indent=2))