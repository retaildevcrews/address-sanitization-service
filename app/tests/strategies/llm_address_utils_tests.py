import unittest

from app.utils.llm.llm_address_utils import LLMEntityExtraction

class TestLLMAddressUtils(unittest.TestCase):

    address= "1 Microsoft Way, Redmond, WA 98052"

    def test_llm_entity_extraction(self):
        llm_extractor= LLMEntityExtraction()
        result = llm_extractor.get_address_expansion(self.address)
        print("RESULT", result)
        assert result is not None

    def test_llm_address_entities(self):
        llm_extractor= LLMEntityExtraction()
        result = llm_extractor.get_address_entities(self.address)
        print("RESULT", result)
        assert result is not None

if __name__ == "__main__":
    unittest.main()
