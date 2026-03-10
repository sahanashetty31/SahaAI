"""
SahaAI CFO API - Separate FastAPI app with receipt analysis, statement explainer,
fraud detection, goal planner, and financial score.

Run:  uvicorn cfo_api:app --reload --port 8001
Docs: http://127.0.0.1:8001/docs
"""
import json
import os
import re
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Keys we treat as "recommendations" when parsing LLM JSON
REC_KEYS = [
    "improvement_suggestions", "improvement_plan", "prevention_tips",
    "recommended_action", "top_improvements", "30_day_plan", "monthly_action_plan",
    "habits_to_improve", "financial_observations", "key_weaknesses",
    "manipulation_tactics", "financial_gaps", "investment_strategy",
    "score_explanation", "reasons", "summary_advice",
]


def _extract_json(text: str) -> str | None:
    """Get JSON string from LLM output (handles markdown code blocks and extra text)."""
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    # Try ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    # Try raw JSON object
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


def parse_analysis_and_recommendations(raw: str) -> tuple[str, str]:
    """Parse LLM response; return (result_text, recommendations_text)."""
    rec_parts = []
    result_text = raw or ""
    json_str = _extract_json(raw)
    if json_str:
        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, dict):
                return result_text, ""
            for key in REC_KEYS:
                if key not in parsed or parsed[key] is None:
                    continue
                val = parsed[key]
                label = key.replace("_", " ").title()
                if isinstance(val, list):
                    rec_parts.append(
                        label + ":\n" + "\n".join(f"{i+1}. {v}" if isinstance(v, str) else f"{i+1}. {json.dumps(v)}" for i, v in enumerate(val))
                    )
                else:
                    rec_parts.append(f"{label}: {val}")
            if rec_parts:
                result_obj = {k: v for k, v in parsed.items() if k not in REC_KEYS}
                result_text = json.dumps(result_obj, indent=2) if result_obj else result_text
        except (json.JSONDecodeError, TypeError):
            pass
    return result_text, "\n\n".join(rec_parts) if rec_parts else ""

# ------------------------
# Setup (google.genai SDK)
# ------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not set in .env")

client = genai.Client(api_key=api_key)
MODEL = "gemini-2.5-flash"

app = FastAPI(title="SahaAi - AI CFO")

# ------------------------
# Utility: Financial Score
# ------------------------
def calculate_financial_score(income, expenses, emi):

    savings = income - expenses - emi
    savings_ratio = savings / income if income else 0
    dti = emi / income if income else 0

    score = 100

    if savings_ratio < 0.1:
        score -= 30
    elif savings_ratio < 0.2:
        score -= 15

    if dti > 0.4:
        score -= 25
    elif dti > 0.3:
        score -= 15

    if savings < 0:
        score -= 20

    score = max(score, 0)

    return {
        "score": score,
        "savings": savings,
        "dti_percent": round(dti * 100, 2)
    }

# ------------------------
# 1️⃣ Multimodal Receipt Analyzer
# ------------------------
@app.post("/analyze-receipt")
async def analyze_receipt(file: UploadFile = File(...)):

    image = await file.read()
    mime = file.content_type or "image/jpeg"

    prompt = """
    Analyze this receipt image. Return ONLY valid JSON with these exact keys:
    - merchant (string)
    - total_amount (number)
    - category (one of: Food, Travel, Utilities, Shopping, EMI, Other)
    - payment_method (string if visible, else null)
    - recommended_action (string: 1–2 short tips to save or track this expense better)
    """
    if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        mime = "image/jpeg"

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image, mime_type=mime),
            prompt,
        ],
        config=types.GenerateContentConfig(temperature=0),
    )
    result_text, rec_text = parse_analysis_and_recommendations(response.text or "")
    return {"analysis": result_text, "recommendations": rec_text}

# ------------------------
# 2️⃣ Bank Statement Explainer
# ------------------------
class StatementInput(BaseModel):
    statement_text: str

