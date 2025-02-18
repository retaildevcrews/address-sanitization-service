# app/main.py
import json

from datetime import datetime

from fastapi import FastAPI, HTTPException

from .parsers_and_expanders.libpostal import parse_address as libpostal_parse_address
from .parsers_and_expanders.libpostal import expand_address as libpostal_expand_address
from .parsers_and_expanders.llm import LLMEntityExtraction

from .exceptions import GeocodingError
from .schemas import AddressRequest, AddressResponse
from .strategies import StrategyFactory
from .exceptions import GeocodingError
from .utils import batch_executor

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
)

llm_extractor = LLMEntityExtraction()


@app.get("/", include_in_schema=False)
def health_check():
    return {"status": "healthy", "version": app.version}


@app.get("/api/v1/address/parse/libpostal")
async def parse_address_libpostal(address: str):
    """
    Parse a free-form address into its components using libpostal

    Parameters:
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    """
    try:
        parsed = libpostal_parse_address(address)
        parsed_dict = {component[1]: component[0] for component in parsed}
        response = {"address": address, "parsed": parsed_dict}
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/address/expand/libpostal")
async def expand_address_libpostal(address: str):
    """
    Parse a free-form address into its components using libpostal

    Parameters:
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    """
    try:
        result = libpostal_expand_address(address)

        response = {"address": address, "expanded_address": result}
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/address/expand/libpostal/batch")
async def expand_address_libpostal_batch(addresses: list):
    """
    Expand addresses passed in as an array of addresses in the format:
    [
        {"address": "1 Microsoft Way, Redmond, WA 98052"},
        {"address": "2 Microsoft Way, Redmond, WA 98052"},
        {"address": "3 Microsoft Way, Redmond, WA 98052"}
    ]

    Parameters:
    - **addresses**: List of address objects
    """
    try:
        address_strings = [address["address"] for address in addresses]
        executor = batch_executor.BatchExecutor(
            func=libpostal_expand_address, num_threads=5, delay=0.5
        )
        results = []

        for address in address_strings:
            result = executor.execute(address)
            results.append(result)
        return {"expanded_addresses": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/address/parse/llm")
async def parse_address_llm(address: str):
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


@app.get("/api/v1/address/expand/llm")
async def expand_address_llm(address: str):
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


@app.post("/api/v1/address/expand/llm/batch")
async def expand_address_llm_batch(addresses: list):
    """
    Expand addresses passed in as an array of addresses in the format:
    [
        {"address": "1 Microsoft Way, Redmond, WA 98052"},
        {"address": "2 Microsoft Way, Redmond, WA 98052"},
        {"address": "3 Microsoft Way, Redmond, WA 98052"}
    ]

    Parameters:
    - **addresses**: List of address objects
    """
    try:
        address_strings = [address["address"] for address in addresses]
        executor = batch_executor.BatchExecutor(
            func=llm_extractor.expand_address, num_threads=5, delay=0.5
        )
        results = []

        for address in address_strings:
            result = executor.execute(address)
            results.append(result)
        return {"expanded_addresses": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/address", response_model=AddressResponse, tags=["Address"])
async def sanitize_address(payload: AddressRequest):
    """
    Process an address using the specified geocoding strategy

    Parameters:
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    - **country_code**: ISO 3166-1 alpha-2 country code (e.g., "US")
    - **strategy**: Geocoding provider to use (azure_search, mapbox, etc.)
    - **use_libpostal**: Whether to sanitize the address using libpostal (default: True)
    """
    try:
        print("Payload Address:", payload.address)

        # Check the use_libpostal flag from the payload
        if payload.use_libpostal:
            sanitized_address = libpostal_expand_address(payload.address)
            print("Sanitized Address (libpostal):", sanitized_address)
        else:
            sanitized_address = payload.address
            print("Skipping libpostal. Using raw address:", sanitized_address)

        # Get the requested strategy
        strategy = StrategyFactory.get_strategy(payload.strategy)

        # Execute geocoding using the (possibly) sanitized address
        address_results = strategy.geocode(
            address=sanitized_address, country_code=payload.country_code
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
