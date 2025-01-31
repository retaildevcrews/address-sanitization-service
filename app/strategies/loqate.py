# app/strategies/loqate.py
import os
import requests
from typing import List, Dict
from ..schemas import AddressResult, AddressPayload, Coordinates
from ..exceptions import GeocodingError
from . import GeocodingStrategy, StrategyFactory

@StrategyFactory.register("loqate")
class LoqateMapsStrategy(GeocodingStrategy):
    # Configuration constants
    API_BASE_URL = "https://api.addressy.com/Capture/Interactive/"
    TIMEOUT = 5  # seconds
    MAX_RESULTS = 10
    REQUIRED_ENV_VARS = ["LOQATE_API_KEY"]

    def __init__(self):
        self._validate_environment()
        self.api_key = os.getenv("LOQATE_API_KEY")

    def _validate_environment(self):
        """Ensure required environment variables are present"""
        missing = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing:
            raise ValueError(
                f"Missing Loqate Maps environment variables: {', '.join(missing)}"
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
                detail=f"Unexpected Loqate Maps error: {str(e)}",
                status_code=500
            )

    def _make_api_call(self, address: str, country_code: str) -> Dict:
        """Handle API communication"""
        container = ''
        query = "Interactive/Find/v1.10/json3.ws?"
        params = {
            "Key": self.api_key,
            "Text": address,
            "Countries": country_code,
            "Limit": self.MAX_RESULTS,
            "IsMiddleware": False,
            "Container": container
        }
        try:

            response = requests.get(self.API_BASE_URL + query,
                                    params=params,
                                    timeout=self.TIMEOUT)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise GeocodingError(
                detail="Loqate Maps API request timed out",
                status_code=504
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            detail = f"Loqate Maps API error: {e.response.text}"
            raise GeocodingError(detail=detail, status_code=status_code)
        except requests.exceptions.RequestException as e:
            raise GeocodingError(
                detail=f"Loqate Maps connection error: {str(e)}",
                status_code=503
            )

    def _process_response(self, data: Dict, country_code: str) -> List[AddressResult]:
        """Process and validate API response"""

        if not isinstance(data, dict) or "features" not in data:
            raise GeocodingError(
                detail="Invalid Loqate Maps API response format",
                status_code=500
            )


        def count_highlighted_characters(highlight_ranges):
            count = 0
            for start, end in highlight_ranges:
                count += end - start
            return count

        def clean_highlight(highlight):
            if highlight.endswith(';'):
                highlight = highlight[:-1]
            return highlight

        def parse_highlight(highlight):
            parts = highlight.split(';')
            text_ranges = [(int(r.split('-')[0]), int(r.split('-')[1])) for r in parts[0].split(',')] if parts[0] else []
            description_ranges = [(int(r.split('-')[0]), int(r.split('-')[1])) for r in parts[1].split(',')] if len(parts) > 1 and parts[1] else []
            return text_ranges, description_ranges

        results = data.get("Items", []) # this are just addresses without details

        if not results:
            raise GeocodingError(
                detail="No results found in Loqate Maps response",
                status_code=404
            )

        # build a list of addresses with highlighted count
        addresses = []
        for item in results['Items']:
            if item['Type'] == 'Address':
                highlight = clean_highlight(item['Highlight'])
                text_ranges, description_ranges = parse_highlight(highlight)
                highlighted_count = count_highlighted_characters(text_ranges) + count_highlighted_characters(description_ranges)
                addresses.append({
                    'Id': item['Id'],
                    'Highlight': highlight,
                    'Highlighted Count': highlighted_count
                })


        return [
            # self._parse_result(r, country_code)
            # for r in sorted(
            #     results,
            #     key=lambda x: x.get("relevance", 0.0),
            #     reverse=True
            # )

            # Sort addresses by the number of highlighted characters in descending order
            sorted_addresses = sorted(addresses, key=lambda x: x['Highlighted Count'], reverse=True)

            self._parse_result(sorted_addresses, country_code)
        ]

    def _parse_result(self, result: Dict, country_code: str) -> AddressResult:
        """Convert Loqate-specific response to standard format"""

        # TODO: Add try except block to handle API call and missing keys
        def retrieve_address(id):
            url = "https://api.addressy.com/Capture/Interactive/Retrieve/v1.00/json3.ws?Key={api_key}&Id={id}&Field1Format={{Latitude}}&Field2Format={{Longitude}}".format(api_key=self.api_key, id=id)
            response = requests.get(url)
            return response.json()

        # sorted_addresses = result
        # Fetch more data and create AddressResult objects
        address_result = []
        for result in result:

            #TODO Refactor _make_api_call to take query and params as arguments and use it here

            retrieve_data = retrieve_address(result["Id"])  # MAKES Another API call to get more data

            if retrieve_data['Items']:
                address_info = retrieve_data['Items'][0]

                print(f"Id: {address_info.get('Id')}")
                print(f"address_info: {address_info}")

                try:
                    latitude = float(address_info["Field1"])
                    longitude = float(address_info["Field2"])
                except ValueError as e:
                    latitude = 0.0
                    longitude = 0.0


                address_result.append(
                    AddressResult(
                        confidenceScore=result.get("Highlighted Count", 0.0),
                        address=AddressPayload(
                            streetNumber=address_info.get("BuildingNumber", ""),
                            streetName=address_info.get("Street", ""),
                            municipality=address_info.get("City", ""),
                            municipalitySubdivision=address_info.get("District", ""),
                            postalCode=address_info.get("PostalCode", ""),
                            countryCode= country_code #address_info.get("CountryISO3", "")
                        ),
                        freeformAddress=address_info.get("Label", ""),
                        coordinates=Coordinates(
                            lat=latitude,
                            lon=longitude
                        ),
                        serviceUsed="Loqate"
                    )
                )

        return address_result
