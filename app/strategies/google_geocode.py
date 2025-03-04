# app/strategies/Google.py
import os
import requests
from typing import List, Dict
from ..schemas import AddressResult, AddressPayload, Coordinates
from ..exceptions import GeocodingError
from . import GeocodingStrategy, StrategyFactory
from ..utilities import create_empty_address_result
import logging

logger = logging.getLogger(__name__)


@StrategyFactory.register("google_geocode")
class GoogleMapsStrategy(GeocodingStrategy):
    # Configuration constants
    API_BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    TIMEOUT = 5  # seconds
    MAX_RESULTS = 10
    REQUIRED_ENV_VARS = ["GOOGLE_API_KEY"]

    def __init__(self):
        self._validate_environment()
        self.api_key = os.getenv("GOOGLE_API_KEY")

    def _validate_environment(self):
        """Ensure required environment variables are present"""
        missing = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing:
            raise ValueError(
                f"Missing google api key environment variables: {', '.join(missing)}"
            )

    def geocode(self, address: str, country_code: str) -> List[AddressResult]:
        """Main geocoding interface implementation"""
        try:
            response = self._make_api_call(address, country_code)
            return self._process_response(response, country_code)
        except GeocodingError:
            raise
        except Exception as e:
            raise GeocodingError(detail=f"Unexpected error: {str(e)}", status_code=500)

    def _make_api_call(self, address: str, country_code: str) -> Dict:
        """Handle API communication"""

        params = {"key": self.api_key, "address": address}

        try:
            response = requests.get(
                self.API_BASE_URL, params=params, timeout=self.TIMEOUT
            )

            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise GeocodingError(
                detail="Google Maps API request timed out", status_code=504
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            detail = f"Google Maps API error: {e.response.text}"
            raise GeocodingError(detail=detail, status_code=status_code)
        except requests.exceptions.RequestException as e:
            raise GeocodingError(
                detail=f"Google Maps connection error: {str(e)}", status_code=503
            )

    def _process_response(self, data: Dict, country_code: str) -> List[AddressResult]:
        """Process and validate API response"""
        logger.error(f"Processing Google Maps response: {data}")
        if not isinstance(data, dict) or "results" not in data:
            raise GeocodingError(
                detail="Invalid Google Maps API response format", status_code=500
            )

        results = data.get("results", [])

        # If no results found, return a "fallback" AddressResult instead of raising 404
        if not results:
            return create_empty_address_result(country_code, "Google")
        return [
            self._parse_result(r, country_code)
            for r in sorted(
                results, key=lambda x: x.get("relevance", 0.0), reverse=True
            )
        ]

    def _parse_result(self, result: Dict, country_code: str) -> AddressResult:
        """Convert Google-specific response to standard format"""
        address_components = result.get("address_components", [])
        formatted_address = result.get("formatted_address", "")
        coordinates = result.get("geometry", {}).get("location", {})
        lat = coordinates.get("lat", 0.0)
        lon = coordinates.get("lng", 0.0)
        if not lat or not lon:
            raise GeocodingError(
                detail="Missing coordinates in Google Maps API response",
                status_code=500,
            )
        street_number = ""
        street_name = ""
        postal_code = ""
        municipality = ""
        country_code = ""
        municipality_subdivision = ""
        types = result.get("types", [])
        types = result.get("types", [])
        type = ", ".join(types)
        for component in address_components:
            types = component.get("types", [])
            if "street_number" in types:
                street_number = component.get("long_name", "")
            elif "route" in types:
                street_name = component.get("long_name", "")
            elif "locality" in types:
                municipality = component.get("long_name", "")
            elif "country" in types:
                country_code = component.get("short_name", "")
            elif "postal_code" in types:
                postal_code = component.get("long_name", "")
            elif "administrative_area_level_2" in types:
                municipality_subdivision = component.get("long_name", "")

        address_obj = AddressPayload(
            streetNumber=street_number,
            streetName=street_name,
            postalCode=postal_code,
            municipality=municipality,
            countryCode=country_code,
            municipalitySubdivision=municipality_subdivision,
        )
        address_result = AddressResult(
            confidenceScore=0.0,
            type=type,
            address=address_obj,
            freeformAddress=formatted_address,
            coordinates=Coordinates(lat=lat, lon=lon),
            serviceUsed="google_geocode",
        )

        return address_result
