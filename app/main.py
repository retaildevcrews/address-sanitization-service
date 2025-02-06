# app/main.py
from datetime import datetime

from fastapi import FastAPI, HTTPException

from .exceptions import GeocodingError
from .schemas import AddressRequest, AddressResponse
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


@app.post("/api/v1/address", response_model=AddressResponse, tags=["Address"])
async def sanitize_address(payload: AddressRequest):
    """
    Process an address using the specified geocoding strategy

    Parameters:
    - **address**: Free-form address string (e.g., "1 Microsoft Way, Redmond, WA 98052")
    - **country_code**: ISO 3166-1 alpha-2 country code (e.g., "US")
    - **strategy**: Geocoding provider to use (azure, google, etc.)
    """
    try:
        # Get the requested strategy
        strategy = StrategyFactory.get_strategy(payload.strategy)

        # Execute geocoding
        address_results = strategy.geocode(
            address=payload.address, country_code=payload.country_code
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
