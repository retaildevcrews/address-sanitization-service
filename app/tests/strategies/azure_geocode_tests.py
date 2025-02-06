import unittest
from unittest.mock import MagicMock, patch

from app.strategies.azure_geocode import AzureMapsStrategy


class TestAzureGeocode(unittest.TestCase):

    def test_process_address_azure_geocode(self):
        strategy = AzureMapsStrategy()
        # Call the function
        result = strategy.geocode("1440 daniel carrion lima alcides", "PE")
        print("RESULT", result)
        assert result is not None


if __name__ == "__main__":
    unittest.main()
