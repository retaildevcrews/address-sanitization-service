import pandas as pd
import requests
import sys
import logging
from pprint import pformat
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Test geocoding strategies by sending addresses to an API."
    )
    parser.add_argument(
        "strategies",
        nargs="+",
        help="One or more geocoding strategies (e.g., azure, osm_nominatim, mapbox)."
    )
    parser.add_argument(
        "--csv-file",
        default="sample_data/peru.csv",
        help="Path to the input CSV file with addresses."
    )
    parser.add_argument(
        "--output-file",
        default="results.csv",
        help="Path to the output CSV file for results."
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8001/api/v1/address",
        help="API endpoint for geocoding."
    )
    return parser.parse_args()

def read_csv(csv_file):
    """
    Read the CSV file containing address data.
    """
    try:
        df = pd.read_csv(csv_file)
        logger.info("Successfully read CSV file: %s", csv_file)
        return df
    except Exception as e:
        logger.error("Failed to read CSV file '%s': %s", csv_file, e)
        sys.exit(1)

def process_address(session, address, country_code, strategy, api_url):
    """
    Send the address data to the API with the given strategy and return the best result.

    :param session: requests.Session() object for HTTP requests.
    :param address: The address string to geocode.
    :param country_code: The country code of the address.
    :param strategy: The geocoding strategy to use.
    :param api_url: The API endpoint URL.
    :return: A dictionary with the best geocoding result or None if no result.
    """
    payload = {
        "address": address,
        "country_code": country_code,
        "strategy": strategy
    }
    try:
        response = session.post(api_url, json=payload)
        response.raise_for_status()
        result = response.json()

        # Log the full response in debug mode for troubleshooting
        logger.debug("Response for strategy '%s' and address '%s': %s", strategy, address, pformat(result))

        if "error_code" in result:
            logger.error("Server returned an error for strategy '%s': %s", strategy, result)
            sys.exit(1)

        if result.get("addresses"):
            best_result = max(
                result["addresses"],
                key=lambda x: x.get("confidenceScore", 0)
            )
            return {
                "strategy": strategy,
                "input_address": address,
                "country_code": country_code,
                "confidence_score": best_result.get("confidenceScore"),
                "street_number": best_result.get("address", {}).get("streetNumber"),
                "street_name": best_result.get("address", {}).get("streetName"),
                "municipality": best_result.get("address", {}).get("municipality"),
                "postal_code": best_result.get("address", {}).get("postalCode"),
                "latitude": best_result.get("coordinates", {}).get("lat"),
                "longitude": best_result.get("coordinates", {}).get("lon")
            }
        else:
            logger.warning("No results found for strategy '%s' and address '%s'", strategy, address)
            return None

    except requests.exceptions.RequestException as e:
        logger.error("Request error for strategy '%s' and address '%s': %s", strategy, address, e)
        sys.exit(1)

def save_results(results, output_file):
    """
    Save the collected results into a CSV file.
    """
    if results:
        results_df = pd.DataFrame(results)
        try:
            results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            logger.info("Results saved to %s", output_file)
        except Exception as e:
            logger.error("Failed to write results CSV: %s", e)
            sys.exit(1)
    else:
        logger.warning("No results to save.")

def main():
    args = parse_args()

    df = read_csv(args.csv_file)
    results = []

    # Use a session for improved performance with multiple HTTP requests
    with requests.Session() as session:
        for index, row in df.iterrows():
            address = row.get("address")
            country_code = row.get("country_code")

            for strategy in args.strategies:
                logger.info("Processing strategy '%s' for address '%s'", strategy, address)
                result = process_address(session, address, country_code, strategy, args.api_url)
                if result:
                    results.append(result)

    save_results(results, args.output_file)

if __name__ == "__main__":
    main()
