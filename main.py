import os
import json
import re
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

# -----------------------------
# Load Environment Variables
# -----------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# -----------------------------
# Gemini Client
# -----------------------------
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

def _parse_json_from_text(text: str) -> dict:
    """Extract JSON from model response, handling markdown code blocks."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)

# -----------------------------
# Initialize App
# -----------------------------
app = FastAPI(title="SahaAi - Personal AI CFO")

# -----------------------------
# Financial Analysis Engine
# -----------------------------
def analyze_financial_data(income: float, expenses: float, emi: float):

    savings = income - expenses - emi
    dti = emi / income if income > 0 else 0

    if dti > 0.4:
        risk = "High Risk"
    elif dti > 0.25:
        risk = "Moderate Risk"
    else:
        risk = "Low Risk"

    if savings < 0:
        advice = "You are overspending. Reduce expenses immediately."
    elif savings < 0.2 * income:
        advice = "Increase savings. Try to save at least 20% of income."
    else:
        advice = "Your financial health looks stable."

    return {
        "savings": savings,
        "dti_percent": round(dti * 100, 2),
        "risk_level": risk,
        "advice": advice
    }

# -----------------------------
# Request Models
# -----------------------------
class ChatInput(BaseModel):
    message: str

# -----------------------------
# CHAT ENDPOINT
# -----------------------------
@app.post("/chat")
def chat_with_sahaai(data: ChatInput):

    prompt = f"""
You are a financial assistant.

Extract income, expenses and emi from the following text.
Return ONLY valid JSON.

Text:
{data.message}

Format:
{{
  "income": number,
  "expenses": number,
  "emi": number
}}
"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0),
        )
        structured_data = _parse_json_from_text(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API Error: {str(e)}")

    income = float(structured_data.get("income", 0))
    expenses = float(structured_data.get("expenses", 0))
    emi = float(structured_data.get("emi", 0))

    analysis = analyze_financial_data(income, expenses, emi)

    return {
        "structured_data": structured_data,
        "analysis": analysis
    }

# -----------------------------
# IMAGE ENDPOINT
# -----------------------------
@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    mime = file.content_type or "image/jpeg"
    if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        mime = "image/jpeg"

    prompt = """Look at this image (receipt, bill, or expense document).
1. Briefly describe what you see (extracted text / key details).
2. Extract the total expense amount as a number if visible; otherwise use 0.

Return ONLY valid JSON in this exact format:
{"extracted_text": "your description here", "expense": number}"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
                prompt,
            ],
            config=types.GenerateContentConfig(temperature=0),
        )
        data = _parse_json_from_text(response.text)
        extracted_text = data.get("extracted_text", "")
        expense = data.get("expense", 0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini Vision API Error: {str(e)}")

    return {
        "extracted_text": extracted_text,
        "expense_detected": {"expense": expense},
    }

# -----------------------------
# Health Check
# -----------------------------
@app.get("/health")
def health():
    return {"status": "SahaAi running successfully 🚀"}

# -----------------------------
# UI – serve frontend at /
# -----------------------------
_static_dir = Path(__file__).parent / "static"
_index_html = _static_dir / "index.html"


@app.get("/")
def serve_ui():
    if _index_html.is_file():
        return FileResponse(_index_html)
    return {"message": "SahaAI API. Set up static/index.html for UI."}