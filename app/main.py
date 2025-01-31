import os
import requests
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

# ========================
# Configuration
# ========================


AZURE_MAPS_KEY = os.getenv("AZURE_MAPS_KEY", "YOUR_AZURE_MAPS_KEY")
MAPBOX_MAPS_KEY = os.getenv("MAPBOX_MAPS_KEY", "YOUR_MAPBOX_MAPS_KEY")

SMARTY_STREET_MAPS_AUTH_ID = os.getenv("SMARTY_STREET_MAPS_AUTH_ID", "YOUR_SMARTY_STREET_MAPS_AUTH_ID")
SMARTY_STREET_MAPS_AUTH_TOKEN = os.getenv("SMARTY_STREET_MAPS_AUTH_TOKEN", "YOUR_SMARTY_STREET_MAPS_AUTH_TOKEN")

LOQATE_API_KEY = os.getenv("LOQATE_API_KEY", "YOUR_LOQATE_API_KEY")


# ========================
# Request Model
# ========================
class AddressRequest(BaseModel):
    address: str
    country_code: str
    strategy: str

# ========================
# New Response Models
# ========================

class Coordinates(BaseModel):
    lat: float
    lon: float

class AddressPayload(BaseModel):
    streetNumber: str
    streetName: str
    municipality: str
    municipalitySubdivision: str
    postalCode: str
    countryCode: str

class AddressResult(BaseModel):
    confidenceScore: float
    address: AddressPayload
    freeformAddress: str
    coordinates: Coordinates
    serviceUsed: str
    status: str

class Metadata(BaseModel):
    query: str
    country: str
    timestamp: datetime
    totalResults: int

class AddressResponse(BaseModel):
    metadata: Metadata
    addresses: List[AddressResult]

# ========================
# FastAPI Initialization
# ========================
app = FastAPI(
    title="Address Sanitization Service",
    description="A minimal FastAPI app that sanitizes addresses via Azure Maps.",
    version="0.1.0",
)

# ========================
# Health Check Endpoint
# ========================
@app.get("/", include_in_schema=False)
def health_check():
    return {"status": "healthy", "version": app.version}

# ========================
# Main Endpoint
# ========================
# @app.post("/api/v1/address", response_model=AddressResponse)
# def sanitize_address(payload: AddressRequest):
@app.post("/api/v1/address")
def sanitize_address():
    """
    Receive a JSON payload with the following fields:
    {
      "address": "1 Microsoft Way, Redmond, WA 98052",
      "country_code": "US",
      "strategy": "azure" or "mapbox"
    }

    Currently, we only support "azure" as a strategy.
    This endpoint returns a JSON response with metadata and a list of addresses.
    """
    # # Validate the strategy
    # if payload.strategy.lower() != "azure" and payload.strategy.lower() != "mapbox":
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Unsupported strategy: {payload.strategy}. Only 'azure' and 'mapbox' are supported.",
    #     )

    # call_smarty_street_maps_api()

    call_loqate_maps_api()


#     if payload.strategy.lower() == "azure":
#         address_objects = call_azure_maps_api(payload)
#     else:
#         address_objects = call_mapbox_maps_api(payload)
#    # Construct metadata
#     metadata = Metadata(
#         query=payload.address,
#         country=payload.country_code,
#         timestamp=datetime.utcnow(),
#         totalResults=len(address_objects)
#     )

#     # Return the final structured response
#     return AddressResponse(
#         metadata=metadata,
#         addresses=address_objects
#     )


def call_azure_maps_api(payload):
    azure_url = "https://atlas.microsoft.com/search/address/json"
    params = {
        "api-version": "1.0",
        "subscription-key": AZURE_MAPS_KEY,
        "query": payload.address,
        "countrySet": payload.country_code
    }

    try:
        response = requests.get(azure_url, params=params, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

    data = response.json()
    results = data.get("results", [])

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No matching address found from Azure Maps."
        )

    # Sort results by descending score (so highest confidence is first)
    sorted_results = sorted(results, key=lambda r: r.get("score", 0.0), reverse=True)

    # Build the list of AddressResult objects
    address_objects = []
    for result in sorted_results:
        address_info = result.get("address", {})
        address_objects.append(
            AddressResult(
                confidenceScore=result.get("score", 0.0),
                address=AddressPayload(
                    streetNumber=address_info.get("streetNumber", ""),
                    streetName=address_info.get("streetName", ""),
                    municipality=address_info.get("municipality", ""),
                    municipalitySubdivision=address_info.get("municipalitySubdivision", ""),
                    postalCode=address_info.get("postalCode", ""),
                    countryCode=address_info.get("countryCodeISO3", payload.country_code)
                ),
                freeformAddress=address_info.get("freeformAddress", payload.address),
                coordinates=Coordinates(
                    lat=result["position"]["lat"],
                    lon=result["position"]["lon"]
                ),
                serviceUsed="azure",
                status="SUCCESS",
            )
        )
    return address_objects


