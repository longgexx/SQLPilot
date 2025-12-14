import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlpilot.database.base import DatabaseAdapter
from sqlpilot.core.config import Settings, SecurityConfig
from sqlpilot.core.tools import AgentTools

class MockDatabaseAdapter(DatabaseAdapter):
    async def connect(self):
        pass

    async def close(self):
        pass

    async def get_table_schema(self, table_name: str):
        return {
            "columns": [
                {"name": "id", "type": "int", "primary_key": True},
                {"name": "name", "type": "varchar(255)"}
            ],
            "indexes": ["idx_name"]
        }

    async def get_table_statistics(self, table_name: str):
        return {"row_count": 1000, "size_mb": 10}

    async def explain_sql(self, sql: str):
        return {"plan": "Seq Scan on table"}

    async def execute_query(self, sql: str, params: tuple = None):
        if "SELECT * FROM users" in sql:
            return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        return []

    async def get_version(self):
        return "MockDB 1.0"

@pytest.fixture
def mock_db_adapter():
    return MockDatabaseAdapter()

@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=Settings)
    settings.security = SecurityConfig(
        dangerous_keywords=["DROP", "DELETE", "TRUNCATE"],
        max_rows=100
    )
    return settings

@pytest.fixture
def agent_tools(mock_db_adapter, mock_settings):
    return AgentTools(mock_db_adapter, mock_settings)
