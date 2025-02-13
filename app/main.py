# app/main.py

from datetime import datetime
from fastapi import FastAPI, HTTPException, Query

from .utils.libpostal import parse_address as libpostal_parse_address
from .utils.libpostal import expand_address as libpostal_expand_address

from .exceptions import GeocodingError
from .schemas import (
    AddressRequest,
    AddressResponse,
    ExpandAddressResponse,
    ParseAddressResponse,
)
from .strategies import StrategyFactory

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

@app.get("/", include_in_schema=False)
def health_check():
    return {"status": "healthy", "version": app.version}


@app.get("/api/v1/parse_address",
         response_model=ParseAddressResponse,
         tags=["Address"])
async def parse_address(address: str = Query(...,
                                             description="Free-form address string (e.g. '1 Microsoft Way, Redmond, WA 98052')")):
    """
    **Parse a free-form address** into its components using libpostal.
    \n
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    """
    try:
        parsed = libpostal_parse_address(address)
        parsed_dict = {component[1]: component[0] for component in parsed}
        response = {
            "address": address,
            "parsed": parsed_dict
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/expand_address",
         response_model=ExpandAddressResponse,
         tags=["Address"])
async def expand_address(address: str = Query(...,
                                              description="Free-form address string (e.g. '1 Microsoft Way, Redmond, WA 98052')")):
    """
    **Expand/normalize a free-form address** using libpostal.
    \n
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    """
    try:
        result = libpostal_expand_address(address)
        response = {
            "address": address,
            "expanded_address": result
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/address",
          response_model=AddressResponse,
          tags=["Address"])
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
            sanitized_address = libpostal_expand_address(payload.address)
        else:
            sanitized_address = payload.address

        # Get the requested strategy
        strategy = StrategyFactory.get_strategy(payload.strategy)

        # Execute geocoding
        address_results = strategy.geocode(
            address=sanitized_address,
            country_code=payload.country_code
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
