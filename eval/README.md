# Address Sanitization Evaluations

This folder contains custom evaluators for use with the address sanitization service

---

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Running Evaluations](#running-evaluations)

---

## Overview

- **Language**: Python (azure.ai.evaluation)
- **Dependencies**: Managed with Poetry in the project root `pyproject.toml`

---

## Getting Started

Follow the steps in the project root README to configure credentials for the Azure Map and Mapbox services

### Running evaluations

Evalations can be run on a .jsonl dataset using the --dataset_path parameter. The default value is /eval/data/peru.jsonl

```bash

# run the application directly using Poetry from the project root
poetry install  # Installs dependencies
poetry run python ./eval/evaluate_address_data.py

```

Results are output in JSON format to a file speciifed by the --output_path parameter. The default value is /eval/data/results.json

The results should look like the following:

```json

 {
            "inputs.address": "11 urb jose i de martin lote porres san av mz",
            "inputs.country_code": "PE",
            "outputs.azure.address": {
                "streetNumber": "",
                "streetName": "Avenida Jos\u00e9 de San Mart\u00edn",
                "municipality": "Carabayllo",
                "municipalitySubdivision": "",
                "postalCode": "15318",
                "countryCode": "PER"
            },
            "outputs.azure.match_count": 10,
            "outputs.azure.min_score": 0.280848288,
            "outputs.azure.max_score": 0.3710061155,
            "outputs.azure.avg_score": 0.3182205467,
            "outputs.azure.score": 0.3710061155,
            "outputs.azure.results": [
                {
                    "confidenceScore": 0.3710061155,
                    "address": {
                        "streetNumber": "",
                        "streetName": "Avenida Jos\u00e9 de San Mart\u00edn",
                        "municipality": "Carabayllo",
                        "municipalitySubdivision": "",
                        "postalCode": "15318",
                        "countryCode": "PER"
                    },
                    "freeformAddress": "Avenida Jos\u00e9 de San Mart\u00edn Carabayllo, 15318",
                    "coordinates": {
                        "lat": -11.8986149,
                        "lon": -77.0316493
                    },
                    "serviceUsed": "azure"
                },

```
