from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class OptimizeOptions(BaseModel):
    llm_provider: Optional[str] = "qwen"
    sample_size: Optional[int] = 1000

class OptimizeRequest(BaseModel):
    sql: str
    database: str = "mysql"
    options: Optional[OptimizeOptions] = None

class ValidationResult(BaseModel):
    semantic_check: Dict[str, Any]
    performance_check: Dict[str, Any]
    boundary_tests: Optional[Dict[str, Any]] = None

class DiagnosisResult(BaseModel):
    root_cause: str
    bottlenecks: List[str]

class OptimizeResponseData(BaseModel):
    original_sql: str
    optimized_sql: Optional[str] = None
    diagnosis: Optional[DiagnosisResult] = None
    validation: Optional[ValidationResult] = None
    confidence: Optional[str] = None
    recommendation: Optional[str] = None
    explanation: Optional[str] = None

class OptimizeResponse(BaseModel):
    success: bool
    data: OptimizeResponseData
    meta: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    components: Dict[str, str]