@app.post("/explain-statement")
def explain_statement(data: StatementInput):

    prompt = f"""
    Analyze this bank statement text. Return ONLY valid JSON with these keys:
    - total_income (number)
    - total_expense (number)
    - largest_expense_category (string)
    - risk_indicator (string: Low/Medium/High and brief reason)
    - summary_advice (string)
    - improvement_suggestions (array of 2–4 short strings: specific tips to improve finances)
    
    Text:
    {data.statement_text}
    """

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0),
    )
    result_text, rec_text = parse_analysis_and_recommendations(response.text or "")
    return {"analysis": result_text, "recommendations": rec_text}

# ------------------------
# 3️⃣ Fraud Detector
# ------------------------
class FraudInput(BaseModel):
    message: str

@app.post("/detect-fraud")
def detect_fraud(data: FraudInput):

    prompt = f"""
    Analyze the following message for financial scam. Return ONLY valid JSON with these keys:
    - risk_level (string: Low, Medium, or High)
    - reasons (string or array of strings)
    - recommended_action (string: what the user should do)
    - prevention_tips (array of 2–3 short strings: how to avoid such scams)
    
    Message:
    {data.message}
    """

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0),
    )
    result_text, rec_text = parse_analysis_and_recommendations(response.text or "")
    return {"analysis": result_text, "recommendations": rec_text}

# ------------------------
# 4️⃣ Goal Planner
# ------------------------
class GoalInput(BaseModel):
    income: float
    expenses: float
    emi: float
    goal_amount: float
    years: int

@app.post("/goal-planner")
def goal_planner(data: GoalInput):

    savings = data.income - data.expenses - data.emi
    months = data.years * 12

    if savings <= 0:
        return {"error": "No savings available for planning."}

    required_monthly_saving = data.goal_amount / months

    prompt = f"""
    User earns {data.income} per month, saves {savings}/month. Goal: {data.goal_amount} in {data.years} years. Required monthly saving: {required_monthly_saving}.
    Return ONLY valid JSON with these keys:
    - achievable (boolean)
    - summary (string: one line)
    - adjustment_needed (string, if any)
    - investment_risk (string: Low/Moderate/High)
    - monthly_action_plan (array of 3–5 short strings: concrete steps to reach the goal)
    """

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0),
    )
    result_text, rec_text = parse_analysis_and_recommendations(response.text or "")
    return {
        "required_monthly_saving": required_monthly_saving,
        "analysis": result_text,
        "recommendations": rec_text,
    }

# ------------------------
# 5️⃣ Financial Health Score
# ------------------------
class ScoreInput(BaseModel):
    income: float
    expenses: float
    emi: float

@app.post("/financial-score")
def financial_score(data: ScoreInput):

    result = calculate_financial_score(
        data.income,
        data.expenses,
        data.emi
    )

    prompt = f"""
    User financial snapshot: income ₹{data.income}/month, expenses ₹{data.expenses}, EMI ₹{data.emi}.
    Score: {result['score']}/100, savings ₹{result['savings']}, DTI {result['dti_percent']}%.
    Return ONLY valid JSON with these keys:
    - score_explanation (string: 1–2 sentences on what the score means)
    - top_improvements (array of 3–4 short strings: specific actions to improve score)
    - habits_to_improve (array of 2–3 short strings, optional)
    """
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0),
        )
        _result_text, rec_text = parse_analysis_and_recommendations(response.text or "")
        result["coaching"] = _result_text
        result["recommendations"] = rec_text
    except Exception:
        result["coaching"] = None
        result["recommendations"] = ""

    return result

# ------------------------
# Health & Root
# ------------------------
@app.get("/")
def root():
    return {"app": "SahaAi AI CFO", "docs": "/docs", "health": "/health"}

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.get("/health")
def health():
    return {"status": "AI CFO Running 🚀"}
