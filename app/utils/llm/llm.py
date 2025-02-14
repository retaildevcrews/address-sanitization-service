from openai import AzureOpenAI
from openai.types import SystemMessage

from os.path import dirname
from os.path import abspath
from os.path import dirname
from os.path import join as join_path
from os import getenv
import json
import time


def _generate_response_format(file_name, file_path=None):
    if file_path is None:
        file_path = abspath(dirname(__file__))
    schema_file = join_path(file_path, file_name)
    with open(schema_file, "r") as file:
        address_schema = json.loads(file.read())
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_file,
            "schema": address_schema,
            "strict": True
        }
    }

class Message:
    def __init__(self, content):
        self.content = content


class SystemMessage(Message):
    def __init__(self, content):
        super().__init__(content)
        self.role = "system"


class UserMessage(Message):
    def __init__(self, content):
        super().__init__(content)
        self.role = "user"

def _call_model(client:AzureOpenAI, model_deployment, messages, response_format):
    completion = client.chat.completions.create(
        model=model_deployment,
        messages=messages,
        response_format=response_format
    )
    return json.loads(completion.choices[0].message.content)

def single_user_message(client:AzureOpenAI, model_deployment, system_message, user_prompt, response_format):
    messages = [system_message, {"role": "user", "content": user_prompt}]
    return _call_model(client,model_deployment, messages, response_format)

def batch_user_message(client: AzureOpenAI, model_deployment, system_message, user_prompts, response_format):
    messages = [system_message] + [{"role": "user", "content": prompt} for prompt in user_prompts]
    return _call_model(client, model_deployment, messages, response_format)["responses"]



