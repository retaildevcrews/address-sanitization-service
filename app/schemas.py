# app/schemas.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# ========================
# Request Schema
# ========================
class AddressRequest(BaseModel):
    address: str = Field(
        ...,
        example="1 Microsoft Way, Redmond, WA 98052",
        description="Free-form address string to geocode"
    )
    country_code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        example="US",
        description="ISO 3166-1 alpha-2 country code"
    )
    strategy: str = Field(
        "azure",
        example="azure",
        description="Geocoding strategy to use (azure, google, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "address": "1 Microsoft Way, Redmond, WA 98052",
                "country_code": "US",
                "strategy": "azure"
            }
        }

# ========================
# Component Schemas
# ========================
class Coordinates(BaseModel):
    lat: float = Field(..., example=47.641673)
    lon: float = Field(..., example=-122.125648)

class AddressPayload(BaseModel):
    streetNumber: str = Field(..., example="1", description="Street number component")
    streetName: str = Field(
        ...,
        example="Northeast One Microsoft Way",
        description="Full street name including directionals"
    )
    municipality: str = Field(..., example="Redmond", description="City or town name")
    municipalitySubdivision: str = Field(
        "",
        example="King County",
        description="County or district within municipality"
    )
    postalCode: str = Field(..., example="98052", description="ZIP/postal code")
    countryCode: str = Field(
        ...,
        min_length=2,
        max_length=3,
        example="US",
        description="ISO country code (2 or 3 character)"
    )

class AddressResult(BaseModel):
    confidenceScore: float = Field(
        ...,
        ge=0,
        le=1,
        example=0.9965,
        description="Confidence score from 0 (low) to 1 (high)"
    )
    address: AddressPayload
    freeformAddress: str = Field(
        ...,
        example="1 Microsoft Way, Redmond, WA 98052",
        description="Formatted full address string"
    )
    coordinates: Coordinates
    serviceUsed: str = Field(..., example="azure", description="Geocoding provider name")

class Metadata(BaseModel):
    query: str = Field(..., description="Original input query string")
    country: str = Field(..., description="Requested country filter")
    timestamp: datetime = Field(..., description="UTC timestamp of response")
    totalResults: int = Field(..., ge=0, description="Total number of matches found")

# ========================
# Response Schema
# ========================
class AddressResponse(BaseModel):
    metadata: Metadata
    addresses: List[AddressResult]

    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "query": "1 Microsoft Way, Redmond, WA 98052",
                    "country": "US",
                    "timestamp": "2025-01-29T00:37:23.869661",
                    "totalResults": 1
                },
                "addresses": [{
                    "confidenceScore": 0.9965,
                    "address": {
                        "streetNumber": "1",
                        "streetName": "Northeast One Microsoft Way",
                        "municipality": "Redmond",
                        "municipalitySubdivision": "",
                        "postalCode": "98052",
                        "countryCode": "US"
                    },
                    "freeformAddress": "1 Microsoft Way, Redmond, WA 98052",
                    "coordinates": {
                        "lat": 47.641673,
                        "lon": -122.125648
                    },
                    "serviceUsed": "azure"
                }]
            }
        }
