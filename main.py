import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Jarvis Cloud Brain is online!"

@app.route("/alexa-webhook", methods=["POST"])
def alexa_webhook():
    data = request.json
    print("Received command from Alexa:", data)

    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": "Hello! Jarvis cloud brain is listening to you."
            },
            "shouldEndSession": True
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
