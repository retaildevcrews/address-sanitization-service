from openai import AzureOpenAI
from os.path import dirname
from os.path import abspath
from os.path import dirname
from os.path import join as join_path
import json


def _call_model(client: AzureOpenAI, model_deployment, messages, response_format):
    completion = client.chat.completions.create(
        model=model_deployment, messages=messages, response_format=response_format
    )
    return json.loads(completion.choices[0].message.content)


def generate_response_format(file_name, file_path=None):
    if file_path is None:
        file_path = abspath(dirname(__file__))
    schema_file = join_path(file_path, file_name)
    #json_schema object can only have alphanumeric characters
    if '.' in file_name:
        file_name = file_name.split('.')[0]
    file_name = ''.join(e for e in file_name if e.isalnum())
    with open(schema_file, "r") as file:
        address_schema = json.loads(file.read())
    return {
        "type": "json_schema",
        "json_schema": {"name": file_name, "schema": address_schema, "strict": True},
    }


def call_model(
    client: AzureOpenAI, model_deployment, system_prompt, user_prompt, response_format
):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    return _call_model(client, model_deployment, messages, response_format)


def call_model_batch(
    client: AzureOpenAI, model_deployment, system_prompt, user_prompts, response_format
):
    messages = [{"role": "system", "content": system_prompt}] + [
        {"role": "user", "content": user_prompt} for user_prompt in user_prompts
    ]
    return _call_model(client, model_deployment, messages, response_format)["responses"]
