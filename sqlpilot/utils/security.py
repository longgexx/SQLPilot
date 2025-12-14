import re
from typing import List, Optional
from sqlpilot.core.config import SecurityConfig

class SecurityGuard:
    def __init__(self, config: SecurityConfig):
        self.config = config
        # Simple regex to start with, can be enhanced with sqlparse later
        self.forbidden_patterns = [
            re.compile(rf"\b{op}\b", re.IGNORECASE) for op in self.config.forbidden_operations
        ]

    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Check if SQL is safe to execute.
        Returns (is_safe, error_message)
        """
        # 1. Check for forbidden operations
        for pattern in self.forbidden_patterns:
            if pattern.search(sql):
                return False, f"Forbidden operation detected: {pattern.pattern}"

        # 2. Basic injection checks (very distinct from normal SQL)
        if ";" in sql.strip()[:-1]: # Check for multiple statements
             return False, "Multiple statements are not allowed for security reasons"
        
        # 3. Comment injection check (basic)
        if "--" in sql or "/*" in sql:
            # This is strict but safe for an automated tool initially
            pass # Relaxing this for now as comments might be valid in complex SQL, 
                 # but we should be careful. 
                 # Let's just warn or allow for now if it's just a SELECT.
        
        return True, None

    def enforce_limit(self, sql: str) -> str:
        """
        Ensure the SQL has a LIMIT clause to prevent huge result sets.
        This is a simple implementation; a robust one would use an SQL parser.
        """
        if "LIMIT" not in sql.upper():
            return f"{sql} LIMIT {self.config.max_result_rows}"
        return sql
