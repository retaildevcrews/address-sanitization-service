# app/strategies/result_helper.py

from .schemas import AddressResult, AddressPayload, Coordinates

def create_empty_address_result(country_code, strategy):
    return [
        AddressResult(
            confidenceScore=0.0,
            address=AddressPayload(
                streetNumber="",
                streetName="",
                municipality="",
                municipalitySubdivision="",
                postalCode="",
                countryCode=country_code.upper()
            ),
            freeformAddress="",
            coordinates=Coordinates(lat=0.0, lon=0.0),
            serviceUsed=strategy
        )
    ]
