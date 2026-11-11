import os
import datetime
import pytz
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from groq import Groq

app = FastAPI()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    user_context: Optional[Dict[str, Any]] = {}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        user_msg = request.message
        
        # Lock in precise Indian Standard Time (IST) dynamically
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.datetime.now(ist)
        current_date_str = now.strftime("%A, %B %d, %Y")
        current_time_str = now.strftime("%I:%M %p")

        system_prompt = (
            f"You are Jarvis, an ultra-concise, accurate voice assistant.\n"
            f"LOCAL TIME & DATE CONTEXT: Today is {current_date_str}. The current time is {current_time_str} IST.\n\n"
            "CRITICAL RULES:\n"
            "1. ACCURACY: Always use the exact IST time and date context above when asked about time/date. Use built-in web search for AQI, weather, news, or live data.\n"
            "2. TENSE CONSISTENCY: Match the user's tense. Reply to past questions in past tense, present in present tense, and upcoming/future questions in future tense.\n"
            "3. BREVITY: Speak in strictly 1 to 2 short sentences.\n"
            "4. MEMORY RECALL: Continuously incorporate user facts (location, subjects, name) provided in User Context."
        )

        messages = [{"role": "system", "content": system_prompt}]

        if request.user_context:
            messages.append({"role": "system", "content": f"Stored User Context & Memory: {request.user_context}"})

        if request.history:
            for turn in request.history[-6:]:
                if "user" in turn and "jarvis" in turn:
                    messages.append({"role": "user", "content": turn["user"]})
                    messages.append({"role": "assistant", "content": turn["jarvis"]})

        messages.append({"role": "user", "content": user_msg})

        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=[{"type": "browser_search"}],
            temperature=0.2,
            max_tokens=150
        )

        reply = completion.choices[0].message.content.strip()
        return {"response": reply}

    except Exception as e:
        print(f"Server error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {"status": "Jarvis backend online with persistent memory & IST time lock."}
