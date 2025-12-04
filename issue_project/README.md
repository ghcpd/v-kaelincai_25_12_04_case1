# Weather Forecast API Project

A simple weather forecast API service for demonstration and learning purposes.

## Problem Scenario

When querying weather for the city "Springfield", the API returns a 500 error. This occurs because the temperature field in the third-party weather data source is `null` (due to weather station failure), and the code doesn't properly handle null values.

## Project Structure

```
issue_project/
├── src/
│   ├── __init__.py
│   ├── weather_service.py    # Core business logic (contains bug)
│   └── api.py                 # Flask API endpoints
├── tests/
│   ├── __init__.py
│   ├── test_weather_service.py  # Unit tests
│   └── test_api.py             # Integration tests
├── data/
│   └── mock_weather_responses.json  # Mock data
├── requirements.txt
├── README.md
└── KNOWN_ISSUE.md
```

## Quick Start

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Run Tests (will see failing tests)

```powershell
pytest -v
```

### 3. Run API Server (Optional)

```powershell
python -m src.api
```

Then visit:
- Health check: http://localhost:5000/health
- Normal query: http://localhost:5000/api/weather?city=London
- Trigger bug: http://localhost:5000/api/weather?city=Springfield

## Test Description

The project includes multiple test cases:

- ✅ **Passing tests**: Queries for normal cities (e.g., New York, London)
- ❌ **Failing tests**: Springfield query should return 200 but actually returns 500
- ✅ **Bug demonstration tests**: Verify that Springfield indeed returns 500 error

Test commands:

```powershell
# Run all tests
pytest -v

# Run unit tests only
pytest tests/test_weather_service.py -v

# Run integration tests only
pytest tests/test_api.py -v

# Show detailed output
pytest -v -s
```

## Issue Details

See [KNOWN_ISSUE.md](KNOWN_ISSUE.md) for:
- Detailed problem description
- Trigger conditions
- Root cause analysis
- Fix suggestions

## Tech Stack

- Python 3.8+
- Flask 3.0.0
- pytest 7.4.3
- requests 2.31.0
