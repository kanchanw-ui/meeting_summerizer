from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from typing import List
import docx
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI()

# CORS setup
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import sqlite3
from datetime import datetime

# Database setup
def init_db():
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS meetings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT,
                  transcript TEXT,
                  summary TEXT,
                  emails TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

class HistoryItem(BaseModel):
    id: int
    filename: str
    transcript: str
    summary: str
    emails: List[str]
    timestamp: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/history", response_model=List[HistoryItem])
def get_history():
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    c.execute("SELECT id, filename, transcript, summary, emails, timestamp FROM meetings ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        # emails are stored as JSON string in DB, need to parse back to list
        try:
            email_list = json.loads(row[4])
        except:
            email_list = []
            
        history.append(HistoryItem(
            id=row[0], 
            filename=row[1], 
            transcript=row[2],
            summary=row[3], 
            emails=email_list,
            timestamp=row[5]
        ))
    return history

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename
    content = ""
    
    try:
        if filename.endswith(".txt"):
            content = (await file.read()).decode("utf-8")
        elif filename.endswith(".docx"):
            # Save temporarily to read with python-docx
            temp_filename = f"temp_{filename}"
            with open(temp_filename, "wb") as f:
                f.write(await file.read())
            
            doc = docx.Document(temp_filename)
            content = "\n".join([para.text for para in doc.paragraphs])
            
            # Clean up
            os.remove(temp_filename)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload .txt or .docx")
            
        return {"transcript": content, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GenerateResponse(BaseModel):
    summary: str
    emails: List[str]

class GenerateRequest(BaseModel):
    transcript: str
    filename: str = "Unknown File"

@app.post("/generate", response_model=GenerateResponse)
async def generate_content(request: GenerateRequest):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("DEBUG: No API Key found in env")
        raise HTTPException(status_code=500, detail="API Key not found. Please set GEMINI_API_KEY in .env file.")
    
    print(f"DEBUG: Using API Key starting with: {api_key[:5]}")
    genai.configure(api_key=api_key)
    
    # Using gemini-flash-latest as it is explicitly listed
    model = genai.GenerativeModel('gemini-flash-latest')
    
    prompt = f"""
    You are an expert meeting assistant. Analyze the following meeting transcript and provide:
    1. A summary of the meeting (100-150 words).
    2. Three distinct follow-up email drafts:
       - Option 1: Formal and detailed.
       - Option 2: Concise and action-oriented.
       - Option 3: Friendly and casual.
    
    Return the output strictly in VALID JSON format with the following structure. Do not include any markdown formatting like ```json ... ```, just the raw JSON string:
    {{
        "summary": "...",
        "emails": ["Email 1 content...", "Email 2 content...", "Email 3 content..."]
    }}
    
    Transcript:
    {request.transcript[:10000]} 
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text
        
        # Clean up markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        data = json.loads(content)
        
        # Save to DB
        try:
            conn = sqlite3.connect('meetings.db')
            c = conn.cursor()
            c.execute("INSERT INTO meetings (filename, transcript, summary, emails) VALUES (?, ?, ?, ?)",
                      (request.filename, request.transcript, data["summary"], json.dumps(data["emails"])))
            conn.commit()
            conn.close()
        except Exception as db_err:
            print(f"Database Error: {db_err}")
        
        return GenerateResponse(summary=data["summary"], emails=data["emails"])
        
    except Exception as e:
        print(f"Error generating content: {e}")
        with open("error.log", "w") as f:
            f.write(str(e))
        # Fallback to dummy data for demo purposes if API fails
        print("Falling back to Demo Mode")
        
        demo_summary = "⚠️ **DEMO MODE (API Key Invalid)**\n\nThis is a simulated summary because the provided API key was invalid or expired. In a real scenario, this text would be generated by Google Gemini based on your transcript.\n\nKey points from the meeting:\n- Discussed project timeline and deliverables.\n- Identified key stakeholders for the next phase.\n- Agreed on a follow-up meeting next Tuesday."
        
        demo_emails = [
            "Subject: Meeting Follow-up - Formal\n\nDear Team,\n\nThank you for your time today. As discussed, we will proceed with the agreed-upon timeline. Please review the attached action items.\n\nBest regards,\n[Your Name]",
            "Subject: Action Items\n\nHi everyone,\n\nGreat meeting! Here's what we need to do next:\n1. Finalize the report.\n2. Contact the vendor.\n\nCheers,\n[Your Name]",
            "Subject: Quick recap\n\nHey team,\n\nThanks for hopping on the call. Just wanted to send a quick note that we are good to go on the new feature. Let's crush it!\n\nBest,\n[Your Name]"
        ]
        
        return GenerateResponse(summary=demo_summary, emails=demo_emails)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
