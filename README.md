# 🚀 **SahaAI**  
**Multimodal AI-powered personal CFO** — turns everyday financial data into intelligent, risk-aware decisions.

A smart assistant designed to help you manage, analyze, and make better decisions with your financial data using AI.

---

## 💡 What is SahaAI?

**SahaAI** is an AI-driven personal financial assistant that processes multimodal financial inputs to provide insights, actionable recommendations, and risk awareness. Whether you’re tracking expenses, evaluating investment behavior, or simply exploring spending patterns, SahaAI simplifies financial decision-making with intelligent automation.

**Core goals:**
- Analyze financial data using AI
- Provide risk-aware suggestions
- Turn raw data into meaningful insights

---

## 📦 Features

✅ **Receipt analysis** — Upload receipt images; get merchant, amount, category, payment method  
✅ **Statement explainer** — Paste bank/statement text for plain-language explanations  
✅ **Fraud detection** — Get risk assessment and red flags on transaction text  
✅ **Goal planner** — Describe a financial goal; get a step-by-step plan  
✅ **Financial score** — Income, expenses, EMI → savings ratio and DTI-based score  
✅ **Web dashboard** — Single-page UI at `/` with all tools  
✅ **REST API** — All features available under `/api` for integration

---

## 🧠 Technologies

- **Backend:** Python 3.10+, FastAPI, Google Gemini (genai)
- **Frontend:** Vanilla HTML/CSS/JS (Plus Jakarta Sans), served from `static_cfo/`
- **Dependencies:** See `requirements.txt` (fastapi, uvicorn, python-dotenv, python-multipart, google-genai, edge-tts, requests)

---

## 🛠 Setup & Installation

### 1. Clone this repository
```bash
git clone https://github.com/your-username/SahaAI.git
cd SahaAI
```

### 2. Create a virtual environment and install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment variables
Create a `.env` file in the project root with your Google Gemini API key:
```bash
echo "GEMINI_API_KEY=your_api_key_here" > .env
```
Get an API key from [Google AI Studio](https://aistudio.google.com/apikey).

---

## ▶️ Run the app

Start the server (with hot reload):
```bash
uvicorn main_cfo:app --reload --port 8001
```

Then open in your browser:
- **Dashboard:** http://127.0.0.1:8001/
- **API docs:** http://127.0.0.1:8001/api/docs
- **Health check:** http://127.0.0.1:8001/api/health

---

## 📡 API overview

The CFO API is mounted at `/api`. Main endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analyze-receipt` | Upload receipt image (multipart); returns JSON analysis |
| `POST` | `/api/explain-statement` | Body: `{"statement_text": "..."}` — plain-language explanation |
| `POST` | `/api/detect-fraud` | Body: `{"transaction_text": "..."}` — fraud risk and red flags |
| `POST` | `/api/goal-planner` | Body: `{"goal_description": "..."}` — step-by-step plan |
| `POST` | `/api/financial-score` | Body: `{"income", "expenses", "emi"}` — score, savings, DTI |
| `GET`  | `/api/health` | Service health check |

---

## 📁 Project structure

```
SahaAI/
├── main_cfo.py       # FastAPI app: mounts API at /api, serves UI at /
├── cfo_api.py        # CFO API (receipt, statement, fraud, goals, score)
├── static_cfo/
│   └── index.html    # Dashboard UI
├── requirements.txt
├── .env              # GEMINI_API_KEY (create locally, do not commit)
└── README.md
```

---

## 📄 License

Use and extend as you like. Replace `your-username` in the clone URL with your GitHub username or org.
