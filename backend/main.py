import uuid
import json
import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from pathlib import Path
from datetime import datetime
import sqlite3

from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from backend.feedback import init_db, insert_feedback, get_all_feedback, get_sentiment_summary, get_monthly_feedback_counts

init_db()

# IBM WatsonX setup
ibm_creds = {
    "apikey": "ff_M1r6h3R6G794iN6gTqkctmvbsUpE2mOriPGeOjkUT",
    "url": "https://us-south.ml.cloud.ibm.com"
}

generate_params = {
    GenParams.DECODING_METHOD: DecodingMethods.SAMPLE,
    GenParams.MAX_NEW_TOKENS: 10,
    GenParams.TEMPERATURE: 0.5,
    GenParams.TOP_P: 1.0
}

sentiment_model = ModelInference(
    model_id="ibm/granite-13b-instruct-v2",
    credentials=ibm_creds,
    project_id="681ba72f-98cd-445b-9e00-28eeb87fdb77",
    params=generate_params
)

def analyze_sentiment(text):
    prompt = f"""
    Analyze the sentiment of this review and answer "positive", "negative", or "neutral":
    "{text}"
    """
    response = sentiment_model.generate(prompt=prompt, params=generate_params)
    return response["results"][0]["generated_text"].strip().lower()

# Paths for frontend
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# Init app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend assets
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Serve index.html
@app.get("/")
def get_index():
    return FileResponse(FRONTEND_DIR / "index.html")

# Session file setup
SESSION_FILE = "backend/chat_sessions.json"
if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE, "r") as f:
        chat_sessions = json.load(f)
else:
    chat_sessions = {}

def save_sessions():
    with open(SESSION_FILE, "w") as f:
        json.dump(chat_sessions, f, indent=4)

# Load IBM Granite model
model_id = "ibm-granite/granite-3.3-2b-instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
granite_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer, trust_remote_code=True)

# Create session
@app.get("/new-session")
def start_new_session():
    session_id = str(uuid.uuid4())
    chat_sessions[session_id] = []
    save_sessions()
    return {"session_id": session_id}

# Chat with context
@app.post("/chat/{session_id}")
def chat(session_id: str, request: Request):
    import asyncio
    async def get_prompt():
        data = await request.json()
        return data.get("prompt")
    prompt = asyncio.run(get_prompt())

    if session_id not in chat_sessions:
        return JSONResponse(content={"error": "Invalid session ID"}, status_code=404)

    history = "\n".join([f"{m['role']}: {m['message']}" for m in chat_sessions[session_id]])
    full_prompt = history + f"""
        You are a knowledgeable AI assistant helping citizens understand government services and policies.

        Respond to the user in clear, well-structured **Markdown format** with:
        - Headings for schemes or topics
        - Bullet points for key steps, features, or actions
        - Examples if possible

        User: {prompt}
        AI:"""

    response = granite_pipeline(full_prompt, max_new_tokens=200)
    answer = response[0]['generated_text'].split("AI:")[-1].strip()

    chat_sessions[session_id].append({"role": "User", "message": prompt})
    chat_sessions[session_id].append({"role": "AI", "message": answer})
    save_sessions()

    return {"response": answer}

# Get session history
@app.get("/history/{session_id}")
def get_history(session_id: str):
    if session_id not in chat_sessions:
        return JSONResponse(content={"error": "Invalid session ID"}, status_code=404)
    return {"messages": chat_sessions[session_id]}

@app.post("/submit-feedback")
async def submit_feedback(category: str = Form(...), message: str = Form(...)):
    sentiment = analyze_sentiment(message)
    insert_feedback(category, message, sentiment)
    return {"message": "Feedback received", "sentiment": sentiment}

@app.get("/feedbacks")
def get_feedbacks():
    feedback_entries = get_all_feedback()
    formatted = [
        f"{entry[1].capitalize()} - {entry[2]}"  # category - message
        for entry in feedback_entries
    ]
    return {"feedbacks": formatted}


@app.get("/sentiment-breakdown")
def get_sentiment_data():
    return get_sentiment_summary()

@app.get("/feedback-timeline")
def get_feedback_timeline():
    return get_monthly_feedback_counts()
@app.get("/sessions")
def get_sessions():
    return [{"id": sid, "title": (chat_sessions[sid][1]['message'].split('\n')[0][:30] 
                                  if len(chat_sessions[sid]) > 1 else "New Session")}
            for sid in chat_sessions]
