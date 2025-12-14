import pytest
from fastapi.testclient import TestClient
from sqlpilot.api.app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data

def test_optimize_endpoint_validation():
    # Test missing SQL
    response = client.post("/api/v1/optimize", json={"database": "mysql"})
    assert response.status_code == 422 # Validation error

    # Test invalid database
    response = client.post("/api/v1/optimize", json={"sql": "SELECT 1", "database": "invalid"})
    assert response.status_code == 400
