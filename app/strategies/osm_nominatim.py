# app/strategies/osm_nominatim.py
import os
import requests
import logging
from typing import List, Dict
from ..schemas import AddressResult, AddressPayload, Coordinates
from ..exceptions import GeocodingError
from . import GeocodingStrategy, StrategyFactory
from ..utilities import create_empty_address_result
from ..singleton_logger import SingletonLogger

logger = SingletonLogger().get_logger()



@StrategyFactory.register("osm_nominatim")
class NominatimStrategy(GeocodingStrategy):
    # Configuration constants
    API_BASE_URL = "https://nominatim.openstreetmap.org/search"
    TIMEOUT = 5  # seconds
    MAX_RESULTS = 10
    REQUIRED_ENV_VARS = []  # Nominatim (OpenStreetMap) doesn't require an API key

    def __init__(self):
        self._validate_environment()

    def _validate_environment(self):
        """Ensure required environment variables are present"""
        missing = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing:
            logger.error(f"Missing environment variables: {', '.join(missing)}")
            raise ValueError(
                f"Missing environment variables: {', '.join(missing)}"
            )
        logger.info("Environment variables validated successfully")

    def geocode(self, address: str, country_code: str) -> List[AddressResult]:
        """Main geocoding interface implementation"""
        logger.info(f"Geocoding address: {address} for country: {country_code}")
        try:
            response = self._make_api_call(address, country_code)
            return self._process_response(response, country_code)
        except GeocodingError as e:
            logger.error(f"GeocodingError: {e.detail}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise GeocodingError(
                detail=f"Unexpected Nominatim (OpenStreetMap) error: {str(e)}",
                status_code=500
            )

    def _make_api_call(self, address: str, country_code: str) -> Dict:
        """Handle API communication"""
        params = {
            "q": address,
            "countrycodes": country_code.lower(),
            "format": "jsonv2",
            "limit": self.MAX_RESULTS,
            "addressdetails": 1,
            "namedetails": 1,
        }

        try:
            logger.info(f"Making API call to {self.API_BASE_URL} with params: {params}")
            response = requests.get(
                self.API_BASE_URL,
                params=params,
                timeout=self.TIMEOUT,
                headers={"User-Agent": "AddressSanitizationService/1.0"}
            )
            response.raise_for_status()
            logger.info("API call successful")
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Nominatim (OpenStreetMap) API request timed out")
            raise GeocodingError(
                detail="Nominatim (OpenStreetMap) API request timed out",
                status_code=504
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            detail = f"Nominatim API error: {e.response.text}"
            logger.error(f"HTTPError: {detail}")
            raise GeocodingError(detail=detail, status_code=status_code)
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error: {str(e)}")
            raise GeocodingError(
                detail=f"Nominatim (OpenStreetMap) connection error: {str(e)}",
                status_code=503
            )

    def _process_response(self, data: List[Dict], country_code: str) -> List[AddressResult]:
        """Process and validate API response"""
        if not isinstance(data, list):
            logger.error("Invalid API response format")
            raise GeocodingError(
                detail="Invalid Nominatim (OpenStreetMap) API response format",
                status_code=500
            )

        # If no data returned, return a fallback result instead of a 404 error
        if not data:
            logger.info("No data returned from API, returning fallback result")
            return create_empty_address_result(country_code, "osm_nominatim")

        # Sort by "importance" (descending)
        sorted_data = sorted(
            data,
            key=lambda x: float(x.get("importance", 0)),
            reverse=True
        )

        logger.info(f"Processing {len(sorted_data)} results")
        return [
            self._parse_result(r, country_code) for r in sorted_data
        ]

    def _parse_result(self, result: Dict, country_code: str) -> AddressResult:
        """Convert Nominatim-specific response to standard format"""
        address_info = result.get("address", {})

        logger.debug(f"Parsing result: {result}")
        return AddressResult(
            confidenceScore=self._calculate_confidence_score(result),
            address=AddressPayload(
                streetNumber=address_info.get("house_number", ""),
                streetName=address_info.get("road", ""),
                municipality=(
                    address_info.get("city", "")
                    or address_info.get("town", "")
                ),
                municipalitySubdivision=address_info.get("county", ""),
                postalCode=address_info.get("postcode", ""),
                countryCode=address_info.get("country_code", country_code).upper()
            ),
            freeformAddress=result.get("display_name", ""),
            coordinates=Coordinates(
                lat=float(result.get("lat", 0.0)),
                lon=float(result.get("lon", 0.0))
            ),
            serviceUsed="osm_nominatim"
        )

    def _calculate_confidence_score(self, result: Dict) -> float:
        """Convert Nominatim importance to a bounded confidence score (0.0 to 1.0)."""
        importance = float(result.get("importance", 0.0))
        score = min(1.0, max(0.0, importance))
        logger.debug(f"Calculated confidence score: {score}")
        return score
