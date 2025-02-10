import argparse
import pandas as pd
import pathlib
from address_evaluator import AddressEvaluator
from azure.ai.evaluation import evaluate
from dotenv import load_dotenv

load_dotenv('credentials.env', override=True)

def run_evaluation(dataset_path, output_path):
    # Create the evaluators
    azure_maps_evaluator = AddressEvaluator(strategy="azure_geocode")
    mapbox_evaluator = AddressEvaluator(strategy="mapbox")

    evaluators = {
            azure_maps_evaluator.name: azure_maps_evaluator,
            mapbox_evaluator.name: mapbox_evaluator,
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
    print(summary)

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
        result["input_address"] = row['inputs.address']
        result["country_code"] = row['inputs.country_code']
        for evaluator in evaluators.keys():
            matches.append(row[f"outputs.{evaluator}.address"])
            result[f"{evaluator}_confidenceScore"] = row[f"outputs.{evaluator}.address"]['confidenceScore']
        matches.sort(key=lambda x: x['confidenceScore'], reverse=True)
        result["best_match"] = matches[0]
        output.append(result)


    return output

if __name__ == "__main__":
    # Read the dataset path from the command line
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset_path",
        help="full path to the dataset .jsonl file",
        default=str(pathlib.Path.cwd()) + "/eval/data/peru.jsonl",
        type=str,
    )
    parser.add_argument(
        "--output_path",
        help="full path to the output .json file",
        default=str(pathlib.Path.cwd()) + "/eval/data/results.json",
    )
    args = parser.parse_args()

    run_evaluation(args.dataset_path, args.output_path)
