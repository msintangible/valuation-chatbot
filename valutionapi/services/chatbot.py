"""
chatbot.py
----------
Tool-Using LLM Agent for Financial Intelligence Platform

This is a pure tool orchestration agent that:
- Routes user queries to appropriate backend endpoints
- Combines responses from multiple endpoints
- Uses recommendation service for personalization
- Generates natural language responses via LLM

CRITICAL RULES:
- NEVER hallucinates financial data - ALL data comes from endpoints
- NEVER implements business logic - delegates to services
- ALWAYS uses recommendation service for suggestions/next-actions
- Purely orchestrates existing backend endpoints
"""

import os
from dotenv import load_dotenv
from google import genai
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import json
import re

from services.agent_tools import ToolExecutor, ToolRegistry

load_dotenv()


class FinancialIntelligenceAgent:
    """
    Pure Tool Orchestration Agent for Financial Intelligence.
    
    Role: Route user queries → Call appropriate endpoints → Format responses
    
    Tools Available:
    1. Stock valuation endpoint (ML-based)
    2. SHAP explanation endpoint
    3. Portfolio risk endpoint
    4. Recommendation service (for personalization & suggestions)
    5. Prediction history endpoints
    6. Portfolio CRUD endpoints
    
    Intelligence Source: ALL from backend services, NEVER custom logic
    """
    
    def __init__(self, db: Session, base_url: str = "http://localhost:8001"):
        self.db = db
        self.tool_executor = ToolExecutor(base_url)
        self.tool_registry = ToolRegistry(base_url)
        
        # Initialize Gemini client for response formatting only
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        self.llm_client = genai.Client(api_key=api_key)
        
    async def process_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """
        Main entry point - pure tool orchestration.
        
        Flow:
        1. Analyze query intent
        2. Call appropriate endpoints based on intent
        3. Call recommendation service for personalization
        4. Format response with LLM
        5. Use recommendations for next-action
        """
        print(f"➡️ process_query called with: {query}")
        # Step 1: Analyze query intent
        intent = self._analyze_intent(query)

        tickers = intent.get("entities", {}).get("tickers", [])

        ticker_required_intents = ["stock_valuation", "explanation", "comparison"]

        if intent["type"] in ticker_required_intents and not tickers:
            return {
                "response": (
                    "❌ I couldn't detect a valid stock ticker.\n\n"
                    "Please enter a valid ticker symbol like:\n"
                    "- Apple → AAPL\n"
                    "- Tesla → TSLA\n"
                    "- Microsoft → MSFT\n\n"
                    "Example: 'Is AAPL undervalued?'"
                ),
                "next_best_action": "Try asking about a specific stock ticker (e.g., AAPL)",
                "tools_used": [],
                "recommendations": {"top_sectors": [], "suggested_tickers": []}
            }
        
        # Step 2: Execute endpoints based on intent
        tool_results = await self._execute_tools(user_id, query, intent)
        
        # Step 3: Get personalized recommendations from backend service
        should_get_recommendations = (
                intent["type"] == "suggestions"
                or (intent["type"] == "general" and not tickers)
        )

        if should_get_recommendations:
            recommendations = await self._get_recommendations(user_id, intent, tool_results)
        else:
            recommendations = {"top_sector": [], "suggestions": []}
        
        # Step 4: Generate response using tool data + recommendations
        response = await self._generate_response(
            query=query,
            intent=intent,
            tool_results=tool_results,
            recommendations=recommendations
        )
        
        # Step 5: Extract next-action from recommendations
        next_action = self._extract_next_action(intent, recommendations)
        
        return {
            "response": response,
            "next_best_action": next_action,
            "tools_used": [r["tool"] for r in tool_results if "tool" in r],
            "recommendations": {
                "top_sectors": recommendations.get("top_sectors", []),
                "suggested_tickers": [s.get("ticker") for s in recommendations.get("suggestions", [])[:3]]
            }
        }
    
    def _analyze_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine intent and extract entities.
        
        Intents:
        - stock_valuation: User wants to know if stock is under/over valued
        - explanation: User wants to know WHY (SHAP)
        - portfolio_risk: User wants portfolio analysis
        - suggestions: User wants recommendations
        - comparison: User wants to compare stocks
        - history: User wants to see past predictions
        """
        query_lower = query.lower()
        
        intent = {
            "type": "unknown",
            "confidence": 0.0,
            "entities": {},
            "needs_explanation": False,
            "needs_risk_analysis": False
        }


        tickers = self._extract_tickers(query)

        if tickers:
            intent["entities"]["tickers"] = tickers

        # Detect portfolio keywords
        portfolio_keywords = ["portfolio", "holdings", "my stocks", "all my"]
        if any(kw in query_lower for kw in portfolio_keywords):
            intent["type"] = "portfolio_risk"
            intent["confidence"] = 0.9
            intent["needs_risk_analysis"] = True
            return intent
        
        # Detect explanation keywords
        explanation_keywords = ["why", "explain", "how come", "reason", "because", "shap"]
        if any(kw in query_lower for kw in explanation_keywords):
            intent["needs_explanation"] = True
            if tickers:
                intent["type"] = "explanation"
                intent["confidence"] = 0.95
                return intent
        
        # Detect suggestion keywords
        suggestion_keywords = ["suggest", "recommend", "what should i", "ideas", "options"]
        if any(kw in query_lower for kw in suggestion_keywords):
            intent["type"] = "suggestions"
            intent["confidence"] = 0.85
            return intent
        
        # Detect comparison keywords
        comparison_keywords = ["compare", "versus", "vs", "better", "which one"]
        if any(kw in query_lower for kw in comparison_keywords) and len(tickers) >= 2:
            intent["type"] = "comparison"
            intent["confidence"] = 0.9
            intent["entities"]["tickers"] = tickers[:5]  # Limit to 5
            return intent
        
        # Detect valuation keywords
        valuation_keywords = ["value", "worth", "price", "overvalued", "undervalued", "fair"]
        if any(kw in query_lower for kw in valuation_keywords) and tickers:
            intent["type"] = "stock_valuation"
            intent["confidence"] = 0.9
            return intent
        
        # Default: if ticker found, assume valuation
        if tickers:
            intent["type"] = "stock_valuation"
            intent["confidence"] = 0.7
            return intent
        
        # No clear intent
        intent["type"] = "general"
        intent["confidence"] = 0.5
        return intent
    
    def _extract_tickers(self, query: str) -> List[str]:
        """
        Extract stock ticker symbols from query.
        Simple validation: looks for 1-5 uppercase letters.
        """
        # Step 1: Regex
        tickers = re.findall(r'\b[A-Z]{1,5}\b', query)

        # Step 2: Only ONE fallback attempt
        if not tickers:
            llm_tickers = self._llm_extract_tickers(query)
            if llm_tickers:
                tickers = llm_tickers

        # Step 3: Clean + dedupe
        seen = set()
        valid_tickers = []

        for ticker in tickers:
            ticker = ticker.upper().strip()
            if re.match(r'^[A-Z]{1,5}$', ticker) and ticker not in seen:
                seen.add(ticker)
                valid_tickers.append(ticker)

        return valid_tickers



    
    def _llm_extract_tickers(self, query: str) -> List[str]:
        """
        Use LLM to intelligently extract company names and convert to tickers.
        Fast, simple, handles any company.
        """
        try:
            prompt = f"""Extract stock ticker symbols from this query.

