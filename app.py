from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
  return jsonify({"status": "online", "message": "Jarvis Cloud Brain is active!"})


@app.route("/command", methods=["POST"])
def handle_command():
  req_data = request.get_json() or {}

  # Determine what kind of request Alexa sent (LaunchRequest vs IntentRequest)
  request_type = req_data.get("request", {}).get("type", "")

  if request_type == "LaunchRequest":
    reply_text = "Jarvis is online. How can I assist you today?"
  elif request_type == "IntentRequest":
    intent_name = req_data.get("request", {}).get("intent", {}).get("name", "")
    reply_text = (
        f"Jarvis cloud brain received your request for intent {intent_name}!"
    )
  else:
    reply_text = "Jarvis received your command!"

  # Standard Alexa JSON format
  alexa_response = {
      "version": "1.0",
      "response": {
          "outputSpeech": {"type": "PlainText", "text": reply_text},
          "shouldEndSession": False,  # Keep listening for next command
      },
  }

  return jsonify(alexa_response)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
