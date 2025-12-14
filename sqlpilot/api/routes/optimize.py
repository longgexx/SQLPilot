import time
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlpilot.api.models import OptimizeRequest, OptimizeResponse
from sqlpilot.core.config import settings
from sqlpilot.database.mysql import MySQLAdapter
from sqlpilot.core.tools import AgentTools
from sqlpilot.core.llm import LLMService
from sqlpilot.core.agent import SQLAgent

router = APIRouter()

@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_sql(request: OptimizeRequest):
    start_time = time.time()
    
    # 1. Setup Resources
    if request.database != "mysql":
        raise HTTPException(status_code=400, detail="Only mysql is currently supported")
    
    if not settings.shadow_database.mysql:
        raise HTTPException(status_code=500, detail="MySQL not configured")
        
    db = MySQLAdapter(settings.shadow_database.mysql)
    
    try:
        await db.connect()
        
        # 2. Setup Agent
        tools = AgentTools(db, settings)
        llm_config = settings.llm
        # TODO: Allow overriding provider from request.options
        
        llm = LLMService(llm_config)
        agent = SQLAgent(llm, tools)
        
        # 3. Serialize execution
        result = await agent.optimize(request.sql, request.database)
        
        # Ensure original_sql is present for response validation
        if "original_sql" not in result:
            result["original_sql"] = request.sql

        # Handle agent error case
        if "error" in result:
             # Create a valid response even if error occurred
             result["explanation"] = f"Optimization failed: {result.get('error')}"
             result["confidence"] = "LOW"
             result["recommendation"] = "reject"
             # If raw content exists, maybe put it in explanation or ignore
             if "diagnosis" not in result:
                 result["diagnosis"] = {"root_cause": "Unknown error", "bottlenecks": []}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()

    processing_time = (time.time() - start_time) * 1000
    
    return OptimizeResponse(
        success="error" not in result,
        data=result, 
        meta={
            "processing_time_ms": processing_time,
            "request_id": "TODO" # Add UUID
        }
    )

# TODO: Implement /optimize/stream (requires Agent refactoring to yield events)
