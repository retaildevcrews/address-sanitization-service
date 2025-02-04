# app/main.py
from datetime import datetime
from fastapi import FastAPI, HTTPException
from .schemas import AddressRequest, AddressResponse
from .strategies import StrategyFactory
from .exceptions import GeocodingError
from dotenv import load_dotenv
from .singleton_logger import SingletonLogger

load_dotenv('credentials.env')

logger = SingletonLogger().get_logger()

app = FastAPI(
    title="Address Sanitization Service",
    description="Sanitizes addresses using multiple geocoding providers",
    version="1.0.0",
    openapi_tags=[{
        "name": "Address",
        "description": "Address standardization and geocoding operations"
    }]
)

@app.get("/", include_in_schema=False)
def health_check():
    logger.info("Health check endpoint called")
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
    logger.info(f"Received request to sanitize address: {payload.address} using strategy: {payload.strategy}")
    try:
        # Get the requested strategy
        strategy = StrategyFactory.get_strategy(payload.strategy)
        logger.info(f"Using strategy: {payload.strategy}")

        # Execute geocoding
        address_results = strategy.geocode(
            address=payload.address,
            country_code=payload.country_code
        )
        logger.info(f"Geocoding results: {address_results}")

        # Build metadata
        metadata = {
            "query": payload.address,
            "country": payload.country_code,
            "timestamp": datetime.utcnow(),
            "totalResults": len(address_results)
        }

        return AddressResponse(
            metadata=metadata,
            addresses=address_results
        )

    except GeocodingError as e:
        logger.error(f"Geocoding error: {e.detail}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
