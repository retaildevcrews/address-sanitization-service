import asyncio
from app.main import sanitize_address
from app.schemas import AddressRequest, AddressResponse


class AddressEvaluator:
    """
    This evaluator is used to evaluate address completeness and correctness.
    The floor of the score is 0.
    """

    def __init__(self, strategy="azure"):
        self.name = strategy
        self.strategy = strategy

    def __call__(self, address, country_code):
        """
        Performs the evaluation
        params:
        address: an address to be evaluated
        country_code: the country code of the address
        """
        result = {}
        request = AddressRequest(
            address=address, country_code=country_code, strategy=self.strategy
        )
        response = asyncio.run(sanitize_address(request))
        # sort response.addresses by confidenceScore
        response.addresses.sort(key=lambda x: x.confidenceScore, reverse=True)
        # Output results
        result["address"] = response.addresses[0].model_dump() if response else address
        result["results"] = [x.model_dump() for x in response.addresses] if response else []

        return result
