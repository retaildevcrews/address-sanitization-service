# app/strategies/google_geocode.py
import os
import requests
from typing import List, Dict
from ..schemas import AddressResult, AddressPayload, Coordinates
from ..exceptions import GeocodingError
from . import GeocodingStrategy, StrategyFactory


@StrategyFactory.register("google_geocode")
class GoogleGeocodeStrategy(GeocodingStrategy):
    # Configuration constants
    API_BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    TIMEOUT = 5  # seconds
    MAX_RESULTS = 10
    REQUIRED_ENV_VARS = ["GOOGLE_MAPS_API_KEY"]
    # Map Google address components to our schema
    COMPONENT_MAP = {
        "street_number": "streetNumber",
        "route": "streetName",
        "locality": "municipality",
        "administrative_area_level_2": "municipalitySubdivision",
        "postal_code": "postalCode",
        "country": "countryCode",
    }

    def __init__(self):
        self._validate_environment()
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    def _validate_environment(self):
        """Ensure required environment variables are present"""
        missing = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing:
            raise ValueError(
                f"Missing Google Maps environment variables: {', '.join(missing)}"
            )

    def geocode(self, address: str, country_code: str) -> List[AddressResult]:
        """Main geocoding interface implementation"""
        try:
            response = self._make_api_call(address, country_code)
            return self._process_response(response, country_code)
        except GeocodingError:
            raise
        except Exception as e:
            raise GeocodingError(
                detail=f"Unexpected Google Maps error: {str(e)}", status_code=500
            )

    def _make_api_call(self, address: str, country_code: str) -> Dict:
        """Handle API communication"""
        params = {
            "address": address,
            "components": f"country:{country_code}",
            "key": self.api_key,
            "language": "en",
            "region": country_code.lower(),
        }
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
        if not isinstance(data, dict) or "results" not in data:
            raise GeocodingError(
                detail="Invalid Google Maps API response format", status_code=500
            )
        results = data.get("results", [])
        if not results:
            raise GeocodingError(
                detail="No results found in Google Maps response", status_code=404
            )

        parsed_results = [self._parse_result(r, country_code) for r in results]
        # Sort results by confidence score
        # and return the top N results
        if len(parsed_results) > self.MAX_RESULTS:
            parsed_results = sorted(
                parsed_results,
                key=lambda x: x.confidenceScore,
                reverse=True,
            )[: self.MAX_RESULTS]
        return parsed_results

    def _parse_result(self, result: Dict, country_code: str) -> AddressResult:
        """Convert Google-specific response to standard format"""
        components = self._extract_components(result)
        geometry = result.get("geometry", {})
        location = geometry.get("location", {})
        location_type = result.get("geometry", {}).get("location_type", "")
        address = AddressPayload(
            streetNumber=components.get("streetNumber", ""),
            streetName=components.get("streetName", ""),
            municipality=components.get("municipality", ""),
            municipalitySubdivision=components.get("municipalitySubdivision", ""),
            postalCode=components.get("postalCode", ""),
            countryCode=components.get("countryCode", country_code.upper()),
        )
        address_result = AddressResult(
            address=address,
            confidenceScore=self._calculate_confidence_score(address, location_type),
            freeformAddress=result.get("formatted_address", ""),
            type=location_type,
            coordinates=Coordinates(
                lat=location.get("lat", 0.0), lon=location.get("lng", 0.0)
            ),
            serviceUsed="google_geocode",
        )
        return address_result

    def _extract_components(self, result: Dict) -> Dict:
        """Map Google address components to our schema"""
        components = {}
        for component in result.get("address_components", []):
            for type in component["types"]:
                if type in self.COMPONENT_MAP:
                    field = self.COMPONENT_MAP[type]
                    components[field] = component["short_name"]
        return components

    def _calculate_confidence_score(
        self, address: AddressPayload, location_type: str
    ) -> float:
        """
        Calculate confidence score based on address components and location type.
        The score is a combination of the address type and the number of components
        present in the address. Rooftop addresses are considered the most reliable,
        while approximate addresses are less reliable.
        """
        score_map = {
            "ROOFTOP": 1.0,
            "RANGE_INTERPOLATED": 0.9,
            "GEOMETRIC_CENTER": 0.75,
            "APPROXIMATE": 0.5,
        }
        address_type_score = score_map.get(location_type, 0.5)
        component_count = sum(
            1
            for component in [
                address.streetNumber,
                address.streetName,
                address.municipality,
                address.municipalitySubdivision,
                address.postalCode,
                address.countryCode,
            ]
            if component
        )
        address_components_score = component_count / 6.0
        # Combine the scores
        combined_score = address_type_score * address_components_score
        return combined_score
