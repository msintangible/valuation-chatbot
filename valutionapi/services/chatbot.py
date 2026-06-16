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
from services.query_classifier import (
    QueryCategory,
    QueryClassification,
    METRIC_LEXICON,
    KNOWN_TICKER_UNIVERSE,
    classify_query,
)
from models.models import Prediction

load_dotenv()


def is_general_query(query: str) -> bool:
    """Detect greetings/help/very-short non-financial inputs."""
    normalized = query.strip().lower()
    if not normalized:
        return True

    tokens = re.findall(r"[a-zA-Z0-9']+", normalized)
    if not tokens:
        return True

    greetings = {"hi", "hello", "hey", "yo", "hola"}
    help_terms = {
        "help",
        "help me",
        "what can you do",
        "how does this work",
        "what do you do",
    }
    finance_terms = {
        "stock",
        "stocks",
        "ticker",
        "analyze",
        "analysis",
        "valuation",
        "overvalued",
        "undervalued",
        "portfolio",
        "risk",
        "price",
        "shares",
        "suggest",
        "recommend",
        "compare",
        "explain",
        "metric",
        "metrics",
        "indicator",
        "indicators",
        "ratio",
        "roe",
        "roa",
        "eps",
        "ebitda",
        "p/e",
        "pe",
        "peg",
        "beta",
        "rsi",
        "macd",
        "dividend",
        "yield",
        "cash flow",
        "debt to equity",
        "current ratio",
        "quick ratio",
    }

    if normalized in help_terms:
        return True

    if any(token in greetings for token in tokens) and len(tokens) <= 3:
        return True

    has_ticker_like_text = bool(re.search(r"\b[A-Z]{1,5}\b", query))
    has_finance_term = any(term in normalized for term in finance_terms)

    # Treat very short non-financial messages as general chat.
    if len(tokens) <= 2 and not has_finance_term and not has_ticker_like_text:
        return True

    return False


