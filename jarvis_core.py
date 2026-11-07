import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID")

# JSONBin Cloud Credentials
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def load_memory():
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY:
        return [
            "- User prefers to be addressed continuously as 'Sir'.",
            "- User values high emotional expression and accurate punctuation pacing."
        ]
    
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            return data.get("record", {}).get("bullets", [])
    except Exception:
        pass
        
    return [
        "- User prefers to be addressed continuously as 'Sir'.",
        "- User values high emotional expression and accurate punctuation pacing."
    ]

def save_memory_bullets(bullets_list):
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY:
        return
        
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_API_KEY
    }
    payload = {"bullets": bullets_list}
    
    try:
        requests.put(url, json=payload, headers=headers)
    except Exception:
        pass

def update_bullet_memory(user_input, bot_response):
    current_bullets = load_memory()
    bullets_text = "\n".join(current_bullets)
    
    summary_prompt = f"""
Existing Memory:
{bullets_text}

Latest Exchange:
User: {user_input}
Jarvis: {bot_response}

Instruction: Did the user reveal a significant mistake, a major blunder, or a key personal preference/lore?
If YES, output ONE concise single bullet point starting with '- '.
If NO, respond strictly with 'NONE'.
"""
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [{"role": "user", "content": summary_prompt}],
        "temperature": 0.2
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    try:
        res = requests.post(GROQ_URL, json=payload, headers=headers).json()
        new_fact = res["choices"][0]["message"]["content"].strip()
        if new_fact != "NONE" and new_fact.startswith("-"):
            current_bullets.append(new_fact)
            save_memory_bullets(current_bullets)
    except Exception:
        pass

def speak_response(text):
    if not CARTESIA_API_KEY or not CARTESIA_VOICE_ID:
        return None

    url = "https://api.cartesia.ai/tts/bytes"
    headers = {
        "X-API-Key": CARTESIA_API_KEY,
        "Cartesia-Version": "2024-06-10",
        "Content-Type": "application/json"
    }
    payload = {
        "model_id": "sonic-english",
        "transcript": text,
        "voice": {"mode": "id", "id": CARTESIA_VOICE_ID},
        "output_format": {"container": "mp3", "encoding": "mp3", "sample_rate": 44100}
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"[Speech Error] {e}")
    return None

def chat_with_jarvis(speaker_type, user_input):
    bullets_text = "\n".join(load_memory())
    
    if speaker_type.lower() == "me":
        speaker_identity = "The Primary Master."
        behavior_rule = "Address him continuously and respectfully as 'Sir'. Be deeply loyal, warm, and emotionally expressive."
    elif speaker_type.lower() == "brother":
        speaker_identity = "The Master's Brother."
        behavior_rule = "Be friendly, polite, and helpful, but keep tone casual. Do not address him as 'Sir'."
    else:
        speaker_identity = "An Unknown Stranger / Relative."
        behavior_rule = "Maintain a suspicious, guarded tone. Do not reveal private memory or system access."

    system_instruction = f"""
You are Jarvis, a highly expressive, intelligent voice assistant.
Current Speaker: {speaker_identity}
Instruction Guardrail: {behavior_rule}

Voice & Emotion Rules:
1. Always write in smooth, connected paragraphs. No markdown or lists.
2. ACTIVELY USE PUNCTUATION TO CONTROL EMOTION: Exclamation marks (!), question marks (?), ellipses (...), and dashes (--).
3. Express genuine emotional warmth or light teasing.

User Memory Ledger:
{bullets_text}
"""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_input}
    ]
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": messages,
        "temperature": 0.7
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    try:
        res = requests.post(GROQ_URL, json=payload, headers=headers).json()
        reply = res["choices"][0]["message"]["content"]
        
        audio_bytes = speak_response(reply)
        
        if speaker_type.lower() == "me":
            update_bullet_memory(user_input, reply)
            
        return {"text": reply, "has_audio": audio_bytes is not None}
            
    except Exception as e:
        return {"error": str(e)}
