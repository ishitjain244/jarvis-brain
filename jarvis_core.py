import os
import uuid
import io
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# Configuration keys (pulling from Render Environment Variables)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY")
CARTESIA_VOICE_ID = os.environ.get("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091") # Default fallback voice

# In-memory store for serving audio snippets to Alexa via GET requests
AUDIO_CACHE = {}

def chat_with_jarvis(speaker, message):
    """
    Core function that queries Groq LLM for a response, 
    then passes the text into Cartesia TTS to generate raw MP3 audio bytes.
    """
    try:
        # 1. Query Groq LLM (Qwen model)
        groq_headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        groq_payload = {
            "model": "qwen-2.7b", # Or your active model string
            "messages": [
                {"role": "system", "content": "You are Jarvis, an elite, highly concise artificial intelligence assistant serving your user with a formal 'Sir' persona."},
                {"role": "user", "content": f"{speaker}: {message}"}
            ],
            "max_tokens": 150
        }
        
        groq_res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=groq_headers, json=groq_payload, timeout=10)
        groq_data = groq_res.json()
        reply_text = groq_data.get("choices", [{}])[0].get("message", {}).get("content", "At your service, Sir.")
        
        # 2. Convert response text to audio using Cartesia TTS API
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
        
        if cartesia_res.status_code == 200:
            audio_bytes = cartesia_res.content
        else:
            audio_bytes = None

        return {
            "text": reply_text,
            "audio_bytes": audio_bytes
        }
        
    except Exception as e:
        print(f"Error in chat_with_jarvis pipeline: {e}")
        return {
            "text": "Systems are encountering an exception, Sir.",
            "audio_bytes": None
        }


@app.route("/", methods=["GET"])
def home():
    """Health check route to verify Render server status."""
    return "Jarvis is online and active, Sir.", 200


@app.route("/chat", methods=["POST"])
def termux_chat():
    """
    Endpoint for Termux / direct clients. 
    Accepts JSON with message and streams raw MP3 audio bytes directly.
    """
    data = request.json or {}
    speaker = data.get("speaker", "me")
    message = data.get("message", "Hello")
    
    result = chat_with_jarvis(speaker, message)
    audio_bytes = result.get("audio_bytes")
    
    if not audio_bytes:
        return jsonify({"error": "Audio generation failed"}), 500
        
    # Stream bytes directly without saving files to disk
    return Response(audio_bytes, mimetype="audio/mpeg")


@app.route("/alexa", methods=["POST"])
def alexa_webhook():
    """
    Endpoint for Amazon Alexa Custom Skill requests.
    Interprets user speech, generates audio via Cartesia, and returns an AudioPlayer directive.
    """
    req = request.json or {}
    req_type = req.get("request", {}).get("type", "")
    
    user_speech = "Hello"
    
    if req_type == "LaunchRequest":
        user_speech = "Jarvis online and awaiting your command, Sir."
    elif req_type == "IntentRequest":
        intent_name = req.get("request", {}).get("intent", {}).get("name", "")
        
        # Handle built-in stop/cancel requests gracefully
        if intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
            return jsonify({
                "version": "1.0",
                "response": {
                    "outputSpeech": {"type": "PlainText", "text": "Goodbye, Sir."},
                    "shouldEndSession": True
                }
            })
            
        # Extract speech slots safely
        slots = req.get("request", {}).get("intent", {}).get("slots", {})
        for key, val in slots.items():
            if "value" in val:
                user_speech = val["value"]
                break

    # Quick text-based exit check
    if user_speech.lower() in ["exit", "stop", "bye", "quit", "shut down"]:
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": "Shutting down audio systems, Sir."},
                "shouldEndSession": True
            }
        })

    # Run core brain pipeline (Groq + Cartesia)
    result = chat_with_jarvis("me", user_speech)
    reply_text = result.get("text")
    audio_bytes = result.get("audio_bytes")
    
    if not audio_bytes:
        # Fallback to plain text speech if TTS fails
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": reply_text or "Systems active, Sir."},
                "shouldEndSession": False
            }
        })

    # Cache audio temporarily in memory so Alexa's GET request can fetch it securely
    audio_id = str(uuid.uuid4())
    AUDIO_CACHE[audio_id] = audio_bytes
    
    audio_stream_url = f"https://jarvis-brain-3y1y.onrender.com/stream-audio/{audio_id}"

    # Return standard Alexa AudioPlayer directive
    return jsonify({
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
            "shouldEndSession": True  # Closes session safely once audio streaming begins
        }
    })


@app.route("/stream-audio/<audio_id>", methods=["GET"])
def stream_cached_audio(audio_id):
    """
    Secure temporary GET endpoint for Alexa Echo Dot to fetch the generated MP3 stream.
    """
    audio_bytes = AUDIO_CACHE.get(audio_id)
    if not audio_bytes:
        return "Audio stream expired or not found", 404
        
    return Response(audio_bytes, mimetype="audio/mpeg")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
