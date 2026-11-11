import os
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
        
        # System instructions enforcing strict tense, memory retention, and ultra-concise replies
        system_prompt = (
            "You are Jarvis, an advanced, ultra-concise voice assistant.\n"
            "CRITICAL RULES:\n"
            "1. TENSE MATCHING: If the user asks about past events/scores, reply in the past tense. "
            "If they ask about current status, reply in the present tense. "
            "If they ask about future events (like upcoming board exams, schedules, or timelines), "
            "you MUST look up future/current data (current year is 2026) and never accidentally give previous year dates.\n"
            "2. MEMORY PERSISTENCE: Remember all details the user shares during the conversation "
            "(such as their location, subjects, preferences, or goals) and retain them across turns.\n"
            "3. BREVITY: Keep answers strictly between 1 to 2 short, punchy sentences optimized for speech.\n"
            "4. Never say you lack data; use built-in search for any real-time or factual lookup."
        )

        messages = [{"role": "system", "content": system_prompt}]

        # Inject persistent memory context if available
        if request.user_context:
            messages.append({
                "role": "system", 
                "content": f"Persistent User Context & Memory: {request.user_context}"
            })

        if request.history:
            for turn in request.history:
                if "user" in turn and "jarvis" in turn:
                    messages.append({"role": "user", "content": turn["user"]})
                    messages.append({"role": "assistant", "content": turn["jarvis"]})

        messages.append({"role": "user", "content": user_msg})

        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=[{"type": "browser_search"}],
            temperature=0.3,
            max_tokens=180
        )

        reply = completion.choices[0].message.content.strip()
        return {"response": reply}

    except Exception as e:
        print(f"Server error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {"status": "Jarvis backend online with memory & tense intelligence."}
