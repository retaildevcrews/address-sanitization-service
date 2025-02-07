# app/strategies/azure_geocode.py
import os
from typing import Dict, List

import requests
from requests import Session

from ..exceptions import GeocodingError
from ..schemas import AddressPayload, AddressResult, Coordinates
from ..utilities import create_empty_address_result
from . import GeocodingStrategy, StrategyFactory


@StrategyFactory.register("azure_geocode")
class AzureMapsStrategy(GeocodingStrategy):
    API_BASE_URL = "https://atlas.microsoft.com/geocode"
    API_VERSION = "2023-06-01"
    TIMEOUT = 5  # seconds
    MAX_RESULTS = 10
    REQUIRED_ENV_VARS = ["AZURE_MAPS_KEY"]

    def __init__(self):
        self._validate_environment()
        self.api_key = os.getenv("AZURE_MAPS_KEY")
        self.session = Session()

    def _validate_environment(self) -> None:
        """Ensure required environment variables are present"""
        missing = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing:
            raise ValueError(
                f"Missing Azure Maps environment variables: {', '.join(missing)}"
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
                detail=f"Unexpected Azure Maps error: {str(e)}", status_code=500
            )

    def _make_api_call(self, address: str, country_code: str) -> Dict:
        """Handle API communication"""
        params = {
            "api-version": self.API_VERSION,
            "query": address,
            "countrySet": country_code,
            "limit": self.MAX_RESULTS,
        }
        headers = {"subscription-key": self.api_key}

        try:
            response = self.session.get(
                self.API_BASE_URL, headers=headers, params=params, timeout=self.TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise GeocodingError(
                detail="Azure Maps API request timed out", status_code=504
            )
        except requests.exceptions.HTTPError as e:
            raise GeocodingError(
                detail=f"Azure Maps API error: {e.response.text}",
                status_code=e.response.status_code,
            )
        except requests.exceptions.RequestException as e:
            raise GeocodingError(
                detail=f"Azure Maps connection error: {str(e)}", status_code=503
            )

    def _process_response(self, data: Dict, country_code: str) -> List[AddressResult]:
        features = data.get("features", [])
        if not features:
            raise GeocodingError(
                detail="No features found in Azure Maps API response", status_code=404
            )
        return [self._parse_feature(feature) for feature in features]

    def _parse_feature(self, feature: Dict) -> AddressResult:
        print("FEATURE", feature)
        properties = feature.get("properties", {})
        address_info = properties.get("address", {})
        coordinates = feature.get("geometry", {}).get("coordinates", [0.0, 0.0])
        confidence = self._parse_confidence(properties.get("confidence"))

        return AddressResult(
            confidenceScore=confidence,
            address=AddressPayload(
                streetNumber=address_info.get("addressLine", ""),
                streetName=address_info.get("neighborhood", ""),
                municipality=address_info.get("locality", ""),
                municipalitySubdivision=address_info.get("adminDistricts", [{}])[0].get(
                    "shortName", ""
                ),
                postalCode=address_info.get("postalCode", ""),
                countryCode=address_info.get("countryRegion", {}).get("ISO", ""),
            ),
            freeformAddress=address_info.get("formattedAddress", ""),
            coordinates=Coordinates(lat=coordinates[1], lon=coordinates[0]),
            serviceUsed="azure_geocode",
        )

    def _parse_confidence(self, confidence: str) -> float:
        confidence_mapping = {"High": 1.0, "Medium": 0.75, "Low": 0.0}
        return confidence_mapping.get(confidence, 0.0)
