import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_get_table_schema(agent_tools):
    schema_json = await agent_tools.get_table_schema("users")
    schema = json.loads(schema_json)
    assert schema["columns"][0]["name"] == "id"
    assert "indexes" in schema

@pytest.mark.asyncio
async def test_get_table_schema_error(agent_tools):
    agent_tools.db.get_table_schema = AsyncMock(side_effect=Exception("DB Error"))
    result = await agent_tools.get_table_schema("users")
    assert "Error getting schema" in result

@pytest.mark.asyncio
async def test_get_table_statistics(agent_tools):
    stats_json = await agent_tools.get_table_statistics("users")
    stats = json.loads(stats_json)
    assert stats["row_count"] == 1000

@pytest.mark.asyncio
async def test_explain_sql(agent_tools):
    plan_json = await agent_tools.explain_sql("SELECT * FROM users")
    plan = json.loads(plan_json)
    assert plan["plan"] == "Seq Scan on table"

@pytest.mark.asyncio
async def test_execute_and_compare_success(agent_tools):
    # Mock execute_query to return same results for both
    # The mock_db_adapter in conftest already returns specific data for "SELECT * FROM users"
    # We need to ensure specific data is returned for our test queries if they differ from default
    
    # Let's override the execute_query of the instance's db for this specific test if needed,
    # but the default mock handles "SELECT * FROM users".
    
    orig_sql = "SELECT * FROM users"
    opt_sql = "SELECT * FROM users /* optimized */"
    
    # We need to ensure the mock logic in conftest matches these queries or is generic enough.
    # The default mock implementation checks for "SELECT * FROM users" in the sql string.
    # So both should match.

    result_json = await agent_tools.execute_and_compare(orig_sql, opt_sql)
    result = json.loads(result_json)
    
    assert result["status"] == "passed"
    assert result["hash_match"] is True

@pytest.mark.asyncio
async def test_execute_and_compare_unsafe_sql(agent_tools):
    # Security config mocks dangerous keywords like DROP
    orig_sql = "DROP TABLE users"
    opt_sql = "SELECT * FROM users"
    
    result_json = await agent_tools.execute_and_compare(orig_sql, opt_sql)
    result = json.loads(result_json)
    
    assert result["status"] == "error"
    assert "Original SQL unsafe" in result["message"]

@pytest.mark.asyncio
async def test_execute_and_compare_row_count_mismatch(agent_tools):
    # Override execute_query to return different lengths
    async def side_effect(sql, params=None):
        if "original" in sql:
            return [{"id": 1}]
        return [{"id": 1}, {"id": 2}]
    
    agent_tools.db.execute_query = AsyncMock(side_effect=side_effect)
    
    orig_sql = "SELECT * FROM users -- original"
    opt_sql = "SELECT * FROM users -- optimized"
    
    result_json = await agent_tools.execute_and_compare(orig_sql, opt_sql)
    result = json.loads(result_json)

    assert result["status"] == "failed"
    assert result["reason"] == "row_count_mismatch"

@pytest.mark.asyncio
async def test_measure_performance(agent_tools):
    # Mock execute_query to simply wait a bit (or doing nothing is fast enough)
    agent_tools.db.execute_query = AsyncMock(return_value=[])
    
    result_json = await agent_tools.measure_performance("SELECT 1", runs=2)
    result = json.loads(result_json)
    
    assert "avg_ms" in result
    assert result["runs"] == 2

