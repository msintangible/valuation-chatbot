import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import services.portfolio as portfolio_service


class TestPortfolioWorkflow(unittest.TestCase):
    def setUp(self):
        self._original_run_prediction_shap = portfolio_service.run_prediction_shap

        def fake_run_prediction_shap(ticker: str, model, model_columns):
            mocked = {
                "AAPL": {
                    "ticker": "AAPL",
                    "label": "Undervalued",
                    "confidence": 0.9,
                    "shap_summary": {
                        "top_positive_features": ["Volatility (+0.300)", "Momentum (+0.100)"],
                        "top_negative_features": ["Revenue_Growth (-0.200)"],
                        "summary": "Undervalued driven by volatility and momentum.",
                        "prediction_meaning": "The model sees signs the stock may be priced below its fundamentals.",
                        "feature_impacts": [
                            {"feature": "Volatility", "shap_value": 0.300},
                            {"feature": "Momentum", "shap_value": 0.100},
                            {"feature": "Revenue_Growth", "shap_value": -0.200},
                        ],
                    },
                },
                "TSLA": {
                    "ticker": "TSLA",
                    "label": "Fair Value",
                    "confidence": 0.6,
                    "shap_summary": {
                        "top_positive_features": ["Debt_to_Equity (+0.250)"],
                        "top_negative_features": ["EPS (-0.150)"],
                        "summary": "Fair Value with mixed contributors.",
                        "prediction_meaning": "The model sees the stock as roughly in line with its fundamentals.",
                        "feature_impacts": [
                            {"feature": "Debt_to_Equity", "shap_value": 0.250},
                            {"feature": "EPS", "shap_value": -0.150},
                        ],
                    },
                },
                "NVDA": {
                    "ticker": "NVDA",
                    "label": "Overvalued",
                    "confidence": 0.7,
                    "shap_summary": {
                        "top_positive_features": ["Volatility (+0.200)"],
                        "top_negative_features": ["Operating_Margin (-0.100)"],
                        "summary": "Overvalued primarily due to volatility.",
                        "prediction_meaning": "The model sees signs the stock may be priced above its fundamentals.",
                        "feature_impacts": [
                            {"feature": "Volatility", "shap_value": 0.200},
                            {"feature": "Operating_Margin", "shap_value": -0.100},
                        ],
                    },
                },
            }
            return mocked[ticker]

        portfolio_service.run_prediction_shap = fake_run_prediction_shap

    def tearDown(self):
        portfolio_service.run_prediction_shap = self._original_run_prediction_shap

    def test_portfolio_functions_workflow(self):
        user_id = "1"
        tickers = ["AAPL", "TSLA", "NVDA"]
        weights = [0.5, 0.3, 0.2]

        stocks = portfolio_service.run_portfolio_predictions(
            user_id=user_id,
            tickers=tickers,
            weights=weights,
            model=object(),
            model_columns=["any"],
        )

        self.assertEqual(len(stocks), 3)
        self.assertEqual(stocks[0]["ticker"], "AAPL")
        self.assertEqual(stocks[0]["prediction"], "Undervalued")
        self.assertAlmostEqual(stocks[0]["probability"], 0.9, places=6)
        self.assertAlmostEqual(stocks[0]["weight"], 0.5, places=6)

        score = portfolio_service.compute_portfolio_risk_score(stocks)
        self.assertAlmostEqual(score, 0.4070, places=4)

        risk_classification = portfolio_service.classify_portfolio_risk(score)
        self.assertEqual(risk_classification, "Medium Risk")

        shap_agg = portfolio_service.aggregate_portfolio_shap(stocks)
        self.assertIn("top_positive_risk_factors", shap_agg)
        self.assertIn("top_negative_risk_factors", shap_agg)
        self.assertTrue(any("Volatility" in item for item in shap_agg["top_positive_risk_factors"]))
        self.assertTrue(any("Revenue_Growth" in item for item in shap_agg["top_negative_risk_factors"]))
        self.assertGreater(len(shap_agg.get("portfolio_explanation", [])), 0)
        self.assertGreater(len(shap_agg.get("beginner_takeaway", [])), 0)

    def test_classification_boundaries(self):
        self.assertEqual(portfolio_service.classify_portfolio_risk(0.32), "Low Risk")
        self.assertEqual(portfolio_service.classify_portfolio_risk(0.33), "Medium Risk")
        self.assertEqual(portfolio_service.classify_portfolio_risk(0.65), "Medium Risk")
        self.assertEqual(portfolio_service.classify_portfolio_risk(0.66), "High Risk")


if __name__ == "__main__":
    unittest.main(verbosity=2)

