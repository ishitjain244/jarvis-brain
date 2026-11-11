import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from groq import Groq

app = FastAPI()

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        user_msg = request.message
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Jarvis, an ultra-concise voice assistant. "
                    "CRITICAL RULES:\n"
                    "1. Keep answers extremely brief—maximum 1 to 2 short sentences.\n"
                    "2. Use the built-in search tool for any live queries regarding current dates, time, weather, AQI, or news.\n"
                    "3. Never mention missing data or constraints."
                )
            }
        ]

        if request.history:
            for turn in request.history:
                if "user" in turn and "jarvis" in turn:
                    messages.append({"role": "user", "content": turn["user"]})
                    messages.append({"role": "assistant", "content": turn["jarvis"]})

        messages.append({"role": "user", "content": user_msg})

        # Call Groq with built-in browser search tool enabled for real-time lookups
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",  # Supports native built-in tools on Groq
            messages=messages,
            tools=[{"type": "browser_search"}],
            temperature=0.3,
            max_tokens=150
        )

        reply = completion.choices[0].message.content.strip()
        return {"response": reply}

    except Exception as e:
        print(f"Server error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {"status": "Jarvis backend online with native search."}
