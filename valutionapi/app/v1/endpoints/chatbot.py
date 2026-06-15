"""
chatbot.py
-------------------
FastAPI endpoint for AI chatbot agent - pure tool orchestration
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from db.database import get_db
from core.security import get_current_registered_user
from models.models import User
from services.chatbot import FinancialIntelligenceAgent

router = APIRouter(prefix="/chat", tags=["Chatbot"])


class ChatRequest(BaseModel):
    user_id: str
    query: str
    

class ChatResponse(BaseModel):
    response: str
    next_best_action: str
    tools_used: List[str]
    errors: List[dict] = []
    recommendations: dict


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_registered_user),
):
    """
    Chat with the AI financial intelligence agent.
    
    The agent orchestrates backend endpoints:
    1. Analyzes your query intent
    2. Calls appropriate endpoints (valuation, SHAP, portfolio, etc.)
    3. Gets personalized recommendations from recommendation service
    4. Formats response with LLM
    5. Suggests next action based on recommendations
    
    Examples:
    - "What's the valuation for AAPL?"
    - "Why is TSLA overvalued?"
    - "Analyze my portfolio risk"
    - "Suggest some stocks for me"
    
    All intelligence comes from backend services - zero custom logic.
    """
    try:
        agent = FinancialIntelligenceAgent(db=db)
        result = await agent.process_query(
            user_id=current_user.user_id,
            query=request.query
        )
        
        return ChatResponse(
            response=result["response"],
            next_best_action=result["next_best_action"],
            tools_used=result["tools_used"],
            errors=result.get("errors", []),
            recommendations=result["recommendations"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/tools")
async def list_available_tools():
    """List all available tools (backend endpoints) the agent can use."""
    from services.agent_tools import ToolRegistry
    registry = ToolRegistry()
    
    tools_info = []
    for tool_name in registry.list_tools():
        tool = registry.get_tool(tool_name)
        tools_info.append({
            "name": tool["name"],
            "description": tool["description"],
            "when_to_use": tool["when_to_use"],
            "endpoint": tool["endpoint"]
        })
    
    return {"tools": tools_info, "total": len(tools_info)}
