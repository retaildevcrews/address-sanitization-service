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
            response = self._make_find_api_call(address, country_code)
            return self._process_response(response, country_code, address)
        except GeocodingError:
            raise
        except Exception as e:
            raise GeocodingError(
                detail=f"Unexpected Loqate Maps error: {str(e)}",
                status_code=500
            )

    def _make_find_api_call(self, address: str, country_code: str) -> Dict:
        """
            Handle Find API communication
            Returns addresses and places based on the search text/address.
            Documentation: https://www.loqate.com/developers/api/Capture/Interactive/Find/1.1/
        """

        container = ''
        query = "Find/v1.10/json3.ws?"
        params = {
            "Key": self.api_key,
            "Text": address,
            "Countries": country_code,
            "Limit": self.MAX_RESULTS,
            "IsMiddleware": "false",
            "Bias": "false",  # Setting Bias to false will help in returning items that do not match 100%.
            "Container": container
        }
        return self._make_api_call(query, params)


    def _make_retrieve_api_call(self, id: str) -> Dict:
        """
            Handle Retrieve API communication
            Returns the full address details based on the Id.
            Documentation: https://www.loqate.com/developers/api/Capture/Interactive/Retrieve/1.2/
        """

        query = "Retrieve/v1.00/json3.ws"
        params = {
            "Key": self.api_key,
            "Id": id,
            "Field1Format": "{Latitude}",
            "Field2Format": "{Longitude}"
        }
        return self._make_api_call(query, params)


    def _make_api_call(self, query: str, params : dict ) -> Dict:
        """Handle API communication"""
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

    def _process_response(self, data: Dict, country_code, address: str) -> List[AddressResult]:
        """Process and validate API response"""

        if not isinstance(data, dict) or "Items" not in data:
            raise GeocodingError(
                detail="Invalid Loqate Maps API response format",
                status_code=500
            )


        def count_highlighted_characters(highlight_ranges):
            """
                The count_highlighted_characters function takes a list of highlight ranges (tuples of start and end positions) and calculates
                the total number of highlighted characters by summing up the differences between the end and start positions for each range
            """

            count = 0
            for start, end in highlight_ranges:
                count += end - start
            return count

        def clean_highlight(highlight):
            """
                The clean_highlight function removes any trailing semicolon (;) from the highlight string
            """
            if highlight.endswith(';'):
                highlight = highlight[:-1]
            return highlight

        def parse_highlight(highlight):
            """
                The parse_highlight function splits the cleaned highlight string into two parts: text ranges and description ranges.
                Each part is further split into individual ranges, which are then converted into tuples of integers representing the start and end positions of the highlights.
            """

            parts = highlight.split(';')
            text_ranges = [(int(r.split('-')[0]), int(r.split('-')[1])) for r in parts[0].split(',')] if parts[0] else []
            description_ranges = [(int(r.split('-')[0]), int(r.split('-')[1])) for r in parts[1].split(',')] if len(parts) > 1 and parts[1] else []
            return text_ranges, description_ranges

        results = data.get("Items", []) # these are addresses and building type items without details

        if not results:
            raise GeocodingError(
                detail="No results found in Loqate Maps response",
                status_code=404
            )
        # build a list of addresses with highlighted count
        addresses = []
        for item in results:
            if item['Type'] == 'Address':
                highlight = clean_highlight(item['Highlight'])
                text_ranges, description_ranges = parse_highlight(highlight)

                """
                    The highlighted_count is the sum of the highlighted characters in both the text ranges and the description ranges.
                """
                highlighted_count = count_highlighted_characters(text_ranges) + count_highlighted_characters(description_ranges)
                addresses.append({
                    'Id': item['Id'],
                    'HighlightedCount': highlighted_count
                })

        # Sort addresses by the number of highlighted characters in descending order
        sorted_addresses = sorted(addresses, key=lambda x: x['HighlightedCount'], reverse=True)
        return self._parse_result(sorted_addresses, country_code, address)

    def _parse_result(self, result: Dict, country_code, address: str) -> AddressResult:
        """Convert Loqate-specific response to standard format"""

        def calculate_confidence_score(highlighted_count, address_length):
            """
                The confidenceScore can then be calculated as the ratio of highlighted_count to length of the address, ensuring it falls between 0 and 1.
            """
            return min(highlighted_count / address_length, 1.0)

        # Fetch more data and create AddressResult objects
        address_results = []
        for address_result in result:

            retrieve_data = self._make_retrieve_api_call(address_result["Id"])

            if retrieve_data['Items']:
                address_info = retrieve_data['Items'][0]

                try:
                    latitude = float(address_info["Field1"])
                    longitude = float(address_info["Field2"])
                except ValueError as e:
                    latitude = 0.0
                    longitude = 0.0

                highlighted_count = address_result.get("HighlightedCount",0)

                confidence_score = calculate_confidence_score(highlighted_count, len(address))

                address_results.append(
                    AddressResult(
                        confidenceScore=confidence_score,
                        address=AddressPayload(
                            streetNumber=address_info.get("BuildingNumber", ""),
                            streetName=address_info.get("Street", ""),
                            municipality=address_info.get("City", ""),
                            municipalitySubdivision=address_info.get("District", ""),
                            postalCode=address_info.get("PostalCode", ""),
                            countryCode= country_code
                        ),
                        freeformAddress=address_info.get("Label", ""),
                        coordinates=Coordinates(
                            lat=latitude,
                            lon=longitude
                        ),
                        serviceUsed="loqate"
                    )
                )

        return address_results
