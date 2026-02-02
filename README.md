# AI-Driven Stock Valuation Chatbot

This project is a full-stack financial analysis tool that combines **Machine Learning** with a **Conversational AI** interface. The system calculates the intrinsic value of stocks using fundamental and technical data to provide investment classifications.

## 🚀 Features
* **Stock Classification:** Uses a Random Forest model to categorize stocks as *Undervalued*, *Fairly Valued*, or *Overvalued*.
* **Predictive Modeling:** Calculates "Fair Value" estimates based on historical P/E ratios and growth metrics.
* **Technical Indicators:** Integrates SMA-30, SMA-90, and Volatility tracking.
* **REST API:** Powered by FastAPI (in development) to serve model predictions to the Azure Chatbot.

## 🛠️ Technical Stack
* **Language:** Python 3.x
* **Data Source:** Yahoo Finance API (`yfinance`)
* **Machine Learning:** Scikit-Learn (Random Forest Regressor)
* **Backend:** FastAPI (PyCharm environment)
* **Infrastructure:** Git/GitHub for version control

## 📂 Project Structure
* `classification model.ipynb`: Jupyter Notebook containing data preprocessing, feature engineering, and model training.
* `api/`: (In progress) FastAPI implementation for serving predictions.
* `.gitignore`: Configuration to prevent tracking of unnecessary files (like `.ipynb_checkpoints`).

## 📈 Model Methodology
The model utilizes a **Multi-Factor Valuation Score**, justifying its output through:
1.  **Fundamental Ratios:** P/E, P/B, and ROE.
2.  **Momentum Tracking:** Moving average crossovers.
3.  **Explainability:** (Planned) SHAP values to explain *why* a stock is classified a certain way.

---
*Developed as part of a Final Year Project at Atlantic Technological University.*
