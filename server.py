import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from duckduckgo_search import DDGS
from groq import Groq  # Assuming you are using Groq for fast inference

app = FastAPI()

# Initialize Groq client using environment variable
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

def search_web(query: str) -> str:
    """Fetches real-time web results using DuckDuckGo for queries requiring current data."""
    try:
        with DDGS() as ddgs:
            results = [r.get('body', '') for r in ddgs.text(query, max_results=3)]
            if results:
                return "Recent web search context:\n" + "\n".join(results)
    except Exception as e:
        print(f"Web search failed: {e}")
    return ""

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        user_msg = request.message
        
        # Check if query needs real-time data (like news, weather, AQI, current events)
        live_keywords = ["aqi", "weather", "news", "current", "today", "latest", "price", "score"]
        web_context = ""
        if any(kw in user_msg.lower() for kw in live_keywords):
            web_context = search_web(user_msg)

        # Build conversation messages for the AI model
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Jarvis, a helpful, intelligent, and concise AI voice assistant. "
                    "Keep your responses direct, conversational, and optimized to be spoken out loud (avoid markdown links or complex symbols). "
                    "Use the provided web search context if available to answer accurately."
                )
            }
        ]

        # Add history if available
        if request.history:
            for turn in request.history:
                if "user" in turn and "jarvis" in turn:
                    messages.append({"role": "user", "content": turn["user"]})
                    messages.append({"role": "assistant", "content": turn["jarvis"]})

        # Append current user message along with any live web context found
        final_user_prompt = f"{web_context}\n\nUser Question: {user_msg}" if web_context else user_msg
        messages.append({"role": "user", "content": final_user_prompt})

        # Call the LLM (using your preferred model)
        completion = client.chat.completions.create(
            model="qwen/qwen3.8-27b",  # or llama-3.3-70b-versatile depending on your preference
            messages=messages,
            temperature=0.7,
            max_tokens=400
        )

        reply = completion.choices[0].message.content.strip()
        return {"response": reply}

    except Exception as e:
        print(f"Server error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {"status": "Jarvis backend is online and web-enabled."}
