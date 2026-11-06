from flask import Flask, request, jsonify
from google import genai
import os

app = Flask(__name__)

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

@app.route('/ask', methods=['POST', 'GET'])
def ask():
    # silent=True prevents the 415 error if the header is missing
    data = request.get_json(silent=True) or {}
    
    # Grab prompt from JSON body, or fallback to URL query parameters (?prompt=...)
    user_prompt = data.get("prompt") or request.args.get("prompt", "")

    if not user_prompt:
        return jsonify({"reply": "Hello! Jarvis is online and listening. Send a prompt to chat."})

    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=user_prompt
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        error_message = str(e)
        if "503" in error_message or "high demand" in error_message.lower():
            return jsonify({"reply": "The AI model is currently busy. Please try again shortly."})
        return jsonify({"reply": f"Error: {error_message}"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