def _format_invalid_ticker_message(unrecognized: List[str]) -> str:
    """Standardized, transparent message for tickers that failed
    validation — never a silent empty result."""
    joined = ", ".join(unrecognized)
    return f"❌ Invalid tickers detected: {joined}. These are not recognized stock symbols."


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
    
    def __init__(self, db: Session, base_url: str = os.getenv("API_BASE_URL", "https://valuationchatbot-exfsfyf6cta5gpek.germanywestcentral-01.azurewebsites.net")):
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
        0. MANDATORY FIRST STEP: classify_query() decides exactly one of
           TICKER_QUERY / METRIC_EXPLANATION / MIXED_QUERY /
           GENERAL_QUESTION. No tool/API call happens anywhere above this
           line — this is what stops a financial metric (ROE, EPS, P/E,
           ...) from ever reaching a ticker lookup endpoint.
        1. Route based on category.
        2. Call appropriate endpoints based on intent (ticker categories only).
        3. Call recommendation service for personalization.
        4. Format response with LLM.
        5. Use recommendations for next-action.
        """
        print(f"➡️ process_query called with: {query}")
        if is_general_query(query):
            return {
                "response": (
                    "👋 Hey! I can help with stock and portfolio analysis.\n\n"
                    "Try one of these:\n"
                    "- Analyze AAPL\n"
                    "- Why is TSLA overvalued\n"
                    "- Analyze portfolio Growth"
                ),
                "next_best_action": "Ask a financial query to start analysis.",
                "tools_used": [],
                "errors": [],
                "recommendations": {"top_sectors": [], "suggested_tickers": []}
            }

        # ── MANDATORY FIRST STEP — classify before any tool/API call ────
        classification = classify_query(query)
        print(
            f"🔎 Classification: {classification.category} "
            f"tickers={classification.ticker_candidates} metrics={classification.metrics}"
        )

        # Category B: METRIC_EXPLANATION → explanation engine ONLY.
        # Hard rule: NEVER call a market-data API for a metric question.
        if classification.category == QueryCategory.METRIC_EXPLANATION:
            return self._respond_metric_explanation(query, classification)

        # Category D: GENERAL_QUESTION → no structural ticker, no metric
        # term. If the phrasing still looks like a valuation/comparison
        # request, try resolving a company NAME (e.g. "Apple") via the
        # LLM fallback before giving up on a ticker. Otherwise this falls
        # through untouched to the existing portfolio/suggestions/general
        # routing below.
        if classification.category == QueryCategory.GENERAL_QUESTION:
            query_lower = query.lower()
            looks_like_valuation_request = any(
                kw in query_lower
                for kw in ("value", "worth", "price", "overvalued", "undervalued",
                           "fair", "compare", "versus", " vs ", "analyze")
            )
            if looks_like_valuation_request:
                resolved = self._resolve_company_name_tickers(query)
                if resolved:
                    classification = QueryClassification(
                        category=QueryCategory.TICKER_QUERY,
                        raw_query=query,
                        ticker_candidates=resolved,
                        recognized_tickers=[t for t in resolved if t in KNOWN_TICKER_UNIVERSE],
                        unverified_tickers=[t for t in resolved if t not in KNOWN_TICKER_UNIVERSE],
                        metrics=[],
                    )

        # Categories A & C (and GENERAL_QUESTION promoted above) share the
        # ticker pipeline. Tickers always come from `classification` —
        # never re-derived by a second regex — so a metric term can't
        # leak back in here either.
        if classification.category in (QueryCategory.TICKER_QUERY, QueryCategory.MIXED_QUERY):
            return await self._respond_ticker_or_mixed(user_id, query, classification)

        # Category D, no ticker resolved: existing portfolio/suggestions/
        # general LLM routing, with an explicit empty ticker list.
        intent = self._analyze_intent(query, tickers=[])
        return await self._run_intent_pipeline(user_id, query, intent)

    def _respond_metric_explanation(
        self, query: str, classification: QueryClassification
    ) -> Dict[str, Any]:
        """Category B routing: explanation engine ONLY, no tool/API call.

        This is the direct fix for the reported bug:
        "What does ROE tell me?" -> classified METRIC_EXPLANATION ->
        explained via the LLM knowledge layer -> zero ticker API calls.
        """
        response = self._generate_general_finance_response(query, "finance_education")
        example_metric = classification.metrics[0] if classification.metrics else "ROE"
        return {
            "response": response,
            "next_best_action": f"Ask about a ticker to apply this (e.g., 'How is AAPL's {example_metric}?').",
            "tools_used": ["llm_finance_explanation"],
            "errors": [],
            "recommendations": {"top_sectors": [], "suggested_tickers": []},
        }

    async def _respond_ticker_or_mixed(
        self, user_id: str, query: str, classification: QueryClassification
    ) -> Dict[str, Any]:
        """Category A (TICKER_QUERY) & C (MIXED_QUERY) routing.

        - Ticker part -> financial data API (existing tool pipeline).
        - Metric part (MIXED_QUERY only) -> explanation engine.
        - Results combined into one response.

        Also enforces the hard rule "NEVER return empty ticker arrays
        without explaining why validation failed": any ticker the
        backend's live validator rejects (404) is surfaced explicitly via
        the standardized "Invalid tickers detected" message instead of a
        generic/empty failure.
        """
        tickers = classification.ticker_candidates
        intent = self._analyze_intent(query, tickers=tickers)

        ticker_required_intents = ["stock_valuation", "comparison"]
        if intent["type"] in ticker_required_intents and not intent["entities"].get("tickers"):
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
                "errors": [],
                "recommendations": {"top_sectors": [], "suggested_tickers": []}
            }

        result = await self._run_intent_pipeline(user_id, query, intent)

        # Transparently surface backend-rejected tickers (the hard rule:
        # never an unexplained empty result).
        invalid_tickers = self._extract_invalid_tickers(result.get("errors", []))
        if invalid_tickers:
            result["response"] = _format_invalid_ticker_message(invalid_tickers) + "\n\n" + result["response"]

        # Category C: append the metric explanation alongside the
        # ticker data instead of dropping it.
        if classification.category == QueryCategory.MIXED_QUERY and classification.metrics:
            explanation = self._generate_general_finance_response(query, "finance_education")
            result["response"] = result["response"] + "\n\n---\n\n" + explanation
            result["tools_used"] = result.get("tools_used", []) + ["llm_finance_explanation"]

        return result

    def _extract_invalid_tickers(self, errors: List[Dict[str, Any]]) -> List[str]:
        """Pull out tickers the backend's live validator rejected
        (HTTP 404 = "not a recognized stock symbol"), de-duplicated and
        order-preserving."""
        invalid: List[str] = []
        seen = set()
        for err in errors:
            ticker = err.get("ticker")
            if err.get("http_status") == 404 and ticker and ticker not in seen:
                seen.add(ticker)
                invalid.append(ticker)
        return invalid

    async def _run_intent_pipeline(
        self, user_id: str, query: str, intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Steps 2-5 of the original orchestration flow: execute tools for
        a resolved intent, fetch recommendations, format the response.
        Shared by every routing branch that ends up calling a tool."""
        tickers = intent.get("entities", {}).get("tickers", [])

        if intent["type"] in ["finance_education", "general"] and not tickers:
            response = self._generate_general_finance_response(query, intent["type"])
            next_action = (
                "Ask about a ticker to apply this (e.g., 'How is AAPL's ROE?')."
                if intent["type"] == "finance_education"
                else "Ask a finance metric question or request a stock valuation (e.g., Analyze AAPL)."
            )
            return {
                "response": response,
                "next_best_action": next_action,
                "tools_used": ["llm_finance_general"],
                "errors": [],
                "recommendations": {"top_sectors": [], "suggested_tickers": []}
            }

        # Step 2: Execute endpoints based on intent
        tool_results = await self._execute_tools(user_id, query, intent)
        tool_errors = self._collect_tool_errors(tool_results)

        # Step 3: Get personalized recommendations from backend service
        should_get_recommendations = (
                intent["type"] in ["suggestions", "portfolio_suggestions"]
                or (intent["type"] == "general" and not tickers)
        )

        if should_get_recommendations:
            recommendations = await self._get_recommendations(user_id, intent, tool_results)
        else:
            recommendations = {"top_sectors": [], "suggestions": []}

        print(f"📊 DEBUG: Final recommendations before response generation:")
        print(f"   Type: {type(recommendations)}")
        print(f"   Keys: {recommendations.keys() if isinstance(recommendations, dict) else 'N/A'}")
        print(f"   top_sectors: {recommendations.get('top_sectors', [])}")
        print(f"   suggestions: {len(recommendations.get('suggestions', []))} items")

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
            "errors": tool_errors,
            "recommendations": {
                "top_sectors": recommendations.get("top_sectors", []),
                "suggested_tickers": [s.get("ticker") for s in recommendations.get("suggestions", [])[:3]]
            }
        }

    def _collect_tool_errors(self, tool_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []
        for result in tool_results:
            data = result.get("data", {})
            if isinstance(data, dict) and data.get("status") == "error":
                item = dict(data)
                item.setdefault("tool", result.get("tool"))
                errors.append(item)
            elif "error" in result:
                errors.append(
                    {
                        "status": "error",
                        "tool": result.get("tool"),
                        "message": result.get("error", "Tool call failed"),
                        "ticker": result.get("ticker"),
                    }
                )
        return errors
    
    def _analyze_intent(self, query: str, tickers: List[str]) -> Dict[str, Any]:
        """
        Analyze user query to determine WHICH TOOL to call, given an
        already-classified, already-validated ticker list.

        NOTE: this method no longer extracts tickers itself. Ticker vs.
        metric classification is owned exclusively by
        services.query_classifier.classify_query() (the mandatory first
        step in process_query()), so there is exactly one place a token
        can be decided to be a ticker — eliminating the class of bug
        where a financial metric (ROE, EPS, ...) was independently
        re-detected as a ticker by a second, competing regex here.

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

        if tickers:
            intent["entities"]["tickers"] = tickers

        portfolio_name = self._extract_portfolio_name(query)
        if portfolio_name:
            intent["entities"]["portfolio_name"] = portfolio_name

        # Detect suggestion keywords FIRST (higher priority than portfolio risk)
        suggestion_keywords = ["suggest", "recommend", "what should i", "ideas", "options", "optimize"]
        portfolio_keywords = ["portfolio", "holdings"]
        
        if any(kw in query_lower for kw in suggestion_keywords):
            # Check if user wants portfolio-specific suggestions
            if any(kw in query_lower for kw in portfolio_keywords):
                intent["type"] = "portfolio_suggestions"
                intent["confidence"] = 0.95
                return intent
            else:
                intent["type"] = "suggestions"
                intent["confidence"] = 0.85
                return intent
        
        # Detect explanation keywords
        explanation_keywords = ["why", "explain", "how come", "reason", "because", "shap"]
        if any(kw in query_lower for kw in explanation_keywords):
            intent["needs_explanation"] = True
            if tickers:
                intent["type"] = "explanation"
                intent["confidence"] = 0.95
                return intent
            intent["type"] = "explanation"
            intent["confidence"] = 0.8
            return intent
        
        # Detect portfolio risk keywords (AFTER suggestion check)
        portfolio_risk_keywords = ["portfolio risk", "analyze portfolio", "portfolio analysis", "how is my portfolio"]
        if any(kw in query_lower for kw in portfolio_risk_keywords):
            intent["type"] = "portfolio_risk"
            intent["confidence"] = 0.9
            intent["needs_risk_analysis"] = True
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

        # No tickers and no recognized keyword pattern. Metric-explanation
        # queries never reach this point — process_query() routes
        # METRIC_EXPLANATION / MIXED_QUERY straight to the explanation
        # engine before _analyze_intent is ever called. This is the
        # general/portfolio-advice catch-all.
        intent["type"] = "general"
        intent["confidence"] = 0.5
        return intent

    def _generate_general_finance_response(self, query: str, intent_type: str) -> str:
        """Handle non-valuation finance questions with LLM knowledge."""
        prompt = f"""You are a finance assistant for a stock valuation app.

User question: {query}
Detected intent: {intent_type}

Rules:
1. If the question is about financial metrics/indicators, explain clearly:
   - What it means
   - Why it matters
   - How to interpret high vs low values
   - One practical caution
2. Keep answer concise and practical.
3. Do not fabricate real-time market values or claim live data access.
4. If user asks something outside finance, politely steer back to finance and valuation help.
5. Do not provide personalized investment advice.
"""
        try:
            response = self.llm_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as e:
            print(f"WARNING: General finance LLM call failed: {e}")

        if intent_type == "finance_education":
            return (
                "A financial metric helps measure company performance or valuation. "
                "Tell me a specific one (e.g., ROE, EPS, P/E, EBITDA, Beta, RSI), "
                "and I'll explain how to interpret it."
            )
        return (
            "I can answer general finance questions (metrics and indicators) and run stock valuations. "
            "Try: 'What does P/E ratio mean?' or 'Analyze AAPL'."
        )
    
    def _resolve_company_name_tickers(self, query: str) -> List[str]:
        """
        Secondary fallback for GENERAL_QUESTION inputs that name a company
        instead of a ticker symbol (e.g. "What's Apple worth?"). Only
        called by process_query() when classify_query() found neither a
        structural ticker nor a metric term, AND the query otherwise looks
        like a valuation/comparison request.

        This is NOT part of the mandatory classification step — it never
        runs for METRIC_EXPLANATION/MIXED_QUERY inputs, and its output is
        re-filtered through the same metric/stopword exclusion rules as
        every other ticker source, so an LLM hallucination can't smuggle
        a metric abbreviation back in as a "ticker".
        """
        from services.query_classifier import METRIC_LEXICON, TICKER_STOPWORDS

        llm_tickers = self._llm_extract_tickers(query)
        return [t for t in llm_tickers if t not in METRIC_LEXICON and t not in TICKER_STOPWORDS]

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

    def _get_latest_user_ticker(self, user_id: str) -> str:
        """Fallback ticker from latest stored prediction for conversational follow-ups."""
        row = (
            self.db.query(Prediction)
            .filter(Prediction.user_id == user_id)
            .order_by(Prediction.predicted_at.desc())
            .first()
        )
        return row.ticker if row and row.ticker else ""
    
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
        elif intent_type == "explanation":
            ticker = tickers[0] if tickers else self._get_latest_user_ticker(user_id)
            if not ticker:
                results.append(
                    {
                        "tool": "shap_explain",
                        "data": {
                            "status": "error",
                            "message": "No previous stock analysis found. Analyze a stock first.",
                            "ticker": None,
                        },
                    }
                )
                return results
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
                
                # Analyze requested portfolio if specified; otherwise fallback to first.
                if isinstance(portfolios_data, list) and len(portfolios_data) > 0:
                    requested_name = intent.get("entities", {}).get("portfolio_name", "").strip().lower()
                    selected_portfolio_name = None

                    if requested_name:
                        for portfolio in portfolios_data:
                            candidate_name = str(portfolio.get("name", "")).strip()
                            if candidate_name.lower() == requested_name:
                                selected_portfolio_name = candidate_name
                                break

                    if not selected_portfolio_name:
                        selected_portfolio_name = portfolios_data[0].get("name")

                    if selected_portfolio_name:
                        risk_analysis = await self.tool_executor.call_tool(
                            "portfolio_risk_from_saved",
                            {"user_id": user_id, "name": selected_portfolio_name}
                        )
                        results.append({"tool": "portfolio_risk", "data": risk_analysis})
            except Exception as e:
                print(f"Error calling portfolio_risk: {e}")
                results.append({"tool": "portfolio_risk", "error": str(e)})
        
        # Rule 4: Suggestions (delegates to recommendation service)
        # NOTE: Suggestions are handled in _get_recommendations() to avoid duplicate calls
        # elif intent_type == "suggestions":
        #     try:
        #         suggestions = await self.tool_executor.call_user_suggestions(user_id, top_n=5)
        #         results.append({"tool": "user_suggestions", "data": suggestions})
        #     except Exception as e:
        #         print(f"Error calling suggestions: {e}")
        #         results.append({"tool": "user_suggestions", "error": str(e)})
        
        # Rule 4b: Portfolio-specific suggestions
        # elif intent_type == "portfolio_suggestions":
        #     try:
        #         # Get user's portfolios first
        #         portfolios = await self.tool_executor.call_tool("list_portfolios", {"user_id": user_id})
        #         if isinstance(portfolios, list) and len(portfolios) > 0:
        #             portfolio_name = portfolios[0].get("name", "default")
        #             suggestions = await self.tool_executor.call_portfolio_suggestions(
        #                 user_id, portfolio_name, top_n=5
        #             )
        #             results.append({"tool": "portfolio_suggestions", "data": suggestions})
        #     except Exception as e:
        #         print(f"Error calling portfolio suggestions: {e}")
        #         results.append({"tool": "portfolio_suggestions", "error": str(e)})
        
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
        
        # Handle regular user suggestions
        if intent_type == "suggestions":
            try:
                # Check if we already have suggestions from tool_results (to avoid duplicate call)
                existing_suggestion = next(
                    (r for r in tool_results if r.get("tool") == "user_suggestions"),
                    None
                )
                
                if existing_suggestion and "data" in existing_suggestion:
                    print("✓ Using cached suggestion results from tool execution")
                    return existing_suggestion["data"]
                
                # Otherwise, call the suggestions endpoint
                print("✓ Calling user suggestions endpoint")
                recommendations = await self.tool_executor.call_user_suggestions(user_id, top_n=5)
                
                print(f"📊 DEBUG: User recommendations response:")
                print(f"   Type: {type(recommendations)}")
                print(f"   Keys: {recommendations.keys() if isinstance(recommendations, dict) else 'N/A'}")
                print(f"   Data: {recommendations}")
                
                if "error" in recommendations:
                    return {"top_sectors": [], "suggestions": []}
                
                # Normalize response structure (user endpoint uses top_sector, not top_sectors)
                normalized = {
                    "top_sectors": [recommendations.get("top_sector")] if recommendations.get("top_sector") else [],
                    "suggestions": recommendations.get("suggestions", [])
                }
                
                print(f"📊 DEBUG: Normalized recommendations:")
                print(f"   top_sectors: {normalized['top_sectors']}")
                print(f"   suggestions count: {len(normalized['suggestions'])}")
                
                return normalized
                
            except Exception as e:
                print(f"Error getting recommendations: {e}")
                return {"top_sectors": [], "suggestions": []}
        
        # Handle portfolio-specific suggestions
        elif intent_type == "portfolio_suggestions":
            try:
                # Check if we already have portfolio suggestions from tool_results
                existing_suggestion = next(
                    (r for r in tool_results if r.get("tool") == "portfolio_suggestions"),
                    None
                )
                
                if existing_suggestion and "data" in existing_suggestion:
                    print("✓ Using cached portfolio suggestion results from tool execution")
                    return existing_suggestion["data"]
                
                # Otherwise, fetch user's portfolios and call portfolio suggestions
                print("✓ Calling portfolio suggestions endpoint")
                portfolios = await self.tool_executor.call_tool("list_portfolios", {"user_id": user_id})
                
                if isinstance(portfolios, list) and len(portfolios) > 0:
                    portfolio_name = portfolios[0].get("name", "default")
                    recommendations = await self.tool_executor.call_portfolio_suggestions(
                        user_id, portfolio_name, top_n=5
                    )
                    
                    print(f"📊 DEBUG: Portfolio recommendations response:")
                    print(f"   Type: {type(recommendations)}")
                    print(f"   Keys: {recommendations.keys() if isinstance(recommendations, dict) else 'N/A'}")
                    print(f"   Data: {recommendations}")
                    
                    if "error" in recommendations:
                        return {"top_sectors": [], "suggestions": []}
                    
                    # Normalize response structure (portfolio endpoint uses top_sectors, not top_sector)
                    normalized = {
                        "top_sectors": recommendations.get("top_sectors", []),
                        "suggestions": recommendations.get("suggestions", [])
                    }
                    
                    print(f"📊 DEBUG: Normalized recommendations:")
                    print(f"   top_sectors: {normalized['top_sectors']}")
                    print(f"   suggestions count: {len(normalized['suggestions'])}")
                    
                    return normalized
                else:
                    # No portfolios found, fallback to regular suggestions
                    print("  ⚠️ No portfolios found, falling back to user suggestions")
                    return await self.tool_executor.call_user_suggestions(user_id, top_n=5)
                    
            except Exception as e:
                print(f"Error getting portfolio recommendations: {e}")
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

        # Handle both top_sector (singular) and top_sectors (plural) for backwards compatibility
        top_sectors = recommendations.get("top_sectors", [])
        suggestions = recommendations.get("suggestions", [])
        
        print(f"📊 DEBUG: Building LLM prompt with:")
        print(f"   top_sectors: {top_sectors}")
        print(f"   suggestions: {len(suggestions)} items")
        print(f"   First 3 suggestions: {suggestions[:3]}")
        
        # Extract suggestion tickers for display
        suggested_tickers = [s.get("ticker", "") for s in suggestions[:3] if s.get("ticker")]
        
        # Format sectors as comma-separated string
        sectors_str = ", ".join(top_sectors) if top_sectors else "None"
        
        prompt = f"""You are a financial intelligence AI assistant that formats data from backend services.

USER QUERY: {query}

TOOL RESULTS (from backend endpoints):
{context}

PERSONALIZED RECOMMENDATIONS (from recommendation service):
- Top sectors of interest: {sectors_str}
- Suggested tickers: {suggested_tickers}
- Full suggestion details: {json.dumps(suggestions[:5], indent=2) if suggestions else "No suggestions available"}

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
- Sectors you're interested in: {sectors_str}
- Recommended tickers to explore: {suggested_tickers}
{f"- Details: Based on your {sectors_str} interest, consider {', '.join(suggested_tickers[:3])}" if suggested_tickers else ""}

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
                if isinstance(data, dict) and data.get("status") == "error":
                    ticker = data.get("ticker") or "this stock"
                    response_parts.append(
                        f"⚠️ Unable to retrieve data for {ticker}. This may be due to:\n"
                        "- Invalid ticker\n"
                        "- Temporary API issue\n"
                        "- Missing financial data\n\n"
                        "Try again or use a different stock."
                    )
                    continue
                # Endpoint returns: label, confidence, current_price, graham_value
                label = data.get("label", "N/A")
                confidence = data.get("confidence")
                price = data.get("current_price")
                graham_value = data.get("graham_value")
                confidence_text = f"{float(confidence):.1%}" if isinstance(confidence, (int, float)) else "N/A"
                price_text = f"${float(price):.2f}" if isinstance(price, (int, float)) else "Unavailable"
                graham_text = f"${float(graham_value):.2f}" if isinstance(graham_value, (int, float)) else "Unavailable"
                response_parts.append(
                    f"📊 **Valuation**: {label} (Confidence: {confidence_text})\n"
                    f"Current Price: {price_text} | Graham Value: {graham_text}"
                )
            
            elif tool_name == "shap_explain":
                response_parts.append("🔍 **Explanation Available**\n")
                if isinstance(data, dict) and data.get("status") == "error":
                    response_parts.append(data.get("message", "Detailed explanation is currently unavailable."))
                elif "beginner_explanation" in data:
                    response_parts.append(data["beginner_explanation"])
                elif "shap_summary" in data and isinstance(data.get("shap_summary"), dict):
                    response_parts.append(data["shap_summary"].get("summary", "Detailed SHAP summary not available."))
        
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

    def _extract_portfolio_name(self, query: str) -> str:
        """Extract portfolio name from natural-language portfolio analysis prompts."""
        normalized_query = query.strip()
        patterns = [
            r"analyze\s+(?:my\s+)?portfolio\s+(.+)$",
            r"portfolio\s+analysis\s+for\s+(.+)$",
            r"how\s+is\s+(?:my\s+)?portfolio\s+(.+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized_query, flags=re.IGNORECASE)
            if match:
                name = match.group(1).strip().strip("\"'?.!,")
                if name:
                    return name
        return ""


async def chat_stream(
    db: Session,
    user_id: str,
    query: str,
    base_url: str = os.getenv("API_BASE_URL", "https://valuationchatbot-exfsfyf6cta5gpek.germanywestcentral-01.azurewebsites.net")
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

