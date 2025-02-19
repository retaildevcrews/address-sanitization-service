# app/schemas.py

from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel, Field

VALID_STRATEGIES = [
    "azure_search",
    "azure_geocode",
    "mapbox",
    "loqate",
    "osm_nominatim",
]


class Address(BaseModel):
    freeformAddress: str = Field(
        ...,
        example="1 Microsoft Way, Redmond, WA 98052",
        description="Free-form address string to geocode",
    )

VALID_STRATEGIES = ["azure_search", "azure_geocode", "mapbox", "loqate", "osm_nominatim"]


# ========================
# AddressRequest Schema
# ========================
class AddressRequest(BaseModel):
    """
    Represents the request body for the POST /api/v1/address endpoint.
    Includes the free-form address to geocode, the country code,
    the geocoding strategy to use, and a flag to indicate whether
    libpostal should be used for address expansion.
    """
    address: str = Field(
        ...,
        example="1 Microsoft Way, Redmond, WA 98052",
        description="Free-form address string to geocode",
    )
    country_code: str = Field(
        ...,
        min_length=2,
        max_length=2,
        example="US",
        description="ISO 3166-1 alpha-2 country code",
    )
    strategy: str = Field(
        default="azure_search",
        example="azure_search",
        description=f"Geocoding service provider to use. Options: {', '.join(VALID_STRATEGIES)}",
        description=f"Geocoding provider to use. Options: {', '.join(VALID_STRATEGIES)}"
    )
    use_libpostal: bool = Field(
        default=True,
        example=True,
        description="Whether to sanitize/expand the address using libpostal"
    )

    class Config:
        """
        Pydantic model configuration for AddressRequest.
        """
        json_schema_extra = {
            "example": {
                "address": "1 Microsoft Way, Redmond, WA 98052",
                "country_code": "US",
                "strategy": "azure_search",
                "use_libpostal": True,
            }
        }



# ========================
# Component Schemas
# ========================
class Coordinates(BaseModel):
    """
    Represents latitude and longitude in decimal degrees (WGS 84).
    """
    lat: float = Field(
        ..., example=47.641673, description="Latitude in decimal degrees (WGS 84)"
    )
    lon: float = Field(
        ..., example=-122.125648, description="Longitude in decimal degrees (WGS 84)"
    )



class AddressPayload(BaseModel):
    """
    Represents the structured address components.
    """
    streetNumber: str = Field(
        ..., example="1", description="Numeric portion of street address"
    )
    streetName: str = Field(
        ...,
        example="Northeast One Microsoft Way",
        description="Official street name (including any direction)"
    )
    municipality: str = Field(
        ..., example="Redmond", description="Primary municipal jurisdiction (city/town)"
    )
    municipalitySubdivision: str = Field(
        default="",
        example="King County",
        description="Secondary municipal area (county/district)",
    )
    postalCode: str = Field(
        ..., example="98052", description="Postal code in local format"
    )
    countryCode: str = Field(
        ...,
        min_length=2,
        max_length=3,
        example="US",
        description="ISO country code (2 or 3 character format)",
        description="ISO country code (2- or 3-character format)"
    )



class AddressResult(BaseModel):
    """
    Represents one geocoding match, including a confidence score,
    structured address data, and coordinates.
    """
    confidenceScore: float = Field(
        ...,
        ge=0,
        le=1,
        example=0.9965,
        description="Normalized confidence score (1 = highest certainty)",
    )
    address: AddressPayload = Field(..., description="Structured address components")
    freeformAddress: str = Field(
        ...,
        example="1 Microsoft Way, Redmond, WA 98052",
        description="Complete address formatted by the provider"
    )
    coordinates: Coordinates = Field(
        ..., description="Geographic coordinates of the location"
    )
    serviceUsed: str = Field(
        ...,
        example="azure_search",
        description="Identifier of the geocoding service provider",
    )



class Metadata(BaseModel):
    """
    Provides additional context about the geocoding request and response.
    """
    query: str = Field(
        ...,
        description="Original address query as received by the API"
    )
    country: str = Field(
        ...,
        description="Country code filter used in the search"
    )
    timestamp: datetime = Field(
        ..., description="UTC timestamp of API response generation"
    )
    totalResults: int = Field(
        ..., ge=0, description="Total number of matching addresses found"
    )



# ========================
# AddressResponse Schema
# ========================
class AddressResponse(BaseModel):
    """
    Represents the response from the /api/v1/address endpoint,
    containing metadata and a list of possible address matches.
    """
    metadata: Metadata = Field(
        ...,
        description="Summary information about the request"
    )
    addresses: List[AddressResult] = Field(
        ..., description="Ordered list of geocoding results (highest confidence first)"
    )

    class Config:
        """
        Pydantic model configuration for AddressResponse.
        """
        json_schema_extra = {
            "example": {
                "metadata": {
                    "query": "1 Microsoft Way, Redmond, WA 98052",
                    "country": "US",
                    "timestamp": "2025-01-29T00:37:23.869661",
                    "totalResults": 1,
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
                    "serviceUsed": "azure_search"
                }]
            }
        }


# ============================
# ExpandAddressResponse Schema
# ============================
class ExpandAddressResponse(BaseModel):
    """
    Response model for the /api/v1/expand_address endpoint.
    Contains the original address and the expanded version
    derived from libpostal.
    """
    address: str = Field(
        ...,
        description="Original address string"
    )
    expanded_address: str = Field(
        ...,
        description="First expanded version of the address from libpostal"
    )

    class Config:
        """
        Pydantic model configuration for ExpandAddressResponse.
        """
        json_schema_extra = {
            "example": {
                "address": "1 Microsoft Way, Redmond, WA 98052",
                "expanded_address": "1 microsoft way redmond washington 98052"
            }
        }


# ===========================
# ParseAddressResponse Schema
# ===========================
class ParseAddressResponse(BaseModel):
    """
    Response model for the /api/v1/parse_address endpoint.
    Contains the original address plus a dictionary of
    key-value pairs representing parsed address components.
    """
    address: str = Field(
        ...,
        description="Original address string"
    )
    parsed: Dict[str, str] = Field(
        ...,
        description="Key-value pairs representing parsed address components (dynamic keys)"
    )

    class Config:
        """
        Pydantic model configuration for ParseAddressResponse.
        """
        json_schema_extra = {
            "example": {
                "address": "1 Microsoft Way, Redmond, WA 98052",
                "parsed": {
                    "house_number": "1",
                    "road": "microsoft way",
                    "city": "redmond",
                    "state": "wa",
                    "postcode": "98052"
                }
            }
        }
