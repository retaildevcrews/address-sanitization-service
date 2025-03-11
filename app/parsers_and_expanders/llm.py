import json
import time
import logging
from os.path import dirname
from os.path import abspath
from os.path import dirname
from os.path import join as join_path
from openai import AzureOpenAI
from os import getenv
from app.utils.azure_openai_utils import (
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
    def __init__(self, address_expansion_prompt: str, address_extraction_prompt: str, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        AZURE_OPENAI_API_KEY = getenv("AZURE_OPENAI_API_KEY")
        AZURE_OPENAI_API_VERSION = getenv("AZURE_OPENAI_API_VERSION")
        AZURE_OPENAI_ENDPOINT = getenv("AZURE_OPENAI_ENDPOINT")
        AZURE_OPENAI_DEPLOYMENT = getenv("AZURE_OPENAI_DEPLOYMENT")

        # Validate that all required environment variables are set
        required_vars = {
            "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
            "AZURE_OPENAI_API_VERSION": AZURE_OPENAI_API_VERSION,
            "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
            "AZURE_OPENAI_DEPLOYMENT": AZURE_OPENAI_DEPLOYMENT,
        }
        for var_name, var_value in required_vars.items():
            if not var_value:
                raise ValueError(f"The environment variable '{var_name}' is not set or is empty.")


        self.logger.info(f"AZURE_OPENAI_API_VERSION: {AZURE_OPENAI_API_VERSION}")
        self.logger.info(f"AZURE_OPENAI_DEPLOYMENT: {AZURE_OPENAI_DEPLOYMENT}")

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

        self.address_expansion_prompt = address_expansion_prompt

        self.address_extraction_prompt = address_extraction_prompt


    def expand_address(self, address: str) -> dict:
        return call_model(
            client=self.client,
            model_deployment=self.model_deployment,
            system_prompt=self.address_expansion_prompt,
            user_prompt=address,
            response_format=self.response_format_expansion,
            logger=self.logger,
        )

    def parse_address(self, address: str) -> dict:
        return call_model(
            client=self.client,
            model_deployment=self.model_deployment,
            system_prompt=self.address_extraction_prompt,
            user_prompt=address,
            response_format=self.response_format_extraction,
            logger=self.logger,
        )
