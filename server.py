from flask import Flask, request, jsonify
from google import genai
import os

app = Flask(__name__)

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

@app.route('/ask', methods=['POST', 'GET'])
def ask():
    data = request.get_json(silent=True) or {}
    user_prompt = data.get("prompt") or request.args.get("prompt", "")

    if not user_prompt:
        return jsonify({"reply": "Jarvis is online and ready."})

    try:
        # Testing with gemini-3.8-flash
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=user_prompt
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        # This will send the EXACT raw error back to your screen so we can fix it instantly
        return jsonify({"reply": f"RAW ERROR: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
