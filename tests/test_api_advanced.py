import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from sqlpilot.api.app import app

client = TestClient(app)

@pytest.fixture
def mock_dependencies():
    with patch("sqlpilot.api.routes.optimize.MySQLAdapter") as MockDB, \
         patch("sqlpilot.api.routes.optimize.AgentTools") as MockTools, \
         patch("sqlpilot.api.routes.optimize.LLMService") as MockLLM, \
         patch("sqlpilot.api.routes.optimize.SQLAgent") as MockAgent:
        
        # Setup Mock DB instance
        db_instance = MockDB.return_value
        db_instance.connect = AsyncMock()
        db_instance.close = AsyncMock()
        
        # Setup Mock Agent instance
        agent_instance = MockAgent.return_value
        agent_instance.optimize = AsyncMock()
        
        yield {
            "db": db_instance,
            "agent": agent_instance,
            "MockDB": MockDB
        }

def test_optimize_unsupported_db():
    response = client.post("/api/v1/optimize", json={"sql": "SELECT 1", "database": "postgres"})
    assert response.status_code == 400
    assert "Only mysql" in response.json()["detail"]

def test_optimize_success(mock_dependencies):
    # Setup successful agent response
    mock_dependencies["agent"].optimize.return_value = {
        "original_sql": "SELECT * FROM users",
        "optimized_sql": "SELECT id, name FROM users",
        "diagnosis": {"root_cause": "Select *", "bottlenecks": ["Network"]},
        "validation": {
            "semantic_check": {"status": "passed"},
            "performance_check": {
                "status": "passed",
                "original_time_ms": 100,
                "optimized_time_ms": 50,
                "improvement_ratio": 0.5
            },
            "boundary_tests": {"status": "skipped"}
        },
        "confidence": "HIGH",
        "recommendation": "auto_apply",
        "explanation": "Removed select *"
    }

    response = client.post("/api/v1/optimize", json={"sql": "SELECT * FROM users", "database": "mysql"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["optimized_sql"] == "SELECT id, name FROM users"

def test_optimize_db_connection_error(mock_dependencies):
    # Setup DB connection error
    mock_dependencies["db"].connect.side_effect = Exception("Connection refused")
    
    response = client.post("/api/v1/optimize", json={"sql": "SELECT 1", "database": "mysql"})
    
    assert response.status_code == 500
    assert "Connection refused" in response.json()["detail"]

def test_optimize_agent_failure(mock_dependencies):
    # Setup agent returning an error dict (as per code logic)
    mock_dependencies["agent"].optimize.return_value = {
        "error": "LLM overloaded"
    }

    response = client.post("/api/v1/optimize", json={"sql": "SELECT 1", "database": "mysql"})
    
    assert response.status_code == 200 # It returns 200 but success=False based on implementation
    data = response.json()
    assert data["success"] is False
    assert "optimization failed" in data["data"]["explanation"].lower()
