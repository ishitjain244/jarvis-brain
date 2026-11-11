import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from duckduckgo_search import DDGS
from groq import Groq

app = FastAPI()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

def search_web(query: str) -> str:
    """Fetches real-time web results using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = [r.get('body', '') for r in ddgs.text(query, max_results=3)]
            if results:
                return "Real-time web search info:\n" + "\n".join(results)
    except Exception as e:
        print(f"Web search failed: {e}")
    return ""

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        user_msg = request.message
        
        # Trigger web search for live queries (AQI, weather, time, dates, news)
        live_keywords = ["aqi", "weather", "news", "current", "today", "date", "time", "price", "score"]
        web_context = ""
        if any(kw in user_msg.lower() for kw in live_keywords):
            web_context = search_web(user_msg)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are Jarvis, an ultra-concise voice assistant. "
                    "CRITICAL RULE: Keep all answers extremely brief—maximum 1 to 2 short sentences or direct bullet points. "
                    "Never write long paragraphs. Speak naturally and directly."
                )
            }
        ]

        if request.history:
            for turn in request.history:
                if "user" in turn and "jarvis" in turn:
                    messages.append({"role": "user", "content": turn["user"]})
                    messages.append({"role": "assistant", "content": turn["jarvis"]})

        final_user_prompt = f"{web_context}\n\nUser Question: {user_msg}" if web_context else user_msg
        messages.append({"role": "user", "content": final_user_prompt})

        completion = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=messages,
            temperature=0.5,
            max_tokens=150
        )

        reply = completion.choices[0].message.content.strip()
        return {"response": reply}

    except Exception as e:
        print(f"Server error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {"status": "Jarvis backend online."}
