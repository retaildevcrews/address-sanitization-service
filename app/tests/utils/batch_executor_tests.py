import unittest
from app.utils.batch_executor import BatchExecutor

from app.parsers_and_expanders.libpostal import (
    expand_address as libpostal_expand_address,
)
from app.parsers_and_expanders.llm import (
    LLMEntityExtraction
)

import json


class TestLLMAddressUtils(unittest.TestCase):

    def setUp(self):
        addresses_json = """
        [
            {"address": "1 Microsoft Way, Redmond, WA 98052"},
            {"address": "2 Microsoft Way, Redmond, WA 98052"},
            {"address": "3 Microsoft Way, Redmond, WA 98052"}
        ]
        """
        self.addresses = json.loads(addresses_json)
        self.address_strings = [address["address"] for address in self.addresses]
        self.llm_extractor = LLMEntityExtraction()


    # def test_batch_expand_address(self):
    #     executor = BatchExecutor(
    #         func=libpostal_expand_address, num_threads=5, delay=0.5
    #     )
    #     results = executor.execute(self.address_strings)
    #     print("RESULTS:", results)

    def test_batch_expand_address_llm(self):
        executor = BatchExecutor(
            func=self.llm_extractor.expand_address, num_threads=5, delay=0.5
        )
        results = executor.execute(self.address_strings)
        print("RESULTS:", results)


if __name__ == "__main__":
    unittest.main()
