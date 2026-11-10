import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq

app = FastAPI()

# Initialize Groq client
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class QueryRequest(BaseModel):
    message: str
    history: list = []

@app.get("/")
def home():
    return {"status": "Jarvis Render Brain is online"}

@app.post("/chat")
def chat(payload: QueryRequest):
    try:
        messages = [
            {"role": "system", "content": "You are Jarvis, a concise, helpful, and highly intelligent local AI assistant."}
        ]
        
        # Append history
        for item in payload.history:
            messages.append({"role": "user", "content": item.get("user", "")})
            messages.append({"role": "assistant", "content": item.get("jarvis", "")})
            
        messages.append({"role": "user", "content": payload.message})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.6,
            max_tokens=200
        )
        
        response_text = completion.choices[0].message.content
        return {"response": response_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  
