from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
  return jsonify(
      {"status": "online", "message": "Jarvis Cloud Brain is active!"}
  )


@app.route("/command", methods=["POST"])
def handle_command():
  req_data = request.get_json() or {}

  # Safely extract request type and intent name
  request_type = req_data.get("request", {}).get("type", "")
  intent_name = (
      req_data.get("request", {}).get("intent", {}).get("name", "Unknown")
  )

  # Formulate appropriate response text
  if request_type == "LaunchRequest":
    reply_text = "Jarvis is online and ready for your commands!"
  elif request_type == "IntentRequest":
    if intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
      reply_text = "Goodbye!"
    elif intent_name == "AMAZON.HelpIntent":
      reply_text = (
          "You can ask Jarvis to run web searches or check your emails."
      )
    else:
      reply_text = (
          f"Jarvis cloud brain successfully executed intent {intent_name}!"
      )
  else:
    reply_text = "Jarvis received your command!"

  # Strict Alexa ASK JSON Response Structure
  alexa_response = {
      "version": "1.0",
      "response": {
          "outputSpeech": {"type": "PlainText", "text": reply_text},
          "shouldEndSession": False,
      },
  }

  return jsonify(alexa_response)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
