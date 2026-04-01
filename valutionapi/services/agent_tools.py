"""
agent_tools.py
--------------
Tool Registry & Execution Layer for Financial Intelligence Agent

Auto-discovers FastAPI endpoints and converts them into callable agent tools.
"""

import httpx
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime


class ToolRegistry:
    """Registry of all available tools the agent can call."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.tools = self._register_tools()
    
    def _register_tools(self) -> Dict[str, Dict[str, Any]]:
        """Auto-register all available tools with their schemas."""
        return {
            "stock_valuation": {
                "name": "stock_valuation",
                "description": "Get ML-based stock valuation prediction (Undervalued/Fair/Overvalued)",
                "endpoint": "/predict/",
                "method": "POST",
                "input_schema": {
                    "ticker": "str (stock ticker symbol)",
                    "user_id": "str (user identifier)"
                },
                "output_schema": {
                    "predicted_label": "int (0=Undervalued, 1=Fair, 2=Overvalued)",
                    "label_text": "str",
                    "graham_value": "float",
                    "current_price": "float",
                    "confidence": "float",
                    "shap_summary": "dict"
                },
                "when_to_use": "ALWAYS use for stock valuation queries"
            },
            
            "shap_explain": {
                "name": "shap_explain",
                "description": "Get SHAP explainability for why a stock is valued a certain way",
                "endpoint": "/explain/",
                "method": "POST",
                "input_schema": {
                    "ticker": "str",
                    "user_id": "str"
                },
                "output_schema": {
                    "predicted_label": "int",
                    "label_text": "str",
                    "shap_explanation": "dict with feature importance",
                    "top_positive_features": "list",
                    "top_negative_features": "list",
                    "beginner_explanation": "str"
                },
                "when_to_use": "Use when user asks 'why', 'explain', 'how come', or wants deeper insights"
            },
            
            "portfolio_risk": {
                "name": "portfolio_risk",
                "description": "Analyze portfolio risk with weighted multi-stock valuation",
                "endpoint": "/predict/portfolio",
                "method": "POST",
                "input_schema": {
                    "user_id": "str",
                    "portfolio_name": "str",
                    "tickers": "list[str]",
                    "weights": "list[float] (must sum to 1.0)"
                },
                "output_schema": {
                    "portfolio_risk_score": "float (0-1)",
                    "portfolio_classification": "str (Low/Medium/High)",
                    "stocks": "list of stock predictions with weights",
                    "aggregated_shap": "dict with portfolio-level feature importance"
                },
                "when_to_use": "Use for portfolio analysis, risk assessment, multi-stock queries"
            },
            
            "portfolio_risk_from_saved": {
                "name": "portfolio_risk_from_saved",
                "description": "Analyze risk for a saved portfolio with holdings from database",
                "endpoint": "/predict/portfolio/{user_id}/{name}/predict",
                "method": "POST",
                "input_schema": {
                    "user_id": "str",
                    "name": "str (portfolio name)"
                },
                "output_schema": {
                    "portfolio_risk_score": "float",
                    "portfolio_classification": "str",
                    "total_value": "float",
                    "stocks": "list with shares and values"
                },
                "when_to_use": "Use when user references a saved portfolio by name"
            },
            
            "user_suggestions": {
                "name": "user_suggestions",
                "description": "Get personalized stock suggestions based on user history",
                "endpoint": "/suggestions/{user_id}",
                "method": "GET",
                "input_schema": {
                    "user_id": "str",
                    "top_n": "int (default 5)"
                },
                "output_schema": {
                    "top_sector": "str",
                    "suggestions": "list of recommended tickers with predictions"
                },
                "when_to_use": "Use when user asks for recommendations or 'what should I invest in'"
            },
            
            "portfolio_suggestions": {
                "name": "portfolio_suggestions",
                "description": "Get suggestions based on holdings in a specific portfolio",
                "endpoint": "/portfolio_suggestions/{user_id}/{portfolio_name}",
                "method": "GET",
                "input_schema": {
                    "user_id": "str",
                    "portfolio_name": "str",
                    "top_n": "int (default 10)",
                    "sector_count": "int (default 3)"
                },
                "output_schema": {
                    "top_sectors": "list[str]",
                    "suggestions": "list of tickers"
                },
                "when_to_use": "Use for portfolio-specific recommendations"
            },
            
            "get_user_predictions": {
                "name": "get_user_predictions",
                "description": "Get user's recent prediction history",
                "endpoint": "/predictions/user/{user_id}",
                "method": "GET",
                "input_schema": {
                    "user_id": "str",
                    "limit": "int (default 10)"
                },
                "output_schema": {
                    "predictions": "list of past predictions with timestamps"
                },
                "when_to_use": "Use to understand user history for context"
            },
            
            "list_portfolios": {
                "name": "list_portfolios",
                "description": "List all portfolios for a user",
                "endpoint": "/predict/portfolio/{user_id}",
                "method": "GET",
                "input_schema": {
                    "user_id": "str"
                },
                "output_schema": {
                    "portfolios": "list with names and risk metrics"
                },
                "when_to_use": "Use when user asks 'what portfolios do I have' or 'show my portfolios'"
            },
            
            "get_portfolio": {
                "name": "get_portfolio",
                "description": "Get details of a specific portfolio with holdings",
                "endpoint": "/predict/portfolio/{user_id}/{name}",
                "method": "GET",
                "input_schema": {
                    "user_id": "str",
                    "name": "str"
                },
                "output_schema": {
                    "portfolio": "dict with holdings and risk info"
                },
                "when_to_use": "Use to view portfolio details before analysis"
            }
        }
    
    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool definition by name."""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self.tools.keys())
    
    def get_tool_description(self, tool_name: str) -> str:
        """Get human-readable tool description."""
        tool = self.get_tool(tool_name)
        if not tool:
            return f"Unknown tool: {tool_name}"
        return f"{tool['name']}: {tool['description']}\nUse when: {tool['when_to_use']}"


