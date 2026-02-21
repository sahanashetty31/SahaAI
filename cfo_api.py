"""
SahaAI CFO API - Separate FastAPI app with receipt analysis, statement explainer,
fraud detection, goal planner, and financial score.

Run:  uvicorn cfo_api:app --reload --port 8001
Docs: http://127.0.0.1:8001/docs
"""
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

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
    Analyze this receipt image.
    Extract:
    - Merchant name
    - Total amount
    - Category (Food, Travel, Utilities, Shopping, EMI, Other)
    - Payment method if visible
    Return ONLY valid JSON.
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
    return {"analysis": response.text}

# ------------------------
# 1b️⃣ Salary Slip / Form 16 Analyzer
# ------------------------
SALARY_DOC_MIMES = ("image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf")


@app.post("/analyze-salary-document")
async def analyze_salary_document(file: UploadFile = File(...)):
    """
    Upload a salary slip or Form 16 (image or PDF).
    Extracts key fields and returns structured JSON.
    """
    raw = await file.read()
    mime = (file.content_type or "").strip().lower()
    if mime not in SALARY_DOC_MIMES:
        mime = "image/jpeg"

    prompt = """
    This document is either a Salary Slip (payslip) or Form 16 (Indian tax certificate).

    First identify which type it is: "salary_slip" or "form_16".

    Then extract the following as applicable:

    For SALARY SLIP:
    - employer_name, employee_name, month, year
    - gross_salary, basic_salary, hra, special_allowance (if visible)
    - deductions: pf, professional_tax, income_tax_tds, other_deductions (as numbers)
    - net_salary
    - payment_date or similar if visible

    For FORM 16:
    - document_type: "Part A" or "Part B" or "Both" if visible
    - employer_name, employee_name, pan_employee, pan_employer (if visible)
    - assessment_year, period_from, period_to
    - gross_salary, deductions_80c, deductions_80d, other_deductions (if visible)
    - total_income, tax_deducted_tds, tax_payable (if visible)
    - any other key figures in the form

    Use null for any field not found. Return ONLY valid JSON with keys as above (snake_case).
    Do not include markdown or code fences.
    """

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=raw, mime_type=mime),
            prompt,
        ],
        config=types.GenerateContentConfig(temperature=0),
    )
    return {"analysis": response.text}

# ------------------------
# 2️⃣ Bank Statement Explainer
# ------------------------
class StatementInput(BaseModel):
    statement_text: str

@app.post("/explain-statement")
def explain_statement(data: StatementInput):

    prompt = f"""
    Analyze this bank statement text.
    Provide:
    - Total income
    - Total expense
    - Largest expense category
    - Risk indicator
    - Summary advice
    Return JSON format.
    
    Text:
    {data.statement_text}
    """

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0),
    )
    return {"analysis": response.text}

# ------------------------
# 3️⃣ Fraud Detector
# ------------------------
class FraudInput(BaseModel):
    message: str

@app.post("/detect-fraud")
def detect_fraud(data: FraudInput):

    prompt = f"""
    Analyze the following message.
    Determine if it is likely a financial scam.
    Provide:
    - Risk Level (Low, Medium, High)
    - Reasons
    - Recommended action
    Return JSON.
    
    Message:
    {data.message}
    """

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0),
    )
    return {"analysis": response.text}

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
    User earns {data.income} per month.
    Monthly savings: {savings}.
    Goal: {data.goal_amount} in {data.years} years.
    Required monthly saving: {required_monthly_saving}.
    
    Suggest:
    - Is goal achievable?
    - Adjustment needed?
    - Investment suggestion (Low/Moderate/High risk)
    Return JSON.
    """

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0),
    )
    return {
        "required_monthly_saving": required_monthly_saving,
        "analysis": response.text
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
