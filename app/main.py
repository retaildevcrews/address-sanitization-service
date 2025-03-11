# app/main.py
import logging
import yaml
from contextlib import asynccontextmanager

from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Depends

from .parsers_and_expanders.libpostal import parse_address as libpostal_parse_address
from .parsers_and_expanders.libpostal import expand_address as libpostal_expand_address
from .parsers_and_expanders.llm import LLMEntityExtraction

from .exceptions import GeocodingError
from .schemas import (
    AddressRequest,
    AddressResponse,
    ParseAddressResponse,
    ExpandAddressResponse,
    Address,
    SystemPrompt,
)
from .strategies import StrategyFactory
from .exceptions import GeocodingError
from .utils import batch_executor

from typing import List

logger = logging.getLogger(__name__)

def load_config():
    try:
        with open("/app/app/parsers_and_expanders/prompt_config.yaml", "r") as f:
            config = yaml.safe_load(f)
        address_expansion_prompt = config.get("address_expansion_prompt")
        address_extraction_prompt = config.get("address_extraction_prompt")
        return address_expansion_prompt, address_extraction_prompt
    except Exception as e:
        logger.error(f"Failed to load LLM prompt config: {e}")
        return None, None


class ConfigManager:
    def __init__(self):
        self.address_expansion_prompt, self.address_extraction_prompt  = load_config()

    def get_address_expansion_prompt(self):
        return self.address_expansion_prompt
    
    def get_address_extraction_prompt(self):
        return self.address_extraction_prompt

    def set_address_expansion_prompt(self, new_prompt: str):
        self.address_expansion_prompt = new_prompt

    def set_address_extraction_prompt(self, new_prompt: str):
        self.address_extraction_prompt = new_prompt


config_manager = ConfigManager()

global llm_extractor

@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_extractor
    try:
        llm_extractor = LLMEntityExtraction(
            address_expansion_prompt=config_manager.get_address_expansion_prompt(),
            address_extraction_prompt=config_manager.get_address_extraction_prompt(),
            logger=logger,
        )
    except Exception as e:
        logger.error(f"Failed to initialize LLMEntityExtraction: {e}")
    yield


app = FastAPI(
    title="Address Sanitization Service",
    description="Sanitizes addresses using multiple geocoding providers",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Address",
            "description": "Address standardization and geocoding operations",
        }
    ],
    lifespan=lifespan,
)

def get_llm_extractor():
    return LLMEntityExtraction(
        address_expansion_prompt=config_manager.get_address_expansion_prompt(),
        address_extraction_prompt=config_manager.get_address_extraction_prompt(),
        logger=logger
    )


@app.get("/", include_in_schema=False)
def health_check():
    return {"status": "healthy", "version": app.version}


@app.get(
    "/api/v1/address/parse/libpostal",
    response_model=ParseAddressResponse,
    tags=["Address"],
)
async def parse_address(
    address: str = Query(
        ...,
        description="Free-form address string (e.g. '1 Microsoft Way, Redmond, WA 98052')",
    )
):
    """
    **Parse a free-form address** into its components using libpostal.
    \n
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    """
    try:
        response = libpostal_parse_address(address)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/address/parse/libpostal/batch", tags=["Address"])
async def expand_address_libpostal_batch(addresses: List[Address]):
    """
    Parse addresses passed in as an array of addresses


    Parameters:
    - **addresses**: List of address objects
    """
    try:
        address_strings = [address.freeformAddress for address in addresses]
        executor = batch_executor.BatchExecutor(
            func=libpostal_parse_address, num_threads=5, delay=0.5
        )
        results = executor.execute_ordered(address_strings)
        return {"parsed_addresses": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/address/expand/libpostal",
    response_model=ExpandAddressResponse,
    tags=["Address"],
)
async def expand_address(
    address: str = Query(
        ...,
        description="Free-form address string (e.g. '1 Microsoft Way, Redmond, WA 98052')",
    )
):
    """
    Parse a free-form address into its components using libpostal

    Parameters:
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    """
    try:
        response = libpostal_expand_address(address)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/address/expand/libpostal/batch", tags=["Address"])