Query: "{query}"

Rules:
1. Identify company names (e.g., "Apple" → AAPL, "Cisco" → CSCO)
2. Handle typos (e.g., "ciscos" → CSCO)
3. Return ONLY valid US stock tickers
4. If no company found, return "NONE"

Format: Return tickers separated by commas, or "NONE"
Examples:
- "What's Apple worth?" → AAPL
- "Show me ciscos value" → CSCO  
- "Compare Tesla and Google" → TSLA,GOOGL
- "How are you?" → NONE

Tickers:"""

            response = self.llm_client.models.generate_content(
                model="gemini-2.5-flash",  # ✅ Valid model name
                contents=prompt
            )
            
            result = response.text.strip()
            
            # Parse response
            if result.upper() == "NONE" or not result:
                return []
            
            # Extract tickers (comma-separated or space-separated)
            tickers = re.findall(r'\b[A-Z]{2,5}\b', result)
            return tickers
            
        except Exception as e:
            print(f"LLM ticker extraction failed: {e}")
            return []
    
    async def _execute_tools(
        self, 
        user_id: str, 
        query: str, 
        intent: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Route to appropriate endpoints based on intent.
        
        ROUTING RULES (pure delegation to backend):
        - stock_valuation → /predict/ endpoint
        - explanation → /predict/ + /explain/ endpoints
        - portfolio_risk → /predict/portfolio endpoints
        - suggestions → /suggestions/ endpoint (recommendation service)
        - comparison → Multiple /predict/ calls
        """
        results = []
        
        intent_type = intent["type"]
        tickers = intent["entities"].get("tickers", [])
        
        # Rule 1: Stock valuation queries
        if intent_type == "stock_valuation" and tickers:
            ticker = tickers[0]
            try:
                valuation = await self.tool_executor.call_stock_valuation(ticker, user_id)
                print(f"🔍 DEBUG: Valuation response for {ticker}:")
                print(f"   Type: {type(valuation)}")
                print(f"   Keys: {valuation.keys() if isinstance(valuation, dict) else 'N/A'}")
                print(f"   Data: {valuation}")
                results.append({"tool": "stock_valuation", "data": valuation})
            except Exception as e:
                print(f"Error calling stock_valuation for {ticker}: {e}")
                results.append({"tool": "stock_valuation", "error": str(e)})
        
        # Rule 2: Explanation queries (always include SHAP)
        elif intent_type == "explanation" and tickers:
            ticker = tickers[0]
            try:
                # Get valuation
                valuation = await self.tool_executor.call_stock_valuation(ticker, user_id)
                results.append({"tool": "stock_valuation", "data": valuation})
                
                # Get SHAP explanation
                explanation = await self.tool_executor.call_shap_explain(ticker, user_id)
                results.append({"tool": "shap_explain", "data": explanation})
            except Exception as e:
                print(f"Error calling explanation for {ticker}: {e}")
                results.append({"tool": "explanation", "error": str(e)})
        
        # Rule 3: Portfolio risk queries
        elif intent_type == "portfolio_risk":
            try:
                # List portfolios
                portfolios_data = await self.tool_executor.call_tool("list_portfolios", {
                    "user_id": user_id
                })
                results.append({"tool": "list_portfolios", "data": portfolios_data})
                
                # Analyze first portfolio if exists
                if isinstance(portfolios_data, list) and len(portfolios_data) > 0:
                    portfolio_name = portfolios_data[0].get("name")
                    if portfolio_name:
                        risk_analysis = await self.tool_executor.call_tool(
                            "portfolio_risk_from_saved",
                            {"user_id": user_id, "name": portfolio_name}
                        )
                        results.append({"tool": "portfolio_risk", "data": risk_analysis})
            except Exception as e:
                print(f"Error calling portfolio_risk: {e}")
                results.append({"tool": "portfolio_risk", "error": str(e)})
        
        # Rule 4: Suggestions (delegates to recommendation service)
        elif intent_type == "suggestions":
            try:
                suggestions = await self.tool_executor.call_user_suggestions(user_id, top_n=5)
                results.append({"tool": "user_suggestions", "data": suggestions})
            except Exception as e:
                print(f"Error calling suggestions: {e}")
                results.append({"tool": "user_suggestions", "error": str(e)})
        
        # Rule 5: Comparison
        elif intent_type == "comparison" and len(tickers) >= 2:
            for ticker in tickers[:3]:  # Compare up to 3
                try:
                    valuation = await self.tool_executor.call_stock_valuation(ticker, user_id)
                    results.append({"tool": "stock_valuation", "ticker": ticker, "data": valuation})
                except Exception as e:
                    print(f"Error calling stock_valuation for {ticker}: {e}")
        
        # Debug: Print if no tools were executed
        if not results:
            print(f"⚠️ No tools executed for intent: {intent_type}, tickers: {tickers}")
        
        return results
    
    async def _get_recommendations(
        self,
        user_id: str,
        intent: Dict[str, Any],
        tool_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get personalized recommendations from backend service.
        
        CRITICAL: Only called when user explicitly asks for suggestions.
        """
        # Only call suggestions endpoint when user asks for suggestions
        intent_type = intent.get("type", "general")
        
        if intent_type == "suggestions":
            try:
                recommendations = await self.tool_executor.call_user_suggestions(user_id, top_n=5)
                
                if "error" in recommendations:
                    return {"top_sectors": [], "suggestions": []}
                
                return recommendations
                
            except Exception as e:
                print(f"Error getting recommendations: {e}")
                return {"top_sectors": [], "suggestions": []}
        
        # For other intents, don't call suggestions
        return {"top_sectors": [], "suggestions": []}
    
    async def _generate_response(
        self,
        query: str,
        intent: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        recommendations: Dict[str, Any]
    ) -> str:
        """
        Generate natural language response using LLM.
        
        LLM role: Format and structure endpoint data ONLY
        Intelligence source: Backend services (tool results + recommendations)
        
        Response format:
        🧠 Summary
        📊 Valuation Result  
        🔍 SHAP Explanation (if available)
        ⚖️ Interpretation
        📈 Portfolio/Risk Insight (if available)
        💡 Personalized Suggestions (from recommendation service)
        """
        
        # Quick fallback for simple queries to avoid LLM timeout
        intent_type = intent.get("type", "general")
        if intent_type == "stock_valuation" and len(tool_results) == 1:
            # Use fallback directly for simple valuation queries
            return self._build_fallback_response(query, intent, tool_results, recommendations)
        
        # Build context from tool results
        context = self._build_context_from_tools(tool_results)
        
        # Build prompt with recommendations
        prompt = self._build_llm_prompt(query, intent, context, recommendations)
        
        # Call LLM with timeout
        try:
            response = self.llm_client.models.generate_content(
                model="gemini-2.5-flash",  # ✅ Valid model name
                contents=prompt
            )
            
            return response.text
        except Exception as e:
            print(f"⚠️ LLM call failed: {e}")
            # Fallback to structured response
            return self._build_fallback_response(query, intent, tool_results, recommendations)
    
    def _build_context_from_tools(self, tool_results: List[Dict[str, Any]]) -> str:
        """Build context string from tool results."""
        if not tool_results:
            return "No tool data available."
        
        context_parts = []
        for result in tool_results:
            tool_name = result.get("tool", "unknown")
            data = result.get("data", {})
            
            if "error" in data:
                context_parts.append(f"[{tool_name}] Error: {data['error']}")
            else:
                context_parts.append(f"[{tool_name}]\n{json.dumps(data, indent=2)}")
        
        return "\n\n".join(context_parts)
    
    def _build_llm_prompt(
        self,
        query: str,
        intent: Dict[str, Any],
        context: str,
        recommendations: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM - pure formatting, no custom intelligence."""

        top_sector = recommendations.get("top_sector")
        suggestions = recommendations.get("suggestions", [])

        
        # Extract suggestion tickers for display
        suggested_tickers = [s.get("ticker", "") for s in suggestions[:3] if s.get("ticker")]
        
        prompt = f"""You are a financial intelligence AI assistant that formats data from backend services.

USER QUERY: {query}

TOOL RESULTS (from backend endpoints):
{context}

PERSONALIZED RECOMMENDATIONS (from recommendation service):
- Top sectors of interest: {top_sector}
- Suggested tickers: {suggested_tickers}

CRITICAL RULES:
1. NEVER make up financial data - use tool results ONLY
2. All insights must come from tool results or recommendations
3. Format the data clearly and professionally
4. Include personalized suggestions from recommendation service

RESPONSE FORMAT:
🧠 **Summary** (1-2 sentences based on tool data)

📊 **Valuation Result** (if available from tools)
- Prediction: [from tool]
- Confidence: [from tool]
- Current Price vs Graham Value: [from tool]

🔍 **Key Factors** (if SHAP data available)
- [List top factors from SHAP tool results]

⚖️ **Interpretation**
- [What the tool results mean for the investor]

📈 **Portfolio Context** (if portfolio tools were called)
- [Risk and portfolio insights from tools]

💡 **Personalized Suggestions** (from recommendation service)
- Sectors you're interested in: {top_sector}
- Recommended tickers to explore: {suggested_tickers}

Keep it clear, actionable, and data-driven. All data from endpoints only."""
        
        return prompt
    
    def _build_fallback_response(
        self,
        query: str,
        intent: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        recommendations: Dict[str, Any]
    ) -> str:
        """Build fallback response if LLM fails - still uses endpoint data only."""
        
        response_parts = ["🧠 **Financial Intelligence Agent**\n"]
        
        # Add tool results summary
        for result in tool_results:
            tool_name = result.get("tool", "unknown")
            data = result.get("data", {})
            
            if tool_name == "stock_valuation":
                # Endpoint returns: label, confidence, current_price, graham_value
                label = data.get("label", "N/A")
                confidence = data.get("confidence", 0)
                price = data.get("current_price", 0)
                graham_value = data.get("graham_value", 0)
                response_parts.append(
                    f"📊 **Valuation**: {label} (Confidence: {confidence:.1%})\n"
                    f"Current Price: ${price:.2f} | Graham Value: ${graham_value:.2f}"
                )
            
            elif tool_name == "shap_explain":
                response_parts.append("🔍 **Explanation Available**\n")
                if "beginner_explanation" in data:
                    response_parts.append(data["beginner_explanation"])
        
        # Add recommendations from service
        top_sectors = recommendations.get("top_sectors", []) or [recommendations.get("top_sector", "")]
        suggestions = recommendations.get("suggestions", [])
        
        if top_sectors and any(top_sectors):
            response_parts.append(f"\n💡 **Your Top Sectors**: {', '.join(filter(None, top_sectors))}")
        
        if suggestions:
            tickers = [s.get("ticker") for s in suggestions[:3] if s.get("ticker")]
            if tickers:
                response_parts.append(f"**Recommended Tickers**: {', '.join(tickers)}")
        
        return "\n\n".join(response_parts)
    
    def _extract_next_action(
        self,
        intent: Dict[str, Any],
        recommendations: Dict[str, Any]
    ) -> str:
        """
        Extract next-action suggestion from recommendation service.
        
        CRITICAL: Use recommendation service data ONLY, no custom logic.
        The backend service provides personalized suggestions based on user history.
        """
        
        intent_type = intent["type"]
        top_sectors = recommendations.get("top_sectors", []) or [recommendations.get("top_sector", "")]
        suggestions = recommendations.get("suggestions", [])
        
        # Format suggestions from recommendation service
        if suggestions:
            top_tickers = [s.get("ticker") for s in suggestions[:3] if s.get("ticker")]
            
            if intent_type == "stock_valuation":
                if top_sectors and any(top_sectors):
                    sectors_text = ', '.join(filter(None, top_sectors))
                    return f"Want to explore more stocks in your top sectors ({sectors_text})? Try: {', '.join(top_tickers)}"
                else:
                    return f"Based on your history, you might like: {', '.join(top_tickers)}"
            
            elif intent_type == "explanation":
                return f"Want to compare with similar opportunities? Check: {', '.join(top_tickers)}"
            
            elif intent_type == "portfolio_risk":
                return f"To diversify your portfolio, consider: {', '.join(top_tickers)}"
            
            elif intent_type == "suggestions":
                return "Want detailed analysis on any of these suggestions?"
            
            elif intent_type == "comparison":
                return f"Want more options to compare? Try: {', '.join(top_tickers)}"
        
        # Fallback: Generic based on intent
        if intent_type == "stock_valuation":
            return "Want me to explain the valuation factors?"
        elif intent_type == "explanation":
            return "Want to see how this impacts your portfolio?"
        elif intent_type == "portfolio_risk":
            return "Want suggestions to optimize your portfolio?"
        else:
            return "What would you like to explore next?"


async def chat_stream(
    db: Session,
    user_id: str,
    query: str,
    base_url: str = "http://localhost:8001"
):
    """
    Stream chat response.
    
    Pure orchestration: Routes to endpoints → Formats response → Returns
    
    Usage:
        async for chunk in chat_stream(db, user_id, query):
            print(chunk)
    """
    agent = FinancialIntelligenceAgent(db, base_url)
    result = await agent.process_query(user_id, query)
    
    # Stream the response
    response_text = result["response"]
    for char in response_text:
        yield char
    
    # Add next action (from recommendation service)
    yield f"\n\n🤖 **Suggested Next**: {result['next_best_action']}"

