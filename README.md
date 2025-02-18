# Address Sanitization Service

This repository contains a FastAPI application that sanitizes addresses using several providers, including Azure Maps API, MapBox, Loqate and Nominatim (OpenStreetMap). The service accepts an address query, country code, and strategy (currently supporting azure_search, azure_geocode, mapbox, loqate and nominatim), then returns structured address data with confidence scores and metadata.

---

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
  - [Docker Compose](#docker-compose)
  - [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Running the Test Harness](#running-the-test-harness)

---

## Overview

- **Language**: Python (FastAPI)
- **Dependencies**: Managed with Poetry `pyproject.toml`
- **Containerization**: Multi-mode support:
  - 🐳 Docker Compose (local development)
  - 🐳📦 Docker-in-Docker (DinD) in DevContainer/Codespaces
  - ☁️ GitHub Codespaces (browser-based)

---

## Getting Started

### Docker Compose

1. Create a `credentials.env` file in the project root, listing the services you plan to use:

```bash
cat > credentials.env <<EOF
AZURE_MAPS_KEY=your_actual_key_here
MAPBOX_MAPS_KEY=your_actual_key_here
LOQATE_API_KEY=your_actual_key_here
EOF
```

If the credentials.env file already exists, you can add a new variable to it using the echo command with the >> operator.

```bash
echo 'MAPBOX_MAPS_KEY=your_actual_key_here' >> credentials.env
echo 'LOQATE_API_KEY=your_actual_key_here' >> credentials.env
echo "New variable added. If the service is already running, restart it to apply changes."

```

### Running the Application

```bash
# Start the application using Docker Compose (Recommended)
docker compose up --build

# OR run the application directly using Poetry
poetry install  # Installs dependencies
eval "source $(poetry env info --path)/bin/activate" # Activate the virtual environment created by poetry
export $(grep -v '^#' /workspaces/address-sanitization-service/credentials.env| xargs) # Set environment variables from credentials.env file
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Access endpoints at:

- Local/DevContainer: <http://localhost:8000>
- Codespaces: `https://<your-codespace>-8000.app.github.dev`

---

## API Endpoints

### 1. Sanitize Address

**Endpoint**: `POST /api/v1/address`

#### 1. Sample Request using HTTPie (Available strategies: azure_search, azure_geocode, osm_nominatim, mapbox, loqate)

```bash
http POST localhost:8000/api/v1/address \
  address="1 Microsoft Way, Redmond, WA 98052" \
  country_code="US" \
  strategy="azure_search" \
  use_libpostal=true

```

#### 1. Sample Response

```json

{
  "addresses": [
    {
      "address": {
        "countryCode": "US",
        "municipality": "Redmond",
        "postalCode": "98052",
        "streetName": "Northeast One Microsoft Way",
        "streetNumber": "1"
      },
      "confidenceScore": 0.9965,
      "coordinates": {
        "lat": 47.641673,
        "lon": -122.125648
      },
      "serviceUsed": "azure_search"
    }
  ],
  "metadata": {
    "query": "1 Microsoft Way, Redmond, WA 98052",
    "timestamp": "2025-01-29T00:37:23.869661"
  }
}
```

### 2. Parse Address

**Endpoint**: `GET /api/v1/parse_address_libpostal`

#### 2. Sample Request using HTTPie

```bash
http GET localhost:8000/api/v1/parse_address_libpostal address=="1 Microsoft Way, Redmond,WA 98052"

```

#### 2. Sample Response

```json
{
    "address": "1 Microsoft Way, Redmond,WA 98052",
    "parsed": {
        "city": "redmond",
        "house_number": "1",
        "postcode": "98052",
        "road": "microsoft way",
        "state": "wa"
    }
}
```

### 3. Expand Address LibPostal

**Endpoint**: `GET /api/v1/expand_address_libpostal`

#### 3. Sample Request using HTTPie (Available strategies: azure_search, azure_geocode, osm_nominatim, mapbox, loqate)

```bash
http GET localhost:8000/api/v1/expand_address_libpostal address=="1 Microsoft Way, Redmond,WA 98052"

```

#### 3. Sample Response

```json
{
  "address": "1 Microsoft Way, Redmond,WA 98052",
  "expanded_address": "1 microsoft way redmondwashington 98052"
}
```

### 4. Parse Address

**Endpoint**: `GET /api/v1/parse_address_llm`

#### 4. Sample Request using HTTPie

```bash
http GET localhost:8000/api/v1/parse_address_llm address=="1 Microsoft Way, Redmond,WA 98052"

```

#### 4. Sample Response

```json
{
  "streetName": "Microsoft Way",
  "streetNumber": "1",
  "block": null,
  "lot": null,
  "neighbourhood": null,
  "municipality": "Redmond",
  "municipalitySubdivision": null,
  "country": "United States",
  "countryCode": "US",
  "countrySubdivision": "Washington",
  "countrySecondarySubdivision": null,
  "postalCode": 98052
}
```

### 5. Expand Address llm

**Endpoint**: `GET /api/v1/expand_address_llm`

#### 5. Sample Request using HTTPie (Available strategies: azure_search, azure_geocode, osm_nominatim, mapbox, loqate)

```bash
http GET localhost:8000/api/v1/expand_address_llm address=="1 Microsoft Way, Redmond,WA 98052"

```

#### 5. Sample Response

```json
{
  "original_address": "1 Microsoft Way, Redmond,WA 98052",
  "expanded_address": "1 Microsoft Way, Redmond, Washington 98052"
}
```

## Running the Test Harness

The test harness allows you to evaluate different geocoding strategies by sending address queries to the FastAPI service and saving the results.

### Prerequisites

1. **Ensure the API is running**
   The test harness sends requests to `http://localhost:8000/api/v1/address`. Make sure the FastAPI service is up and running.

2. **Prepare the Input Data**
   The `test_harness/peru.csv` file contains sample addresses from Peru. Ensure this file is in place or modify it with your own test data.

### Running the Script

Navigate to the `test_harness` folder and specify the geocoding strategies you want to test:

```bash
cd test_harness
python run_test.py azure_search azure_geocode mapbox loqate
```

You can specify one or more strategies. Available options:

- `azure_search` (Azure Maps Address API)
- `azure_geocode` (Azure Maps Geocode API)
- `osm_nominatim` (Nominatim / OpenStreetMap)
- `mapbox` (MapBox API)
- `loqate` (Loqate API)

If no strategy is provided, the script will exit with an error.

### What Happens?

- The script reads addresses from `peru.csv`.
- It tests each address using the specified geocoding strategies.
- The results are saved to `results.csv` in the same folder.
- If an error occurs (e.g., API failure), execution stops, and an error message is logged.

### Output

After execution, check the `results.csv` file for structured results including:

- **Geocoding strategy used**
- **Input address & country code**
- **Best-matching address with confidence score**
- **Latitude & longitude**

### Troubleshooting

- **Error: "Invalid usage! Please specify at least one geocoding strategy."**
  → Ensure you provide at least one strategy when running the script. Example:

  ```bash
  python run_test.py azure_search mapbox loqate
  ```

- **Error: "Request error with strategy 'X' for address 'Y'"**
  → Ensure the API server is running and accessible at `http://localhost:8000`.

- **No results found for an address**
  → The API might not have a match for that query. Try different input addresses.
