# app/strategies/azure_search.py
import os
import requests
from typing import List, Dict
from ..schemas import AddressResult, AddressPayload, Coordinates
from ..exceptions import GeocodingError
from . import GeocodingStrategy, StrategyFactory
from ..utilities import create_empty_address_result
import logging

logger = logging.getLogger(__name__)


@StrategyFactory.register("azure_search")
class AzureMapsStrategy(GeocodingStrategy):

    # Configuration constants
    API_BASE_URL = "https://atlas.microsoft.com/search/address/json"
    API_VERSION = "1.0"
    TIMEOUT = 5  # seconds
    REQUIRED_ENV_VARS = ["AZURE_MAPS_KEY"]

    def __init__(self):
        self._validate_environment()
        self.api_key = os.getenv("AZURE_MAPS_KEY")

    def _validate_environment(self):
        """Ensure required environment variables are present"""
        missing = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing:
            raise ValueError(
                f"Missing Azure Maps environment variables: {', '.join(missing)}"
            )

    def geocode(self, address: str, country_code: str, max_results: int) -> List[AddressResult]:
        """Main geocoding interface implementation"""
        try:
            response = self._make_api_call(address, country_code, max_results)
            return self._process_response(response, country_code, max_results)
        except GeocodingError:
            raise
        except Exception as e:
            raise GeocodingError(
                detail=f"Unexpected Azure Maps error: {str(e)}", status_code=500
            )

    def _make_api_call(self, address: str, country_code: str, max_results: int) -> Dict:
        """Handle API communication"""
        params = {
            "api-version": self.API_VERSION,
            "subscription-key": self.api_key,
            "query": address,
            "countrySet": country_code,
            "limit": max_results
        }

        try:
            response = requests.get(
                self.API_BASE_URL, params=params, timeout=self.TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise GeocodingError(
                detail="Azure Maps API request timed out", status_code=504
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            detail = f"Azure Maps API error: {e.response.text}"
            raise GeocodingError(detail=detail, status_code=status_code)
        except requests.exceptions.RequestException as e:
            raise GeocodingError(
                detail=f"Azure Maps connection error: {str(e)}", status_code=503
            )

    def _process_response(self, data: Dict, country_code: str, max_results: int) -> List[AddressResult]:
        """Process and validate API response"""
        logger.info(f"Processing Azure Maps response: {data}")
        if not isinstance(data, dict) or "results" not in data:
            raise GeocodingError(
                detail="Invalid Azure Maps API response format", status_code=500
            )

        results = data.get("results", [])

        # If no results found, return a "fallback" AddressResult instead of raising 404
        if not results:
            return create_empty_address_result(country_code, "azure_search")

        return [
            # default sort order is sufficiently good because it takes into account
            # the type of result in addition to score
            self._parse_result(r, country_code)
            for r in results[: max_results]
        ]

    def _parse_result(self, result: Dict, country_code: str) -> AddressResult:
        """Convert Azure-specific response to standard format"""
        address_info = result.get("address", {})
        position = result.get("position", {})
        logger.info(f"Parsing result: {result}")
        return AddressResult(
            confidenceScore=self._get_confidence_score(result),
            type=result.get("type", ""),
            address=AddressPayload(
                streetNumber=address_info.get("streetNumber", ""),
                streetName=address_info.get("streetName", ""),
                municipality=address_info.get("municipality", ""),
                municipalitySubdivision=address_info.get("municipalitySubdivision", ""),
                countrySecondarySubdivision=address_info.get(
                    "countrySecondarySubdivision", ""
                ),
                countryTertiarySubdivision=address_info.get(
                    "countryTertiarySubdivision", ""
                ),
                neighborhood=address_info.get("neighborhood", ""),
                postalCode=address_info.get("postalCode", ""),
                countryCode=self._get_country_code(address_info, country_code),
            ),
            freeformAddress=address_info.get("freeformAddress", ""),
            coordinates=Coordinates(
                lat=position.get("lat", 0.0), lon=position.get("lon", 0.0)
            ),
            serviceUsed="azure_search",
        )

    def _get_confidence_score(self, result: Dict) -> float:
        """Extract and validate confidence score"""
        score = result.get("score", 0.0)
        return max(0.0, min(1.0, float(score)))

    def _get_country_code(self, address_info: Dict, fallback_code: str) -> str:
        """Extract country code with fallback"""
        return address_info.get("countryCodeISO3", fallback_code).upper()
