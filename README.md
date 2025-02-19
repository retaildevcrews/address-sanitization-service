# Address Sanitization Service

This repository contains a FastAPI application that sanitizes addresses using several providers, including Azure Maps API, MapBox, Loqate and Nominatim (OpenStreetMap). The service accepts an address query, country code, and strategy (currently supporting azure_search, azure_geocode, mapbox, loqate and nominatim), then returns structured address data with confidence scores and metadata.

---

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
  - [Docker Compose](#docker-compose)
  - [Running the Application](#running-the-application)
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

## Running the Test Harness

The test harness allows you to evaluate different geocoding strategies by sending address queries to the FastAPI service and saving the results.

### Prerequisites

1. **Ensure the API is running**
   The test harness sends requests to `http://localhost:8000/api/v1/address/sanitize`. Make sure the FastAPI service is up and running.

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
