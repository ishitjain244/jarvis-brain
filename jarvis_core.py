import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def chat_with_jarvis(speaker, message):
    try:
        groq_headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            "You are Jarvis, an elite, highly concise artificial intelligence assistant. "
            "Address your user as 'Sir'. Keep your responses short, natural, and under 2 sentences "
            "so they sound great when spoken aloud."
        )
        
        groq_payload = {
            "model": "qwen-2.7b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{speaker}: {message}"}
            ],
            "max_tokens": 120
        }
        
        groq_res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=groq_headers, json=groq_payload, timeout=10)
        groq_data = groq_res.json()
        reply_text = groq_data.get("choices", [{}])[0].get("message", {}).get("content", "At your service, Sir.")
        return reply_text
    except Exception as e:
        print(f"Error in Groq pipeline: {e}")
        return "Systems are experiencing a slight glitch, Sir."

@app.route("/", methods=["GET"])
def home():
    return "Jarvis Engine is online, Sir.", 200

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
                "outputSpeech": {"type": "PlainText", "text": reply_text},
                "reprompt": {"outputSpeech": {"type": "PlainText", "text": "Standing by, Sir."}},
                "shouldEndSession": False
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
            
        # Extract the spoken text from our custom ChatIntent slot
        slots = req.get("request", {}).get("intent", {}).get("slots", {})
        if "user_input" in slots and "value" in slots["user_input"]:
            user_speech = slots["user_input"]["value"]

    # Exit command check
    if user_speech.lower() in ["exit", "stop", "bye", "quit", "shut down"]:
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": "Shutting down systems. Have a good day, Sir."},
                "shouldEndSession": True
            }
        })

    # Generate response from Groq
    reply_text = chat_with_jarvis("me", user_speech)

    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {"type": "PlainText", "text": reply_text},
            "reprompt": {"outputSpeech": {"type": "PlainText", "text": "Standing by for your next command, Sir."}},
            "shouldEndSession": False  # Keeps session wide open!
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
