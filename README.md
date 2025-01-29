# Address Sanitization Service

This repository contains a **FastAPI** application that sanitizes addresses using the [Azure Maps Search API](https://learn.microsoft.com/en-us/rest/api/maps/search/get-search-address?view=rest-maps-1.0&tabs=HTTP). The service accepts an address query, country code, and strategy (currently only `azure` is supported), then returns structured address data with confidence scores and metadata.

---

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
  - [Docker Compose (Local)](#docker-compose-local)
  - [DevContainer / Codespaces](#devcontainer--codespaces)
  - [Environment Variables](#environment-variables)
  - [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)

---

## Overview

- **Language**: Python (FastAPI)
- **Dependencies**: Managed via `requirements.txt`
- **Containerization**: Multi-mode support:
  - 🐳 Docker Compose (local development)
  - 🐳📦 Docker-in-Docker (DinD) in DevContainer/Codespaces
  - ☁️ GitHub Codespaces (browser-based)

---

## Getting Started

### Docker Compose

1. Create `.env` file in project root:

```bash
echo "AZURE_MAPS_KEY=your_actual_key_here" > .env
```

if the `.env` file already exists to add a new variable to it, you can use the echo command with the `>>` operator

```bash
echo "MAPBOX_MAPS_KEY=your_actual_key_here" >> .env
```

### Running the Application

```bash

# Option 1: Docker Compose

docker compose up --build

# Option 2: Direct execution

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Access endpoints at:

- Local/DevContainer: <http://localhost:8000>
- Codespaces: `https://<your-codespace>-8000.app.github.dev`

---

## API Endpoints

### Sanitize Address

**Endpoint**: `POST /api/v1/address`

#### Sample Request

```bash
http POST localhost:8000/api/v1/address \
  address="1 Microsoft Way, Redmond, WA 98052" \
  country_code="US" \
  strategy="azure"
```

#### Sample Response

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
      "serviceUsed": "azure",
      "status": "SUCCESS"
    }
  ],
  "metadata": {
    "query": "1 Microsoft Way, Redmond, WA 98052",
    "timestamp": "2025-01-29T00:37:23.869661"
  }
}
```
