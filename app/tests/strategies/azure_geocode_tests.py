import unittest


from app.strategies.azure_geocode import AzureMapsStrategy



class TestAzureGeocode(unittest.TestCase):

    def test_process_address_azure_geocode(self):
        strategy = AzureMapsStrategy()
        # Call the function
        # result = strategy.geocode("1440 daniel carrion lima alcides", "PE")
        result = strategy.geocode("1 Microsoft Way, Redmond, WA 98052", "US")
        print("RESULT", result)
        assert result is not None


if __name__ == "__main__":
    unittest.main()
