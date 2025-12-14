import json
import asyncio
import time
import hashlib
from typing import List, Dict, Any, Optional
from sqlpilot.database.base import DatabaseAdapter
from sqlpilot.utils.security import SecurityGuard
from sqlpilot.core.config import Settings

class AgentTools:
    def __init__(self, db: DatabaseAdapter, settings: Settings):
        self.db = db
        self.settings = settings
        self.security = SecurityGuard(settings.security)

    async def get_table_schema(self, table_name: str) -> str:
        """Get table schema including columns, indexes, and constraints."""
        try:
            schema = await self.db.get_table_schema(table_name)
            return json.dumps(schema, default=str)
        except Exception as e:
            return f"Error getting schema for {table_name}: {str(e)}"

    async def get_table_statistics(self, table_name: str) -> str:
        """Get table statistics like row count and index cardinality."""
        try:
            stats = await self.db.get_table_statistics(table_name)
            return json.dumps(stats, default=str)
        except Exception as e:
            return f"Error getting statistics for {table_name}: {str(e)}"

    async def explain_sql(self, sql: str) -> str:
        """Get execution plan for the SQL."""
        try:
            plan = await self.db.explain_sql(sql)
            return json.dumps(plan, default=str)
        except Exception as e:
            return f"Error explaining SQL: {str(e)}"

    async def execute_and_compare(self, original_sql: str, optimized_sql: str) -> str:
        """
        Execute both SQLs and compare results to ensure semantic equivalence.
        Returns a JSON string with comparison details.
        """
        # Security checks
        is_safe_orig, err_orig = self.security.validate_sql(original_sql)
        if not is_safe_orig:
            return json.dumps({"status": "error", "message": f"Original SQL unsafe: {err_orig}"})
        
        is_safe_opt, err_opt = self.security.validate_sql(optimized_sql)
        if not is_safe_opt:
            return json.dumps({"status": "error", "message": f"Optimized SQL unsafe: {err_opt}"})

        # Enforce limits
        limited_orig = self.security.enforce_limit(original_sql)
        limited_opt = self.security.enforce_limit(optimized_sql)

        try:
            # Execute both
            res_orig = await self.db.execute_query(limited_orig)
            res_opt = await self.db.execute_query(limited_opt)

            # Compare basic stats
            count_orig = len(res_orig)
            count_opt = len(res_opt)

            if count_orig != count_opt:
                return json.dumps({
                    "status": "failed",
                    "reason": "row_count_mismatch",
                    "original_rows": count_orig,
                    "optimized_rows": count_opt
                })

            # Compare content hash (simple JSON dump hash for now)
            # Sorting keys to ensure stability
            hash_orig = hashlib.md5(json.dumps(res_orig, sort_keys=True, default=str).encode()).hexdigest()
            hash_opt = hashlib.md5(json.dumps(res_opt, sort_keys=True, default=str).encode()).hexdigest()

            if hash_orig != hash_opt:
                return json.dumps({
                    "status": "failed",
                    "reason": "content_mismatch",
                    "details": "Results differ in content but have same row count"
                })

            return json.dumps({
                "status": "passed",
                "rows": count_orig,
                "hash_match": True
            })

        except Exception as e:
            return json.dumps({"status": "error", "message": f"Execution failed: {str(e)}"})

    async def measure_performance(self, sql: str, runs: int = 3) -> str:
        """Measure execution performance of a SQL query."""
        is_safe, err = self.security.validate_sql(sql)
        if not is_safe:
            return json.dumps({"error": err})

        times = []
        try:
            # Warmup (optional, maybe skip for now to save time/resources)
            # await self.db.execute_query(sql) 

            for _ in range(runs):
                start = time.perf_counter()
                await self.db.execute_query(sql)
                end = time.perf_counter()
                times.append((end - start) * 1000) # ms

            return json.dumps({
                "min_ms": min(times),
                "max_ms": max(times),
                "avg_ms": sum(times) / len(times),
                "median_ms": sorted(times)[len(times)//2],
                "runs": runs
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def execute_custom_test(self, test_name: str, original_sql: str, optimized_sql: str, description: str) -> str:
        """Execute a custom test defined by the agent (wrapper around verify)."""
        # For now, this just logs and calls execute_and_compare, but could be extended
        # for specific boundary checks if we had logic to inject params.
        # Since we don't support parameterized SQL injection from Agent yet,
        # we assume the Agent includes the boundary values in the SQL string.
        
        result = await self.execute_and_compare(original_sql, optimized_sql)
        return json.dumps({
            "test_name": test_name,
            "description": description,
            "result": json.loads(result)
        })

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return OpenAI function definitions for these tools."""
        return [
            {
                "name": "get_table_schema",
                "description": "Get schema information for a table including columns and indexes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "Name of the table"}
                    },
                    "required": ["table_name"]
                }
            },
            {
                "name": "get_table_statistics",
                "description": "Get valid statistics for a table like row count and data size.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "Name of the table"}
                    },
                    "required": ["table_name"]
                }
            },
            {
                "name": "explain_sql",
                "description": "Get the execution plan for a SQL query to analyze performance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": " The SQL query to explain"}
                    },
                    "required": ["sql"]
                }
            },
            {
                "name": "execute_and_compare",
                "description": "Execute original and optimized SQLs to verify they return the same results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "original_sql": {"type": "string", "description": "Original SQL query"},
                        "optimized_sql": {"type": "string", "description": "Candidate optimized SQL query"}
                    },
                    "required": ["original_sql", "optimized_sql"]
                }
            },
            {
                "name": "measure_performance",
                "description": "Measure the execution time of a SQL query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "The SQL query to measure"},
                        "runs": {"type": "integer", "description": "Number of times to run", "default": 3}
                    },
                    "required": ["sql"]
                }
            },
            {
                "name": "execute_custom_test",
                "description": "Run a specific test case (e.g. boundary condition) by executing provided SQLs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "test_name": {"type": "string", "description": "Name of the test case"},
                        "original_sql": {"type": "string", "description": "Original SQL with test specific values"},
                        "optimized_sql": {"type": "string", "description": "Optimized SQL with test specific values"},
                        "description": {"type": "string", "description": "Description of what is being tested"}
                    },
                    "required": ["test_name", "original_sql", "optimized_sql", "description"]
                }
            }
        ]
