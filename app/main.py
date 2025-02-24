# app/main.py
from contextlib import asynccontextmanager

from datetime import datetime
from fastapi import FastAPI, HTTPException, Query

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
)
from .strategies import StrategyFactory
from .exceptions import GeocodingError
from .utils import batch_executor

from typing import List

llm_extractor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_extractor
    try:
        llm_extractor = LLMEntityExtraction()
    except Exception as e:
        print(f"Failed to initialize LLMEntityExtraction: {e}")
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
        results = executor.execute(address_strings)
        return {"expanded_addresses": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/address/parse/llm", tags=["Address"])
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


@app.get("/api/v1/address/expand/llm", tags=["Address"])
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


@app.post("/api/v1/address/expand/llm/batch", tags=["Address"])
async def expand_address_llm_batch(addresses: List[Address]):
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
        results = executor.execute(address_strings)
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
                sanitized_address = expanded_address_dict["expanded_address"]
                print("Sanitized Address (libpostal):", sanitized_address)
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Expanded address not found in the response from libpostal",
                )
        else:
            sanitized_address = payload.address

        # Get the requested strategy
        strategy = StrategyFactory.get_strategy(payload.strategy)

        # Execute geocoding
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
