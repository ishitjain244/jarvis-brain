from flask import Flask, request, jsonify
from google import genai
import os

app = Flask(__name__)

# Reads the GEMINI_API_KEY set in Render's Environment Variables
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json() or {}
    user_prompt = data.get("prompt", "")

    # 1. Local / Remote Action Hooks
    if "ping phone" in user_prompt.lower():
        return jsonify({"reply": "Sending ping signal to your phone."})

    # 2. Forward query to Gemini Cloud
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
    # Render assigns its own port dynamically
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