async def expand_address_libpostal_batch(addresses: List[Address]):
    """
    Expand addresses passed in as an array of addresses


    Parameters:
    - **addresses**: List of address objects
    """
    try:
        address_strings = [address.freeformAddress for address in addresses]
        executor = batch_executor.BatchExecutor(
            func=libpostal_expand_address, num_threads=5, delay=0.5
        )
        results = executor.execute_ordered(address_strings)
        return {"expanded_addresses": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/address/prompt/expansion", tags=["Address"])
async def update_address_expansion_prompt(prompt_data: SystemPrompt):
    """
    Update the address expansion system prompt dynamically at runtime.
    """
    try:
        config_manager.set_address_expansion_prompt(prompt_data.system_prompt)
        return {"message": "Address expansion system prompt updated successfully", "new prompt": prompt_data.system_prompt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/address/prompt/extraction", tags=["Address"])
async def update_address_extraction_prompt(prompt_data: SystemPrompt):
    """
    Update the address extraction system prompt dynamically at runtime.
    """
    try:
        config_manager.set_address_extraction_prompt(prompt_data.system_prompt)
        return {"message": "Address extraction system prompt updated successfully", "new prompt": prompt_data.system_prompt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/address/parse/llm", tags=["Address"])
async def parse_address_llm(address: str, llm_extractor: LLMEntityExtraction = Depends(get_llm_extractor)):
    """
    Parse a free-form address into its components using llm

    Parameters:
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    """
    try:
        response = llm_extractor.parse_address(address)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/address/parse/llm/batch", tags=["Address"])
async def expand_address_llm_batch(addresses: List[Address], llm_extractor: LLMEntityExtraction = Depends(get_llm_extractor)):
    """
    Parse addresses passed in as an array of addresses


    Parameters:
    - **addresses**: List of address objects
    """
    try:
        address_strings = [address.freeformAddress for address in addresses]
        executor = batch_executor.BatchExecutor(
            func=llm_extractor.parse_address, num_threads=5, delay=0.5
        )
        results = executor.execute_ordered(address_strings)
        return {"parsed_addresses": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/address/expand/llm", tags=["Address"])
async def expand_address_llm(address: str, llm_extractor: LLMEntityExtraction = Depends(get_llm_extractor)):
    """
    Parse a free-form address into its components using llm
    Parameters:
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    """
    try:
        response = llm_extractor.expand_address(address)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/address/expand/llm/batch", tags=["Address"])
async def expand_address_llm_batch(addresses: List[Address], llm_extractor: LLMEntityExtraction = Depends(get_llm_extractor)):
    """
    Expand addresses passed in as an array of addresses


    Parameters:
    - **addresses**: List of address objects
    """
    try:
        address_strings = [address.freeformAddress for address in addresses]
        executor = batch_executor.BatchExecutor(
            func=llm_extractor.expand_address, num_threads=5, delay=0.5
        )
        results = executor.execute_ordered(address_strings)
        return {"expanded_addresses": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/address/sanitize", response_model=AddressResponse, tags=["Address"])
async def sanitize_address(payload: AddressRequest):
    """
    **Process an address** using the specified geocoding strategy.
    \n
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    - **country_code**: ISO 3166-1 alpha-2 country code (e.g., "US")
    - **max_results**: Maximum number of results to return (default: 10)
    - **strategy**: Geocoding provider to use (azure_search, mapbox, etc.)
    - **use_libpostal**: Whether to sanitize the address using libpostal (default: True)
    """
    try:
        # Check the use_libpostal flag from the payload
        if payload.use_libpostal:
            # Strategy methods expect string input, expand_address returns a dict
            # only provide the expanded_address to the strategy
            expanded_address_dict = libpostal_expand_address(payload.address)
            if "expanded_address" in expanded_address_dict:
                expanded_address = expanded_address_dict["expanded_address"]
                logger.info(f"Expanded Address (libpostal): {expanded_address}")
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Expanded address not found in the response from libpostal",
                )
        else:
            expanded_address = payload.address

        # Get the requested strategy
        strategy = StrategyFactory.get_strategy(payload.strategy)

        # Execute geocoding
        address_results = strategy.geocode(
            address=expanded_address,
            country_code=payload.country_code,
            max_results=payload.max_results
        )

        # Build metadata
        metadata = {
            "query": payload.address,
            "country": payload.country_code,
            "timestamp": datetime.utcnow(),
            "totalResults": len(address_results),
        }

        return AddressResponse(metadata=metadata, addresses=address_results)

    except GeocodingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@app.post("/api/v1/address/sanitize/batch", tags=["Address"])
async def sanitize_address_batch(payloads: List[AddressRequest]):
    """
    Sanitize a batch of addresses using the specified geocoding strategy.
    
    Parameters:
    - **payloads**: List of AddressRequest objects
    """
    try:
        def process_address(payload: AddressRequest):
            try:
                # Check the use_libpostal flag from the payload
                if payload.use_libpostal:
                    expanded_address_dict = libpostal_expand_address(payload.address)
                    if "expanded_address" in expanded_address_dict:
                        expanded_address = expanded_address_dict["expanded_address"]
                    else:
                        raise ValueError("Expanded address not found in libpostal response")
                else:
                    expanded_address = payload.address
                
                # Get the requested strategy
                strategy = StrategyFactory.get_strategy(payload.strategy)
                
                # Execute geocoding
                address_results = strategy.geocode(
                    address=expanded_address,
                    country_code=payload.country_code,
                    max_results=payload.max_results
                )
                
                # Build metadata
                metadata = {
                    "query": payload.address,
                    "country": payload.country_code,
                    "timestamp": datetime.utcnow(),
                    "totalResults": len(address_results),
                }
                
                return AddressResponse(metadata=metadata, addresses=address_results)
            except Exception as e:
                return {"error": str(e), "query": payload.address}

        executor = batch_executor.BatchExecutor(func=process_address, num_threads=5, delay=0.5)
        results = executor.execute_ordered(payloads)
        return {"sanitized_addresses": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
