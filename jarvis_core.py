import os
import uuid
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY")
CARTESIA_VOICE_ID = os.environ.get("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")

AUDIO_CACHE = {}

def chat_with_jarvis(speaker, message):
    try:
        groq_headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        groq_payload = {
            "model": "qwen-2.7b",
            "messages": [
                {"role": "system", "content": "You are Jarvis, an elite, highly concise artificial intelligence assistant serving your user with a formal 'Sir' persona."},
                {"role": "user", "content": f"{speaker}: {message}"}
            ],
            "max_tokens": 150
        }
        
        groq_res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=groq_headers, json=groq_payload, timeout=10)
        groq_data = groq_res.json()
        reply_text = groq_data.get("choices", [{}])[0].get("message", {}).get("content", "At your service, Sir.")
        
        cartesia_headers = {
            "Authorization": f"Bearer {CARTESIA_API_KEY}",
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json"
        }
        cartesia_payload = {
            "model_id": "sonic-latest",
            "transcript": reply_text,
            "voice": {
                "mode": "id",
                "id": CARTESIA_VOICE_ID
            },
            "output_format": {
                "container": "mp3",
                "bit_rate": 128000,
                "sample_rate": 44100
            }
        }
        
        cartesia_res = requests.post("https://api.cartesia.ai/audio/bytes", headers=cartesia_headers, json=cartesia_payload, timeout=15)
        audio_bytes = cartesia_res.content if cartesia_res.status_code == 200 else None

        return {
            "text": reply_text,
            "audio_bytes": audio_bytes
        }
    except Exception as e:
        print(f"Error in pipeline: {e}")
        return {
            "text": "Systems are encountering an exception, Sir.",
            "audio_bytes": None
        }

@app.route("/", methods=["GET"])
def home():
    return "Jarvis is online and active, Sir.", 200

@app.route("/chat", methods=["POST"])
def termux_chat():
    data = request.json or {}
    result = chat_with_jarvis(data.get("speaker", "me"), data.get("message", "Hello"))
    if not result.get("audio_bytes"):
        return jsonify({"error": "Audio generation failed"}), 500
    return Response(result.get("audio_bytes"), mimetype="audio/mpeg")

@app.route("/alexa", methods=["POST"])
def alexa_webhook():
    req = request.json or {}
    req_type = req.get("request", {}).get("type", "")
    
    user_speech = "Hello"
    
    if req_type == "LaunchRequest":
        reply_text = "Jarvis online and awaiting your command, Sir."
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": reply_text
                },
                "reprompt": {
                    "outputSpeech": {
                        "type": "PlainText",
                        "text": "What are your orders, Sir?"
                    }
                },
                "shouldEndSession": False  # Keeps microphone open so it doesn't disconnect!
            }
        })
        
    elif req_type == "IntentRequest":
        intent_name = req.get("request", {}).get("intent", {}).get("name", "")
        
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

    if user_speech.lower() in ["exit", "stop", "bye", "quit", "shut down"]:
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": "Shutting down systems, Sir."},
                "shouldEndSession": True
            }
        })

    # Generate normal chat response text
    result = chat_with_jarvis("me", user_speech)
    reply_text = result.get("text")

    # Keep session open (`shouldEndSession: false`) so Alexa listens for your next sentence without disconnecting
    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": reply_text
            },
            "reprompt": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "Standing by for your next command, Sir."
                }
            },
            "shouldEndSession": False
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
