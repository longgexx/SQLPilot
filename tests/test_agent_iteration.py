import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlpilot.core.agent import SQLAgent
from sqlpilot.core.llm import LLMService
from sqlpilot.core.tools import AgentTools

@pytest.mark.asyncio
async def test_agent_iterative_feedback(agent_tools):
    # Mock LLM Service
    llm = MagicMock(spec=LLMService)
    
    # We need to simulate a sequence of responses.
    # Response 1: Low improvement (should trigger feedback)
    response_low = MagicMock()
    message_low = MagicMock()
    message_low.tool_calls = None
    message_low.content = """
    ```json
    {
        "original_sql": "SELECT 1",
        "optimized_sql": "SELECT 1",
        "validation": {
            "performance_check": {
                "status": "passed",
                "improvement_ratio": 1.05
            }
        },
        "recommendation": "manual_review"
    }
    ```
    """
    message_low.model_dump.return_value = {"role": "assistant", "content": message_low.content}
    response_low.choices = [MagicMock(message=message_low)]

    # Response 2: High improvement (should be accepted)
    response_high = MagicMock()
    message_high = MagicMock()
    message_high.tool_calls = None
    message_high.content = """
    ```json
    {
        "original_sql": "SELECT 1",
        "optimized_sql": "SELECT 1 optimized",
        "validation": {
            "performance_check": {
                "status": "passed",
                "improvement_ratio": 50.0
            }
        },
        "recommendation": "auto_apply"
    }
    ```
    """
    message_high.model_dump.return_value = {"role": "assistant", "content": message_high.content}
    response_high.choices = [MagicMock(message=message_high)]

    # Configure LLM to return these in sequence
    llm.chat = AsyncMock(side_effect=[response_low, response_high])

    # Initialize Agent
    agent = SQLAgent(llm, agent_tools)
    
    # Run optimization
    result = await agent.optimize("SELECT 1", "mysql")
    
    # Verification
    # 1. Result should be the high improvement one
    assert result["validation"]["performance_check"]["improvement_ratio"] == 50.0
    
    # 2. LLM should have been called twice
    assert llm.chat.call_count == 2
    
    # 3. The input to the second call should contain the feedback message
    second_call_args = llm.chat.call_args_list[1]
    messages = second_call_args[0][0] # first arg is 'messages' list
    
    # Check for the system feedback message
    assert any("System Feedback" in m["content"] for m in messages if m["role"] == "user")
    # assert "insufficient" in messages[-1]["content"] 
    # Because 'messages' is mutable and modified after the call, messages[-1] is the 2nd assistant response.
    # The feedback message should be the second-to-last (or just in the list).
    feedback_msg = next((m for m in messages if "System Feedback" in m["content"]), None)
    assert feedback_msg is not None
    assert "insufficient" in feedback_msg["content"]

