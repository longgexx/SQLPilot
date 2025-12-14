from fastapi import APIRouter
from sqlpilot.api.models import HealthResponse
from sqlpilot.core.config import settings
from sqlpilot.database.mysql import MySQLAdapter
from sqlpilot.core.llm import LLMService

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def check_health():
    components = {}
    
    # Check DB
    try:
        if settings.shadow_database.mysql:
            db = MySQLAdapter(settings.shadow_database.mysql)
            await db.connect()
            ver = await db.get_version()
            await db.close()
            components["database"] = f"ok (MySQL {ver})"
        else:
            components["database"] = "not_configured"
    except Exception as e:
        components["database"] = f"failed ({e})"

    # Check LLM
    try:
        LLMService(settings.llm)
        components["llm"] = "ok (initialized)"
    except Exception as e:
        components["llm"] = f"failed ({e})"

    return HealthResponse(
        status="healthy" if "failed" not in str(components.values()) else "degraded",
        components=components
    )
