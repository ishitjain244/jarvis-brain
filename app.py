from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
  return jsonify({
      "status": "online",
      "message": "Jarvis Cloud Brain is active and ready!",
  })


@app.route("/command", methods=["POST"])
def handle_command():
  # Get data sent by Alexa
  data = request.get_json() or {}

  # Default reply message
  reply_text = "Jarvis cloud brain is online and connected to your Alexa skill!"

  # Alexa requires responses to follow this exact structure
  alexa_response = {
      "version": "1.0",
      "response": {
          "outputSpeech": {"type": "PlainText", "text": reply_text},
          "shouldEndSession": True,
      },
  }

  return jsonify(alexa_response)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
