# app/main.py
from datetime import datetime

from fastapi import FastAPI, HTTPException

from .exceptions import GeocodingError
from .schemas import AddressRequest, AddressResponse
from .strategies import StrategyFactory
from .exceptions import GeocodingError
from .utils.address_sanitizer import sanitize_with_libpostal

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
            sanitized_address = sanitize_with_libpostal(payload.address)
            print("Sanitized Address (libpostal):", sanitized_address)
        else:
            sanitized_address = payload.address
            print("Skipping libpostal. Using raw address:", sanitized_address)

        # Get the requested strategy
        strategy = StrategyFactory.get_strategy(payload.strategy)

        # Execute geocoding using the (possibly) sanitized address
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
