import os
import requests
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

# ========================
# Configuration
# ========================
AZURE_MAPS_KEY = os.getenv("AZURE_MAPS_KEY", "YOUR_AZURE_MAPS_KEY")

# ========================
# Request Model
# ========================
class AddressRequest(BaseModel):
    address: str
    country_code: str
    strategy: str

# ========================
# New Response Models
# ========================

class Coordinates(BaseModel):
    lat: float
    lon: float

class AddressPayload(BaseModel):
    streetNumber: str
    streetName: str
    municipality: str
    municipalitySubdivision: str
    postalCode: str
    countryCode: str

class AddressResult(BaseModel):
    confidenceScore: float
    address: AddressPayload
    freeformAddress: str
    coordinates: Coordinates
    serviceUsed: str
    status: str

class Metadata(BaseModel):
    query: str
    country: str
    timestamp: datetime
    totalResults: int

class AddressResponse(BaseModel):
    metadata: Metadata
    addresses: List[AddressResult]

# ========================
# FastAPI Initialization
# ========================
app = FastAPI(
    title="Address Sanitization Service",
    description="A minimal FastAPI app that sanitizes addresses via Azure Maps.",
    version="0.1.0",
)

# ========================
# Health Check Endpoint
# ========================
@app.get("/", include_in_schema=False)
def health_check():
    return {"status": "healthy", "version": app.version}

# ========================
# Main Endpoint
# ========================
@app.post("/api/v1/address", response_model=AddressResponse)
def sanitize_address(payload: AddressRequest):
    """
    Receive a JSON payload with the following fields:
    {
      "address": "1 Microsoft Way, Redmond, WA 98052",
      "country_code": "US",
      "strategy": "azure"
    }

    Currently, we only support "azure" as a strategy.
    This endpoint returns a JSON response with metadata and a list of addresses.
    """
    # Validate the strategy
    if payload.strategy.lower() != "azure":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported strategy: {payload.strategy}. Only 'azure' is supported.",
        )

    # Call Azure Maps API
    azure_url = "https://atlas.microsoft.com/search/address/json"
    params = {
        "api-version": "1.0",
        "subscription-key": AZURE_MAPS_KEY,
        "query": payload.address,
        "countrySet": payload.country_code
    }

    try:
        response = requests.get(azure_url, params=params, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

    data = response.json()
    results = data.get("results", [])

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No matching address found from Azure Maps."
        )

    # Sort results by descending score (so highest confidence is first)
    sorted_results = sorted(results, key=lambda r: r.get("score", 0.0), reverse=True)

    # Build the list of AddressResult objects
    address_objects = []
    for result in sorted_results:
        address_info = result.get("address", {})
        address_objects.append(
            AddressResult(
                confidenceScore=result.get("score", 0.0),
                address=AddressPayload(
                    streetNumber=address_info.get("streetNumber", ""),
                    streetName=address_info.get("streetName", ""),
                    municipality=address_info.get("municipality", ""),
                    municipalitySubdivision=address_info.get("municipalitySubdivision", ""),
                    postalCode=address_info.get("postalCode", ""),
                    countryCode=address_info.get("countryCodeISO3", payload.country_code)
                ),
                freeformAddress=address_info.get("freeformAddress", payload.address),
                coordinates=Coordinates(
                    lat=result["position"]["lat"],
                    lon=result["position"]["lon"]
                ),
                serviceUsed="azure",
                status="SUCCESS",
            )
        )

    # Construct metadata
    metadata = Metadata(
        query=payload.address,
        country=payload.country_code,
        timestamp=datetime.utcnow(),
        totalResults=len(address_objects)
    )

    # Return the final structured response
    return AddressResponse(
        metadata=metadata,
        addresses=address_objects
    )
