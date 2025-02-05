# app/strategies/mapbox.py
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

@StrategyFactory.register("mapbox")
class MapboxMapsStrategy(GeocodingStrategy):
    # Configuration constants
    API_BASE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/"
    TIMEOUT = 5  # seconds
    MAX_RESULTS = 10
    REQUIRED_ENV_VARS = ["MAPBOX_MAPS_KEY"]

    def __init__(self):
        self._validate_environment()
        self.api_key = os.getenv("MAPBOX_MAPS_KEY")
        logger.info("MapboxMapsStrategy initialized with API key")

    def _validate_environment(self):
        """Ensure required environment variables are present"""
        missing = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing:
            logger.error(f"Missing environment variables: {', '.join(missing)}")
            raise ValueError(
                f"Missing Mapbox Maps environment variables: {', '.join(missing)}"
            )

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
                detail=f"Unexpected Mapbox Maps error: {str(e)}",
                status_code=500
            )

    def _make_api_call(self, address: str, country_code: str) -> Dict:
        """Handle API communication"""
        query = address + '.json'
        params = {
            'access_token': self.api_key,
            'country': country_code,
            "limit": self.MAX_RESULTS
        }

        logger.info(f"Making API call to Mapbox for address: {address}")
        try:
            response = requests.get(self.API_BASE_URL + query,
                                    params=params,
                                    timeout=self.TIMEOUT)
            response.raise_for_status()
            logger.info("API call successful")
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Mapbox Maps API request timed out")
            raise GeocodingError(
                detail="Mapbox Maps API request timed out",
                status_code=504
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            detail = f"Mapbox Maps API error: {e.response.text}"
            logger.error(f"HTTPError: {detail}")
            raise GeocodingError(detail=detail, status_code=status_code)
        except requests.exceptions.RequestException as e:
            logger.error(f"RequestException: {str(e)}")
            raise GeocodingError(
                detail=f"Mapbox Maps connection error: {str(e)}",
                status_code=503
            )

    def _process_response(self, data: Dict, country_code: str) -> List[AddressResult]:
        """Process and validate API response"""
        logger.info("Processing API response")
        if not isinstance(data, dict) or "features" not in data:
            logger.error("Invalid API response format")
            raise GeocodingError(
                detail="Invalid Mapbox Maps API response format",
                status_code=500
            )

        results = data.get("features", [])

        # If no results found, return a "fallback" AddressResult instead of raising 404
        if not results:
            logger.info("No results found, returning fallback address result")
            return create_empty_address_result(country_code, "mapbox")
        return [
            self._parse_result(r, country_code)
            for r in sorted(
                results,
                key=lambda x: x.get("relevance", 0.0),
                reverse=True
            )
        ]

    def _parse_result(self, result: Dict, country_code: str) -> AddressResult:
        """Convert Mapbox-specific response to standard format"""
        logger.info("Parsing result from API response")

        def extract_postal_code_and_municipality(context):
            postal_code = ""
            municipality = ""

            for item in context:
                if item['id'].startswith('postcode.'):
                    postal_code = item['text']
                elif item['id'].startswith('place.'):
                    municipality = item['text']

            return postal_code, municipality

        postalCode, municipality = extract_postal_code_and_municipality(result['context'])
        address_obj = AddressPayload(
                    streetNumber=result.get("address", ""),
                    streetName=result.get("text", ""),
                    postalCode=postalCode,
                    municipality=municipality,
                    countryCode= country_code,
                    municipalitySubdivision=result.get("municipalitySubdivision", "")
                )
        address_result = AddressResult(confidenceScore=result.get("relevance", 0.0),
                                        address=address_obj,
                                        freeformAddress= result.get("place_name", ""),
                                        coordinates=Coordinates(
                                            lat=result['center'][1],
                                            lon=result['center'][0]
                                        ),
                                        serviceUsed="mapbox"
                                    )

        return address_result