def call_mapbox_maps_api(payload):
    # Set your Mapbox access token
    access_token = MAPBOX_MAPS_KEY

    # Define the endpoint and parameters
    endpoint = 'https://api.mapbox.com/geocoding/v5/mapbox.places/'
    query = payload.address + '.json'
    params = {
        'access_token': access_token,
        'country': payload.country_code,
    }

    # Make the request
    try:
        response = requests.get(endpoint + query, params=params, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

    data = response.json()
    features = data.get("features", [])

    if not features:
        raise HTTPException(
            status_code=404,
            detail="No matching address found from Mapbox."
        )

    # Sort features by descending score (so highest confidence is first)
    sorted_features = sorted(features, key=lambda r: r.get("relevance", 0.0), reverse=True)


    # Function to extract postal code and country from context
    def extract_postal_code_and_country(context):
        postal_code = ""
        country = ""
        municipality = ""
        for item in context:
            if item['id'].startswith('postcode.'):
                postal_code = item['text']
            elif item['id'].startswith('country.'):
                country = item['text']
            elif item['id'].startswith('place.'):
                municipality = item['text']

        return postal_code, country, municipality

    # Build the list of AddressResult objects
    address_objects = []
    for feature in sorted_features:
        postalCode, country , municipality= extract_postal_code_and_country(feature['context'])
        address_obj = AddressPayload(
                    streetNumber=feature.get("address", ""),
                    streetName=feature.get("text", ""),
                    postalCode=postalCode,
                    municipality=municipality,
                    countryCode= country,
                    municipalitySubdivision=feature.get("municipalitySubdivision", "")
                )
        address_result = AddressResult(confidenceScore=feature.get("relevance", 0.0),
                                        address=address_obj,
                                        freeformAddress= feature.get("place_name", payload.address),
                                        coordinates=Coordinates(
                                            lat=feature['center'][1],
                                            lon=feature['center'][0]
                                        ),
                                        serviceUsed="mapbox",
                                        status="SUCCESS",
                                      )


        address_objects.append(address_result)

    return address_objects


def call_smarty_street_maps_api():
    # Replace with your actual SmartyStreets API keys
    auth_id = SMARTY_STREET_MAPS_AUTH_ID
    auth_token = SMARTY_STREET_MAPS_AUTH_TOKEN

    # credentials = StaticCredentials(auth_id, auth_token)
    # client = ClientBuilder(credentials).build_us_street_api_client()

    # # Create a lookup object with the address you want to verify
    # lookup = Lookup()
    # lookup.street = "1600 Amphitheatre Parkway"
    # lookup.city = "Mountain View"
    # lookup.state = "CA"

    # # Send the lookup request
    # client.send_lookup(lookup)

    # # Print the results
    # result = lookup.result

    # print("lookup: ", lookup)
    # print("Result: ", result)

    # if result:
    #     print("Address is valid!")
    #     for candidate in result:
    #         print(candidate.delivery_line_1)
    #         print(candidate.last_line)
    #         print(candidate.metadata.latitude, candidate.metadata.longitude)
    # else:
    #     print("Address is invalid.")


    # Define the endpoint and parameters
    url = "https://us-street.api.smartystreets.com/street-address"
    params = {
        "auth-id": auth_id,
        "auth-token": auth_token,
        "street": "1 Microsoft Way, Redmond, WA 98052",
        "country": "US",
        "match": "invalid",
        "candidates": 5
    }


    # params = {
    #     "auth-id": auth_id,
    #     "auth-token": auth_token,
    #     "street": "1 Microsoft Way, Redmond, WA 98052",
    #     "city": "Redmond",
    #     "state": "CA"
    # }


    # Make the GET request
    response = requests.get(url, params=params)

    # Print the response
    if response.status_code == 200:
        print("Address is valid!")
        print(response.json())
    else:
        print("Error:", response.status_code, response.text)


    # Understanding DPV Match Codes
    # Y: The address is valid and deliverable.
    # S: The address is valid but the secondary information (e.g., apartment number) is missing.
    # D: The address is valid but the secondary information is not recognized.
    # N: The address is not valid or deliverable.
    # By evaluating the DPV match codes, you can determine which address candidate is the most likely and accurate.


def call_loqate_maps_api():

    # https://www.loqate.com/developers/api/Capture/Interactive/Find/1.1/

    # Replace 'your_api_key' with your actual Loqate API key
    api_key = LOQATE_API_KEY
    address = '1 Microsoft Way, Redmond, WA 98052' #'10 Downing Street, London'
    limit = '10'
    country = 'US'

    def find_addresses(text, container=''):
        url = f'https://api.addressy.com/Capture/Interactive/Find/v1.10/json3.ws?Key={api_key}&Text={text}&Countries={country}&Limit={limit}&IsMiddleware=false&Container={container}'
        response = requests.get(url)
        return response.json()

    def retrieve_address(id):
        url = f'https://api.addressy.com/Capture/Interactive/Retrieve/v1.00/json3.ws?Key={api_key}&Id={id}'
        response = requests.get(url)
        return response.json()

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

    # Initial find request
    find_data = find_addresses(address)

    addresses = []

    if find_data['Items']:
        for item in find_data['Items']:
            if item['Type'] == 'Building':
                highlight = clean_highlight(item['Highlight'])
                text_ranges, description_ranges = parse_highlight(highlight)
                highlighted_count = count_highlighted_characters(text_ranges) + count_highlighted_characters(description_ranges)
                addresses.append({
                    'Text': item['Text'],
                    'Description': item['Description'],
                    'Highlight': highlight,
                    'Highlighted Count': highlighted_count
                })

    # Sort addresses by the number of highlighted characters in descending order
    sorted_addresses = sorted(addresses, key=lambda x: x['Highlighted Count'], reverse=True)

    # Print sorted addresses
    for address in sorted_addresses:
        print(f"Address: {address['Text']}, Description: {address['Description']}, Highlighted Count: {address['Highlighted Count']}")

    if sorted_addresses:
        print(f"\nBest Match: {sorted_addresses[0]['Text']}, Description: {sorted_addresses[0]['Description']}, Highlighted Count: {sorted_addresses[0]['Highlighted Count']}")
    else:
        print("No building addresses found.")
