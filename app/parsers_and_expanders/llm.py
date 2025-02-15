import json
import time
from os.path import dirname
from os.path import abspath
from os.path import dirname
from os.path import join as join_path
from openai import AzureOpenAI
from os import getenv
from app.utils.llm_utils.azure_openai_utils import (
    call_model,
    call_model_batch,
)

def generate_response_format(file_name, file_path=None):
    if file_path is None:
        file_path = abspath(dirname(__file__))
    schema_file = join_path(file_path, file_name)
    # json_schema object can only have alphanumeric characters
    if "." in file_name:
        file_name = file_name.split(".")[0]
    file_name = "".join(e for e in file_name if e.isalnum())
    with open(schema_file, "r") as file:
        address_schema = json.loads(file.read())
    return {
        "type": "json_schema",
        "json_schema": {"name": file_name, "schema": address_schema, "strict": True},
    }



class LLMEntityExtraction:
    def __init__(self):
        AZURE_OPENAI_API_KEY = getenv("AZURE_OPENAI_API_KEY")
        AZURE_OPENAI_API_VERSION = getenv("AZURE_OPENAI_API_VERSION")
        AZURE_OPENAI_ENDPOINT = getenv("AZURE_OPENAI_ENDPOINT")
        AZURE_OPENAI_DEPLOYMENT = getenv("AZURE_OPENAI_DEPLOYMENT")

        print("AZURE_OPENAI_API_VERSION", AZURE_OPENAI_API_VERSION)
        print("AZURE_OPENAI_ENDPOINT", AZURE_OPENAI_ENDPOINT)
        print("AZURE_OPENAI_DEPLOYMENT", AZURE_OPENAI_DEPLOYMENT)

        self.client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        )

        self.model_deployment = AZURE_OPENAI_DEPLOYMENT

        self.response_format_expansion = generate_response_format(
            "address_expansion_schema.json"
        )
        self.response_format_extraction = generate_response_format(
            "address_entity_schema.json"
        )
        self.batch_response_format_expansion = generate_response_format(
            "address_expansion_batch_schema.json"
        )
        self.batch_response_format_extraction = generate_response_format(
            "address_entity_batch_schema.json"
        )

        self.system_message_expansion_prompt = """
            You are an AI assistant that can understand Peruvian addresses.
            Given the address below, expand the abbreviations, if any, and correct the word cases, when needed.
            If you find an abbreviation that is ambiguous, use its most common meaning when expanding it.
            """

        self.system_message_extraction_prompt = """
            You are an AI assistant that can extract address entities from Peruvian addresses.
            Given the address below, extract the address entities following the provided schema.
            If the address doesn't contain any of the fields in the schema, those values should be null.
            If the address contain 'Asentamiento Humano','Urbanización', 'Urbanización Humana', or similar, those values correspond to a neighborhood.
            If the address contain 'Sin Número', 'S/N', or similar, the corresponding value should be null.
            """

    # not used in the workflow - just for quick testing
    def expand_address(self, address: str) -> dict:
        return call_model(
            self.client,
            self.model_deployment,
            self.system_message_expansion_prompt,
            address,
            self.response_format_expansion,
        )

    # not used in the workflow - just for quick testing
    def parse_address(self, address: str) -> dict:
        return call_model(
            self.client,
            self.model_deployment,
            self.system_message_extraction_prompt,
            address,
            self.response_format_extraction,
        )

    # def get_address_expansion_batch(self, records: list) -> list:
    #     """
    #     Processes a batch of address expansion requests.

    #     1. First attempts the entire batch call.
    #     - If a rate limit exception is encountered, it retries the entire batch with exponential backoff.
    #     2. If the batch call fails for any other reason (e.g. content filtering trigger, or outer retries are exhausted),
    #     falls back to processing each record individually.
    #     - For each record, rate limit exceptions are retried with exponential backoff.
    #     - Any other exception is recorded in the "error" field.

    #     In all successful responses, an "error": None is added.
    #     """
    #     max_outer_retries = 5
    #     max_retries = 5

    #     def process_batch(records):

    #         responses = call_model_batch(
    #             self.client,
    #             self.model_deployment,
    #             system_message_extraction_prompt,
    #             records,
    #             self.response_format_extraction,
    #         )
    #         for response in responses:
    #             response["error"] = None
    #         return responses

    #     def process_individual(record, idx):
    #         messages = [
    #             self.system_message_expansion,
    #             {"role": "user", "content": record},
    #         ]
    #         retries = 0
    #         while retries < max_retries:
    #             try:
    #                 completion = self.client.chat.completions.create(
    #                     model=self.model_deployment,
    #                     messages=messages,
    #                     response_format=self.batch_response_format_expansion,
    #                 )
    #                 record_response = json.loads(completion.choices[0].message.content)[
    #                     "responses"
    #                 ][0]
    #                 record_response["error"] = None
    #                 return record_response
    #             except Exception as e:
    #                 if "rate limit" in str(e).lower():
    #                     retries += 1
    #                     time.sleep(2**retries)
    #                 else:
    #                     return {"id": idx, "expanded_address": "", "error": str(e)}
    #         return {
    #             "id": idx,
    #             "expanded_address": "",
    #             "error": f"Rate limit exceeded after {max_retries} retries",
    #         }

    #     # Attempt to process the entire batch.
    #     for outer_retries in range(max_outer_retries):
    #         try:
    #             return process_batch(records)
    #         except Exception as e:
    #             if "rate limit" in str(e).lower():
    #                 time.sleep(2 ** (outer_retries + 1))
    #             else:
    #                 break

    #     # Fallback: Process each record individually.
    #     return [process_individual(record, idx) for idx, record in enumerate(records)]

    # def get_address_entities_batch(self, records: list) -> list:
    #     """
    #     Processes a batch of address extraction requests.

    #     1. First attempts the entire batch call.
    #     - If a rate limit exception is encountered, it retries the entire batch with exponential backoff.
    #     2. If the batch call fails for any other reason (e.g. content filtering trigger, or outer retries are exhausted),
    #     falls back to processing each record individually.
    #     - For each record, rate limit exceptions are retried with exponential backoff.
    #     - Any other exception is recorded in the "error" field.

    #     In all successful responses, an "error": None is added.
    #     """
    #     max_outer_retries = 5
    #     outer_retries = 0

    #     # Attempt to process the entire batch.
    #     while True:
    #         try:
    #             messages = [self.system_message_extraction] + [
    #                 {"role": "user", "content": record} for record in records
    #             ]
    #             completion = self.client.chat.completions.create(
    #                 model=self.model_deployment,
    #                 messages=messages,
    #                 response_format=self.batch_response_format_extraction,
    #             )
    #             responses = json.loads(completion.choices[0].message.content)[
    #                 "responses"
    #             ]
    #             # Add error field to each successful response.
    #             for response in responses:
    #                 response["error"] = None
    #             return responses

    #         except Exception as e:
    #             if "rate limit" in str(e).lower():
    #                 # If the error is rate-limit related, retry the entire batch.
    #                 if outer_retries < max_outer_retries:
    #                     outer_retries += 1
    #                     sleep_time = 2**outer_retries  # exponential backoff
    #                     time.sleep(sleep_time)
    #                     continue  # retry the batch call
    #             # For any other exception (or if max outer retries exceeded), break out to process individually.
    #             break

    #     # Fallback: Process each record individually.
    #     responses = []
    #     for idx, record in enumerate(records):
    #         messages = [
    #             self.system_message_extraction,
    #             {"role": "user", "content": record},
    #         ]
    #         retries = 0
    #         max_retries = 5
    #         while True:
    #             try:
    #                 completion = self.client.chat.completions.create(
    #                     model=self.model_deployment,
    #                     messages=messages,
    #                     response_format=self.batch_response_format_extraction,
    #                 )
    #                 # Assume individual call returns a JSON with a "responses" list containing one element.
    #                 record_response = json.loads(completion.choices[0].message.content)[
    #                     "responses"
    #                 ][0]
    #                 record_response["error"] = None
    #                 responses.append(record_response)
    #                 break

    #             except Exception as e:
    #                 if "rate limit" in str(e).lower():
    #                     if retries < max_retries:
    #                         retries += 1
    #                         sleep_time = 2**retries
    #                         time.sleep(sleep_time)
    #                         continue
    #                     else:
    #                         responses.append(
    #                             {
    #                                 "id": idx,
    #                                 "streetName": None,
    #                                 "streetNumber": None,
    #                                 "block": None,
    #                                 "lot": None,
    #                                 "neighbourhood": None,
    #                                 "municipality": None,
    #                                 "municipalitySubdivision": None,
    #                                 "country": None,
    #                                 "countryCode": None,
    #                                 "countrySubdivision": None,
    #                                 "countrySecondarySubdivision": None,
    #                                 "postalCode": None,
    #                                 "error": f"Rate limit exceeded after {max_retries} retries: {str(e)}",
    #                             }
    #                         )
    #                         break
    #                 else:
    #                     responses.append(
    #                         {
    #                             "id": idx,
    #                             "streetName": None,
    #                             "streetNumber": None,
    #                             "block": None,
    #                             "lot": None,
    #                             "neighbourhood": None,
    #                             "municipality": None,
    #                             "municipalitySubdivision": None,
    #                             "country": None,
    #                             "countryCode": None,
    #                             "countrySubdivision": None,
    #                             "countrySecondarySubdivision": None,
    #                             "postalCode": None,
    #                             "error": str(e),
    #                         }
    #                     )
    #                     break
    #     return responses
