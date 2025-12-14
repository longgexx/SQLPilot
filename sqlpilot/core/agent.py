import json
import asyncio
from typing import Dict, Any, List, Optional
from sqlpilot.core.llm import LLMService
from sqlpilot.core.tools import AgentTools
from sqlpilot.prompts.main_agent import SYSTEM_PROMPT
import logging

logger = logging.getLogger(__name__)

class SQLAgent:
    def __init__(self, llm: LLMService, tools: AgentTools):
        self.llm = llm
        self.tools = tools
        self.tool_definitions = tools.get_tool_definitions()
        self.max_iterations = 30

    async def optimize(self, sql: str, database_type: str = "mysql") -> Dict[str, Any]:
        """
        Main optimization loop.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Please optimize this SQL for {database_type}:\n\n{sql}"}
        ]

        logger.info(f"Starting optimization for SQL: {sql[:50]}...")
        
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            # Call LLM
            response = await self.llm.chat(messages, tools=self.tool_definitions)
            message = response.choices[0].message
            
            # Add assistant message to history
            messages.append(message.model_dump())

            # Check if tools are called
            if message.tool_calls:
                # Handle tool calls
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Agent calling tool: {function_name} with {arguments}")
                    
                    # Execute tool
                    if hasattr(self.tools, function_name):
                        tool_func = getattr(self.tools, function_name)
                        try:
                            if asyncio.iscoroutinefunction(tool_func):
                                result = await tool_func(**arguments)
                            else:
                                result = tool_func(**arguments)
                        except Exception as e:
                            result = f"Error executing {function_name}: {str(e)}"
                    else:
                        result = f"Error: Tool {function_name} not found"
                    
                    # Append tool result to history
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": str(result)
                    })
            else:
                # No tool calls, assume final answer
                content = message.content
                if content:
                    try:
                        # Attempt to parse specific JSON block if wrapped in markdown
                        if "```json" in content:
                            json_str = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            json_str = content.split("```")[1].strip()
                        else:
                            json_str = content
                        
                        final_result = json.loads(json_str)

                        # --- ITERATIVE FEEDBACK LOOP ---
                        # Check strictness of output
                        if "validation" in final_result and "performance_check" in final_result["validation"]:
                            perf = final_result["validation"]["performance_check"]
                            ratio = perf.get("improvement_ratio", 1.0)
                            status = perf.get("status", "unknown")
                            recommendation = final_result.get("recommendation", "manual_review")
                            
                            # Threshold for "good enough" improvement (e.g., 10% gain = 1.1x)
                            # Or if the recommendation is explicitly 'reject' (meaning Agent gave up or found no issue)
                            
                            is_rejected = recommendation == "reject"
                            is_minimal_gain = isinstance(ratio, (int, float)) and ratio < 1.1

                            # If we are not done (minimal gain AND not rejected yet), prompt for retry
                            # But we must avoid infinite loops if the agent really thinks it's the best.
                            # We can rely on the Agent's "recommendation" field. 
                            # If Agent says "auto_apply" or "manual_review" BUT gain is low, we challenge it.
                            
                            if not is_rejected and is_minimal_gain:
                                # We only challenge if we haven't challenged this specific outcome too many times?
                                # For now, let's just challenge once per "solution" finding step, but relying on max_iterations to bail us out.
                                # A better way is to check if the Agent explicitly argued "Optimal already".
                                
                                # Let's construct a feedback message.
                                feedback = (
                                    f"System Feedback: The optimization proposed only shows an improvement ratio of {ratio}. "
                                    "This is considered insufficient (< 1.1). "
                                    "Please try a DIFFERENT approach (e.g. check for missing indexes, different join types, or schema changes). "
                                    "If you firmly believe no further optimization is possible, please set 'recommendation' to 'reject' "
                                    "and explain why in 'explanation'."
                                )
                                
                                logger.info(f"Triggering feedback loop: {feedback}")
                                messages.append({"role": "user", "content": feedback})
                                continue # NEXT ITERATION

                        return final_result

                    except json.JSONDecodeError:
                         # If parsing fails, return raw content but wrapped
                        logger.warning("Failed to parse JSON from final response")
                        return {
                            "error": "Failed to parse Agent output",
                            "raw_content": content
                        }
                break

        return {
            "error": "Max iterations reached", 
            "last_message": messages[-1].get("content") if messages else ""
        }
