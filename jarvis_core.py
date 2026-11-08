import os
import sys
import requests
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def load_memory():
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY:
        return ["- User prefers to be addressed as 'Sir'."]
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json().get("record", {}).get("bullets", [])
    except Exception:
        pass
    return ["- User prefers to be addressed as 'Sir'."]

def save_memory_bullets(bullets_list):
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY:
        return
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {"Content-Type": "application/json", "X-Master-Key": JSONBIN_API_KEY}
    try:
        requests.put(url, json={"bullets": bullets_list}, headers=headers)
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
Instruction: Did the user reveal a significant personal preference or key lore? If YES, output ONE concise bullet point starting with '- '. If NO, respond with 'NONE'.
"""
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [{"role": "user", "content": summary_prompt}],
        "temperature": 0.2,
        "max_tokens": 30
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
        print(f"[CARTESIA MISSING LOG] KEY: {bool(CARTESIA_API_KEY)}, VOICE: {bool(CARTESIA_VOICE_ID)}")
        sys.stdout.flush()
        return None
        
    url = "https://api.cartesia.ai/tts/bytes"
    
    headers = {
        "Authorization": f"Bearer {CARTESIA_API_KEY}",
        "X-API-Key": CARTESIA_API_KEY,
        "Cartesia-Version": "2024-06-10",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model_id": "sonic-latest",  # Using the official supported dynamic alias
        "transcript": text,
        "voice": {
            "mode": "id",
            "id": CARTESIA_VOICE_ID
        },
        "output_format": {
            "container": "mp3",
            "encoding": "mp3",
            "sample_rate": 44100
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print("[CARTESIA SUCCESS] Voice bytes generated successfully!")
            sys.stdout.flush()
            return response.content
        else:
            print(f"[CARTESIA API ERROR] Status Code: {response.status_code} | Body: {response.text}")
            sys.stdout.flush()
    except Exception as e:
        print(f"[CARTESIA EXCEPTION] {str(e)}")
        sys.stdout.flush()
        
    return None


def chat_with_jarvis(speaker_type, user_input):
    bullets_text = "\n".join(load_memory())
    
    system_instruction = f"""
You are Jarvis, an ultra-concise voice assistant. Address the user as 'Sir'.
RULES:
1. MAXIMUM 3 TO 6 WORDS. Never write long sentences or paragraphs.
2. Direct match examples:
   - User: "Hi" -> Reply: "Hello, Sir."
   - User: "What are you doing?" -> Reply: "Standing by, Sir."
3. Use light natural punctuation (..., ,, ?) for human-like voice pacing.

Memory:
{bullets_text}
"""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_input}
    ]
    
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 20
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    try:
        res_raw = requests.post(GROQ_URL, json=payload, headers=headers)
        res = res_raw.json()
        
        if "choices" not in res:
            return {"text": "Online, Sir.", "audio_bytes": None}
            
        reply = res["choices"][0]["message"]["content"]
        audio_bytes = speak_response(reply)
        
        if speaker_type.lower() == "me":
            update_bullet_memory(user_input, reply)
            
        return {"text": reply, "audio_bytes": audio_bytes}
            
    except Exception as e:
        return {"text": "Error, Sir.", "audio_bytes": None}

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "Jarvis is online and active!"}), 200

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    data = request.json or {}
    speaker = data.get("speaker", "me")
    message = data.get("message", "")
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
        
    result = chat_with_jarvis(speaker, message)
    reply_text = result.get("text")
    audio_bytes = result.get("audio_bytes")
    
    if audio_bytes:
        return Response(audio_bytes, mimetype="audio/mpeg")
        
    return jsonify({"text": reply_text}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

import uuid

# Temporary in-memory audio store for Alexa GET requests
AUDIO_CACHE = {}

@app.route("/alexa", methods=["POST"])
def alexa_webhook():
    req = request.json or {}
    req_type = req.get("request", {}).get("type", "")
    
    user_speech = "Hello"
    if req_type == "IntentRequest":
        intent_name = req.get("request", {}).get("intent", {}).get("name", "")
        
        # Catch Alexa's built-in stop/cancel intents or user saying exit words
        if intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
            return jsonify({
                "version": "1.0",
                "response": {
                    "outputSpeech": {"type": "PlainText", "text": "Goodbye, Sir."},
                    "shouldEndSession": True
                }
            })
            
        slots = req.get("request", {}).get("intent", {}).get("slots", {})
        for key, val in slots.items():
            if "value" in val:
                user_speech = val["value"]
                break
    elif req_type == "LaunchRequest":
        user_speech = "Hi Jarvis"

    # Also catch text-based exit triggers if passed through speech slot
    if user_speech.lower() in ["exit", "stop", "bye", "quit", "shut down"]:
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": "Shutting down, Sir."},
                "shouldEndSession": True
            }
        })

    # Normal chat processing...
    result = chat_with_jarvis("me", user_speech)
    reply_text = result.get("text")
    audio_bytes = result.get("audio_bytes")
    
    # (Rest of your AudioPlayer stream response code goes here...)

    
    if not audio_bytes:
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": reply_text},
                "shouldEndSession": False
            }
        })

    # Store audio bytes in memory for Alexa to fetch via GET
    audio_id = str(uuid.uuid4())
    AUDIO_CACHE[audio_id] = audio_bytes

    audio_stream_url = f"https://jarvis-brain-3y1y.onrender.com/stream-audio/{audio_id}"

    alexa_response = {
        "version": "1.0",
        "response": {
            "outputSpeech": None,
            "directives": [
                {
                    "type": "AudioPlayer.Play",
                    "playBehavior": "REPLACE_ALL",
                    "audioItem": {
                        "stream": {
                            "url": audio_stream_url,
                            "token": audio_id,
                            "offsetInMilliseconds": 0
                        }
                    }
                }
            ],
            "shouldEndSession": False
        }
    }
    return jsonify(alexa_response)

@app.route("/stream-audio/<audio_id>", methods=["GET"])
def stream_cached_audio(audio_id):
    audio_bytes = AUDIO_CACHE.get(audio_id)
    if not audio_bytes:
        return "Audio not found", 404
    return Response(audio_bytes, mimetype="audio/mpeg")
    
