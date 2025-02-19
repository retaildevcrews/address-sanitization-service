import argparse
import json
import os
import pandas as pd
import pathlib
from address_evaluator import AddressEvaluator
from app.parsers_and_expanders.libpostal import parse_address
from azure.ai.evaluation import evaluate
from dotenv import load_dotenv

load_dotenv("credentials.env", override=True)


def address_parser_score(address: str) -> float:
    """
    Use libpostal to parse an address and return the number of components parsed.
    Score represents the percentage of 5 address components identified
    """
    try:
        parsed = parse_address(address)["parsed_address"]
        return min((len(parsed) / 5), 1)
    except Exception as e:
        print("Failed to parse address due to:", e)
        return 0.0


def run_evaluation(dataset_path, output_path):
    # Create the evaluators
    azure_maps_evaluator = AddressEvaluator(strategy="azure_search")
    azure_geocode_evaluator = AddressEvaluator(strategy="azure_geocode")
    osm_evaluator = AddressEvaluator(strategy="osm_nominatim")
    #mapbox_evaluator = AddressEvaluator(strategy="mapbox")


    evaluators = {
        azure_maps_evaluator.name: azure_maps_evaluator,
        azure_geocode_evaluator.name: azure_geocode_evaluator,
        osm_evaluator.name: osm_evaluator,
        #mapbox_evaluator.name: mapbox_evaluator,

    }
    # Run the evaluation
    result = evaluate(
        evaluation_name="azure_and_mapbox",
        evaluators=evaluators,
        data=dataset_path,
        output_path=output_path,
    )

    # print(result)
    summary = summarize_result(result, evaluators)

    # Write summary to JSON file
    output_dir = os.path.dirname(output_path)
    summary_file_path = os.path.join(output_dir, "results_summary.json")
    with open(summary_file_path, "w") as summary_file:
        json.dump(summary, summary_file, indent=4)

    # Print the summary
    for result in summary:
        print(
            f"Input Address: {result['input_address']}, parser_score: {result['parser_score']}, result: {result['best_match']['freeformAddress']}, confidence: {result['best_match']['confidenceScore']}, service: {result['best_match']['serviceUsed']}"
        )

    average_parser_score = sum([x["parser_score"] for x in summary]) / len(summary)
    average_confidence_score = sum(
        [x["best_match"]["confidenceScore"] for x in summary]
    ) / len(summary)
    print(f"Average parser score: {average_parser_score}")
    print(f"Average confidence score: {average_confidence_score}")


def summarize_result(result, evaluators):
    """
    Generate the evaluation result
    """
    rows = result["rows"]
    df = pd.DataFrame(rows)
    output = []
    for row in rows:
        result = {}
        matches = []
        result["input_address"] = row["inputs.address"]
        result["parser_score"] = address_parser_score(row["inputs.address"])
        result["country_code"] = row["inputs.country_code"]
        for evaluator in evaluators.keys():
            if f"outputs.{evaluator}.address" in row:
                matches.append(row[f"outputs.{evaluator}.address"])
                result[f"{evaluator}_confidenceScore"] = row[
                    f"outputs.{evaluator}.address"
                ]["confidenceScore"]
        matches.sort(key=lambda x: x["confidenceScore"], reverse=True)
        result["best_match"] = matches[0]
        output.append(result)

    return output


if __name__ == "__main__":
    # Read the dataset path from the command line
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset_path",
        help="full path to the dataset .jsonl file",
        default=str(pathlib.Path.cwd()) + "/eval/data/addresses.jsonl",
        type=str,
    )
    parser.add_argument(
        "--output_path",
        help="full path to the output .json file",
        default=str(pathlib.Path.cwd()) + "/eval/data/results.json",
    )
    args = parser.parse_args()

    run_evaluation(args.dataset_path, args.output_path)
