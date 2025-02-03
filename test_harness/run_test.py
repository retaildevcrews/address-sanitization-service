import pandas as pd
import requests
import sys
import logging
from pprint import pformat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

if len(sys.argv) < 2:
    logger.error(
        "Invalid usage! Please specify at least one geocoding strategy.\n"
        "Example usage:\n"
        "  python run_test.py azure mapbox loqate\n"
        "Available strategies: azure, osm_nominatim, mapbox, loqate"
    )
    sys.exit(1)

# Read geocoding strategies from command-line arguments
STRATEGIES = sys.argv[1:]

CSV_FILE = "sample_data/peru.csv"
OUTPUT_FILE = "results.csv"
API_URL = "http://localhost:8000/api/v1/address"

# Read the CSV file
df = pd.read_csv(CSV_FILE)

results = []

# Iterate through each address and strategy
for index, row in df.iterrows():
    address = row["address"]
    country_code = row["country_code"]

    for strategy in STRATEGIES:
        payload = {
            "address": address,
            "country_code": country_code,
            "strategy": strategy
        }

        try:
            response = requests.post(API_URL, json=payload)
            # If the server responds with a 4xx/5xx status code, this will raise an HTTPError
            response.raise_for_status()
            result = response.json()

            # Check for custom error_code in the JSON
            if "error_code" in result:
                logger.error("Server returned an error code: %s", result["error_code"])
                logger.error("Error details: %s", result.get('error_message', 'No details provided.'))
                logger.error("Stopping execution.")
                sys.exit(1)

            logger.info("Strategy: %s | Address: %s", strategy, address)
            logger.info("Response:\n%s", pformat(result))

            # Find the result with the highest confidence score
            if result["addresses"]:
                best_result = max(
                    result["addresses"],
                    key=lambda x: x["confidenceScore"]
                )

                # Extract relevant data for the output CSV
                results.append({
                    "strategy": strategy,
                    "input_address": address,
                    "country_code": country_code,
                    "confidence_score": best_result["confidenceScore"],
                    "street_number": best_result["address"]["streetNumber"],
                    "street_name": best_result["address"]["streetName"],
                    "municipality": best_result["address"]["municipality"],
                    "postal_code": best_result["address"]["postalCode"],
                    "latitude": best_result["coordinates"]["lat"],
                    "longitude": best_result["coordinates"]["lon"]
                })
            else:
                logger.warning(
                    "No results found for strategy '%s' and address '%s'",
                    strategy,
                    address
                )

        except requests.exceptions.RequestException as e:
            logger.error("Request error with strategy '%s' for address '%s': %s", strategy, address, e)
            logger.error("Stopping execution.")
            sys.exit(1)

# Save results to CSV
results_df = pd.DataFrame(results)
results_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

logger.info("Results saved to %s", OUTPUT_FILE)
