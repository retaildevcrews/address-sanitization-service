# app/schemas.py

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field

VALID_STRATEGIES = ["azure", "google", "mapbox"]

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
        default="azure",
        example="azure",
        description=f"Geocoding service provider to use. Options: {', '.join(VALID_STRATEGIES)}"
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
    lat: float = Field(
        ...,
        example=47.641673,
        description="Latitude in decimal degrees (WGS 84)"
    )
    lon: float = Field(
        ...,
        example=-122.125648,
        description="Longitude in decimal degrees (WGS 84)"
    )

class AddressPayload(BaseModel):
    streetNumber: str = Field(
        ...,
        example="1",
        description="Numeric portion of street address"
    )
    streetName: str = Field(
        ...,
        example="Northeast One Microsoft Way",
        description="Official street name including direction prefix/suffix"
    )
    municipality: str = Field(
        ...,
        example="Redmond",
        description="Primary municipal jurisdiction (city/town)"
    )
    municipalitySubdivision: str = Field(
        default="",
        example="King County",
        description="Secondary municipal area (county/district)"
    )
    postalCode: str = Field(
        ...,
        example="98052",
        description="Postal code in local format"
    )
    countryCode: str = Field(
        ...,
        min_length=2,
        max_length=3,
        example="US",
        description="ISO country code (2 or 3 character format)"
    )

class AddressResult(BaseModel):
    confidenceScore: float = Field(
        ...,
        ge=0,
        le=1,
        example=0.9965,
        description="Normalized confidence score (1 = highest certainty)"
    )
    address: AddressPayload = Field(
        ...,
        description="Structured address components"
    )
    freeformAddress: str = Field(
        ...,
        example="1 Microsoft Way, Redmond, WA 98052",
        description="Complete address formatted per provider standards"
    )
    coordinates: Coordinates = Field(
        ...,
        description="Geographic coordinates of the location"
    )
    serviceUsed: str = Field(
        ...,
        example="azure",
        description="Identifier of the geocoding service provider"
    )

class Metadata(BaseModel):
    query: str = Field(
        ...,
        description="Original address query as received by the API"
    )
    country: str = Field(
        ...,
        description="Country code filter used in the search"
    )
    timestamp: datetime = Field(
        ...,
        description="UTC timestamp of API response generation"
    )
    totalResults: int = Field(
        ...,
        ge=0,
        description="Total number of matching addresses found"
    )

# ========================
# Response Schema
# ========================
class AddressResponse(BaseModel):
    metadata: Metadata = Field(
        ...,
        description="Summary information about the request"
    )
    addresses: List[AddressResult] = Field(
        ...,
        description="Ordered list of geocoding results (highest confidence first)"
    )

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
                        "municipalitySubdivision": "King County",
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