class ToolExecutor:
    """Executes tool calls against FastAPI endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.registry = ToolRegistry(base_url)
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call.
        
        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool
            
        Returns:
            Tool execution result as dict
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {
                "error": f"Unknown tool: {tool_name}",
                "available_tools": self.registry.list_tools()
            }
        
        try:
            # Build endpoint URL with path params if needed
            endpoint = tool["endpoint"]
            
            # Handle path parameters (e.g., /portfolio/{user_id}/{name})
            if "{user_id}" in endpoint and "user_id" in params:
                endpoint = endpoint.replace("{user_id}", params["user_id"])
            if "{name}" in endpoint and "name" in params:
                endpoint = endpoint.replace("{name}", params["name"])
            if "{portfolio_name}" in endpoint and "portfolio_name" in params:
                endpoint = endpoint.replace("{portfolio_name}", params["portfolio_name"])
            
            url = f"{self.base_url}{endpoint}"
            
            # Execute request
            async with httpx.AsyncClient(timeout=30.0) as client:
                if tool["method"] == "POST":
                    response = await client.post(url, json=params)
                elif tool["method"] == "GET":
                    # Remove path params from query params
                    query_params = {k: v for k, v in params.items() 
                                   if k not in ["user_id", "name", "portfolio_name"]}
                    response = await client.get(url, params=query_params)
                else:
                    return {"error": f"Unsupported method: {tool['method']}"}
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP {e.response.status_code}",
                "detail": e.response.text,
                "tool": tool_name
            }
        except Exception as e:
            return {
                "error": str(e),
                "tool": tool_name
            }
    
    async def call_stock_valuation(self, ticker: str, user_id: str) -> Dict[str, Any]:
        """Convenience wrapper for stock valuation."""
        return await self.call_tool("stock_valuation", {
            "ticker": ticker,
            "user_id": user_id
        })
    
    async def call_shap_explain(self, ticker: str, user_id: str) -> Dict[str, Any]:
        """Convenience wrapper for SHAP explanation."""
        return await self.call_tool("shap_explain", {
            "ticker": ticker,
            "user_id": user_id
        })
    
    async def call_portfolio_risk(self, user_id: str, portfolio_name: str, 
                                  tickers: List[str], weights: List[float]) -> Dict[str, Any]:
        """Convenience wrapper for portfolio risk analysis."""
        return await self.call_tool("portfolio_risk", {
            "user_id": user_id,
            "portfolio_name": portfolio_name,
            "tickers": tickers,
            "weights": weights
        })
    
    async def call_user_suggestions(self, user_id: str, top_n: int = 5) -> Dict[str, Any]:
        """Convenience wrapper for user suggestions."""
        return await self.call_tool("user_suggestions", {
            "user_id": user_id,
            "top_n": top_n
        })
