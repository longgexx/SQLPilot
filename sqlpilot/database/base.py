from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class DatabaseAdapter(ABC):
    """Abstract base class for database adapters."""

    @abstractmethod
    async def connect(self):
        """Establish connection to the database."""
        pass

    @abstractmethod
    async def close(self):
        """Close the database connection."""
        pass

    @abstractmethod
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get table schema including columns, indexes, and constraints."""
        pass

    @abstractmethod
    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get table statistics like row count and index cardinality."""
        pass

    @abstractmethod
    async def explain_sql(self, sql: str) -> Dict[str, Any]:
        """Get execution plan for the SQL."""
        pass

    @abstractmethod
    async def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        pass
    
    @abstractmethod
    async def get_version(self) -> str:
        """Get database version."""
        pass