class LLMEntityExtraction:
    def __init__(self):
        local_path = abspath(dirname(__file__))

        AZURE_OPENAI_API_KEY = getenv("AZURE_OPENAI_API_KEY")
        AZURE_OPENAI_API_VERSION = getenv("AZURE_OPENAI_API_VERSION")
        AZURE_OPENAI_ENDPOINT = getenv("AZURE_OPENAI_API_ENDPOINT")
        AZURE_OPENAI_DEPLOYMENT = getenv("AZURE_OPENAI_DEPLOYMENT")


        self.client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_deployment=AZURE_OPENAI_DEPLOYMENT
        )

        self.model_deployment = AZURE_OPENAI_DEPLOYMENT

        self.system_message_expansion = SystemMessage(
            "You are an AI assistant that can understand Peruvian addresses."
            "Given the address below, expand the abbreviations, if any, and correct the word cases, when needed."
            "If you find an abbreviation that is ambiguous, use its most common meaning when expanding it."
        )

        self.system_message_extraction = SystemMessage(
            "You are an AI assistant that can extract address entities from Peruvian addresses."
            "Given the address below, extract the address entities following the provided schema."
            "If the address doesn't contain any of the fields in the schema, those values should be null."
            "If the address contain 'Asentamiento Humano','Urbanización', 'Urbanización Humana', or similar, those values correspond to a neighborhood."
            "If the address contain 'Sin Número', 'S/N', or similar, the corresponding value should be null."
        )

        self.response_format_expansion = _generate_response_format("address_expansion_schema.json")
        self.response_format_extraction = _generate_response_format("address_entity_schema.json")
        self.batch_response_format_expansion = _generate_response_format("address_expansion_batch_schema.json")
        self.batch_response_format_extraction = _generate_response_format("address_entity_batch_schema.json")

    # not used in the workflow - just for quick testing
    def get_address_expansion(self, address: str) -> dict:
        return single_user_message(self.client,
                           self.model_deployment,
                           self.system_message_expansion,
                           address,
                           self.response_format_expansion)

    # not used in the workflow - just for quick testing
    def get_address_entities(self, address: str) -> dict:
        return single_user_message(self.client,
                           self.model_deployment,
                           self.system_message_extraction,
                           address,
                           self.response_format_extraction)


    def get_address_expansion_batch(self, records: list) -> list:
        """
        Processes a batch of address expansion requests.

        1. First attempts the entire batch call.
        - If a rate limit exception is encountered, it retries the entire batch with exponential backoff.
        2. If the batch call fails for any other reason (e.g. content filtering trigger, or outer retries are exhausted),
        falls back to processing each record individually.
        - For each record, rate limit exceptions are retried with exponential backoff.
        - Any other exception is recorded in the "error" field.

        In all successful responses, an "error": None is added.
        """
        max_outer_retries = 5
        max_retries = 5

        def process_batch(records):

            responses = batch_user_message(self.client,
                           self.model_deployment,
                           self.system_message_extraction,
                           records,
                           self.response_format_extraction)
            for response in responses:
                response["error"] = None
            return responses

        def process_individual(record, idx):
            messages = [self.system_message_expansion, {"role": "user", "content": record}]
            retries = 0
            while retries < max_retries:
                try:
                    completion = self.client.chat.completions.create(
                        model=self.model_deployment,
                        messages=messages,
                        response_format=self.batch_response_format_expansion
                    )
                    record_response = json.loads(completion.choices[0].message.content)["responses"][0]
                    record_response["error"] = None
                    return record_response
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        retries += 1
                        time.sleep(2 ** retries)
                    else:
                        return {
                            "id": idx,
                            "expanded_address": "",
                            "error": str(e)
                        }
            return {
                "id": idx,
                "expanded_address": "",
                "error": f"Rate limit exceeded after {max_retries} retries"
            }

        # Attempt to process the entire batch.
        for outer_retries in range(max_outer_retries):
            try:
                return process_batch(records)
            except Exception as e:
                if "rate limit" in str(e).lower():
                    time.sleep(2 ** (outer_retries + 1))
                else:
                    break

        # Fallback: Process each record individually.
        return [process_individual(record, idx) for idx, record in enumerate(records)]


    def get_address_entities_batch(self, records: list) -> list:
        """
        Processes a batch of address extraction requests.

        1. First attempts the entire batch call.
        - If a rate limit exception is encountered, it retries the entire batch with exponential backoff.
        2. If the batch call fails for any other reason (e.g. content filtering trigger, or outer retries are exhausted),
        falls back to processing each record individually.
        - For each record, rate limit exceptions are retried with exponential backoff.
        - Any other exception is recorded in the "error" field.

        In all successful responses, an "error": None is added.
        """
        max_outer_retries = 5
        outer_retries = 0

        # Attempt to process the entire batch.
        while True:
            try:
                messages = [self.system_message_extraction] + [
                    {"role": "user", "content": record} for record in records
                ]
                completion = self.client.chat.completions.create(
                    model=self.model_deployment,
                    messages=messages,
                    response_format=self.batch_response_format_extraction
                )
                responses = json.loads(completion.choices[0].message.content)["responses"]
                # Add error field to each successful response.
                for response in responses:
                    response["error"] = None
                return responses

            except Exception as e:
                if "rate limit" in str(e).lower():
                    # If the error is rate-limit related, retry the entire batch.
                    if outer_retries < max_outer_retries:
                        outer_retries += 1
                        sleep_time = 2 ** outer_retries  # exponential backoff
                        time.sleep(sleep_time)
                        continue  # retry the batch call
                # For any other exception (or if max outer retries exceeded), break out to process individually.
                break

        # Fallback: Process each record individually.
        responses = []
        for idx, record in enumerate(records):
            messages = [self.system_message_extraction, {"role": "user", "content": record}]
            retries = 0
            max_retries = 5
            while True:
                try:
                    completion = self.client.chat.completions.create(
                        model=self.model_deployment,
                        messages=messages,
                        response_format=self.batch_response_format_extraction
                    )
                    # Assume individual call returns a JSON with a "responses" list containing one element.
                    record_response = json.loads(completion.choices[0].message.content)["responses"][0]
                    record_response["error"] = None
                    responses.append(record_response)
                    break

                except Exception as e:
                    if "rate limit" in str(e).lower():
                        if retries < max_retries:
                            retries += 1
                            sleep_time = 2 ** retries
                            time.sleep(sleep_time)
                            continue
                        else:
                            responses.append({
                                "id": idx,
                                "streetName": None,
                                "streetNumber": None,
                                "block": None,
                                "lot": None,
                                "neighbourhood": None,
                                "municipality": None,
                                "municipalitySubdivision": None,
                                "country": None,
                                "countryCode": None,
                                "countrySubdivision": None,
                                "countrySecondarySubdivision": None,
                                "postalCode": None,
                                "error": f"Rate limit exceeded after {max_retries} retries: {str(e)}"
                            })
                            break
                    else:
                        responses.append({
                            "id": idx,
                            "streetName": None,
                            "streetNumber": None,
                            "block": None,
                            "lot": None,
                            "neighbourhood": None,
                            "municipality": None,
                            "municipalitySubdivision": None,
                            "country": None,
                            "countryCode": None,
                            "countrySubdivision": None,
                            "countrySecondarySubdivision": None,
                            "postalCode": None,
                            "error": str(e)
                        })
                        break
        return responses
