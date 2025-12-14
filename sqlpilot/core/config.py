import os
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

class DatabaseConfig(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: str

class ShadowDatabaseConfig(BaseModel):
    mysql: Optional[DatabaseConfig] = None
    postgresql: Optional[DatabaseConfig] = None

class LLMProviderConfig(BaseModel):
    api_key: str
    model: str
    base_url: str

class LLMConfig(BaseModel):
    default_provider: str = "qwen"
    qwen: Optional[LLMProviderConfig] = None
    deepseek: Optional[LLMProviderConfig] = None
    glm: Optional[LLMProviderConfig] = None
    openai: Optional[LLMProviderConfig] = None
    ollama: Optional[LLMProviderConfig] = None

class ValidationConfig(BaseModel):
    sample_size: int = 1000
    performance_runs: int = 3
    timeout: int = 30

class SecurityConfig(BaseModel):
    forbidden_operations: List[str] = [
        "DROP", "TRUNCATE", "DELETE", "UPDATE", "INSERT", "ALTER", "GRANT", "REVOKE"
    ]
    max_result_rows: int = 10000

class Settings(BaseSettings):
    server: ServerConfig
    shadow_database: ShadowDatabaseConfig
    llm: LLMConfig
    validation: ValidationConfig
    security: SecurityConfig

    model_config = SettingsConfigDict(
        env_nested_delimiter='__',
        env_file='.env',
        extra='ignore'
    )

    @classmethod
    def load_from_yaml(cls, path: str = "config/config.example.yaml") -> "Settings":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, "r") as f:
            yaml_data = yaml.safe_load(f)
            
        return cls(**yaml_data)

# Global settings instance
try:
    # Try to load from config.yaml if it exists, otherwise use example
    config_path = os.getenv("SQLPILOT_CONFIG", "config/config.yaml")
    if not os.path.exists(config_path):
        config_path = "config/config.example.yaml"
    
    settings = Settings.load_from_yaml(config_path)
except Exception as e:
    print(f"Warning: Failed to load config from {config_path}: {e}")
    # Initialize with defaults if loading fails (might fail validation if fields are missing)
    # in a real scenario we might want to exit or provide safe defaults
    pass
