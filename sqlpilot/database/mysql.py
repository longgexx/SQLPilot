import aiomysql
import logging
import warnings
from typing import List, Dict, Any
from sqlpilot.database.base import DatabaseAdapter
from sqlpilot.core.config import DatabaseConfig

# Suppress aiomysql warnings (like "Field ... won't be calculated")
warnings.filterwarnings("ignore", category=Warning, module="aiomysql")

logger = logging.getLogger(__name__)

class MySQLAdapter(DatabaseAdapter):
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                self.pool = await aiomysql.create_pool(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.user,
                    password=self.config.password,
                    db=self.config.database,
                    autocommit=True,
                    cursorclass=aiomysql.DictCursor
                )
                logger.info(f"Connected to MySQL database at {self.config.host}:{self.config.port}")
            except Exception as e:
                logger.error(f"Failed to connect to MySQL: {e}")
                raise

    async def close(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
            logger.info("Closed MySQL connection pool")

    async def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                return await cur.fetchall()

    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        # Get columns
        columns_sql = f"SHOW COLUMNS FROM {table_name}"
        columns = await self.execute_query(columns_sql)
        
        # Get indexes
        indexes_sql = f"SHOW INDEX FROM {table_name}"
        indexes = await self.execute_query(indexes_sql)
        
        # Get create table statement for full details
        create_sql = f"SHOW CREATE TABLE {table_name}"
        create_stmt = await self.execute_query(create_sql)
        
        return {
            "columns": columns,
            "indexes": indexes,
            "create_statement": create_stmt[0].get("Create Table", "") if create_stmt else ""
        }

    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        # Get basic stats from information_schema
        sql = """
        SELECT table_rows, data_length, index_length 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = %s
        """
        result = await self.execute_query(sql, (self.config.database, table_name))
        
        stats = result[0] if result else {}
        return {
            "row_count": stats.get("table_rows"),
            "data_size_bytes": stats.get("data_length"),
            "index_size_bytes": stats.get("index_length")
        }

    async def explain_sql(self, sql: str) -> Dict[str, Any]:
        # Standard EXPLAIN
        explain_res = await self.execute_query(f"EXPLAIN {sql}")
        
        # EXPLAIN FORMAT=JSON for supported versions (MySQL 5.6+)
        try:
            json_explain_res = await self.execute_query(f"EXPLAIN FORMAT=JSON {sql}")
            json_explain = json_explain_res[0].get("EXPLAIN")
        except Exception:
            json_explain = "Not supported or failed"
            
        return {
            "tabular": explain_res,
            "json": json_explain
        }

    async def get_version(self) -> str:
        res = await self.execute_query("SELECT VERSION()")
        return list(res[0].values())[0] if res else "Unknown"
