# SQLPilot

SQLPilot is an LLM Agent based SQL optimization and verification platform. It uses Large Language Models to diagnose slow queries, generate optimization proposals, and strictly validates them by executing against a shadow database.

## Features

- **Automated Diagnosis**: Analyzes execution plans to find bottlenecks.
- **SQL Optimization**: Suggests rewrites or index changes.
- **Strict Verification**:
    - **Semantic Check**: Ensures optimized SQL returns identical results.
    - **Performance Check**: Measures actual execution time improvements.
- **CLI & API**: Flexible usage patterns.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy the example config and edit it with your database and LLM credentials:

```bash
cp config/config.example.yaml config/config.yaml
```

## Usage

### CLI

```bash
# Optimize a query
python -m sqlpilot.cli.main optimize --sql "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)"

# Check health
python -m sqlpilot.cli.main health
```

### API

Start the server:

```bash
uvicorn sqlpilot.api.app:app --reload
```

Optimize via API:

```bash
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT ...", "database": "mysql"}'
```

## Docker

```bash
docker-compose up --build
```
