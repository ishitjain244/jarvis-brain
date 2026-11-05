from google import genai
from flask import Flask, jsonify, request

app = Flask(__name__)

# Initialize the Gemini client using your AI Studio API key
# (Tip: On Render, you can add GEMINI_API_KEY as an Environment Variable instead of hardcoding it)
client = genai.Client(api_key="AQ.Ab8RN6Kk2juNPm8W-dwve85RzuuG7a7XgcSBM7Er2d1eu6w8nQ")


@app.route("/", methods=["GET"])
def home():
  return jsonify(
      {"status": "online", "message": "Jarvis-Gemini Cloud Brain is active!"}
  )


@app.route("/command", methods=["POST"])
def handle_command():
  req_data = request.get_json() or {}

  request_type = req_data.get("request", {}).get("type", "")
  intent_name = (
      req_data.get("request", {}).get("intent", {}).get("name", "Unknown")
  )

  # Default reply text
  reply_text = "Hello from Jarvis"

  if request_type == "LaunchRequest":
    reply_text = "Jarvis powered by Gemini is online. What would you like to ask?"

  elif request_type == "IntentRequest":
    # Extract what the user said or handle based on intent
    if intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
      reply_text = "Goodbye!"
    elif intent_name == "AMAZON.HelpIntent":
      reply_text = (
          "You can ask Jarvis anything, and Gemini will answer you live."
      )
    else:
      # Pass a prompt to Gemini (you can extract slots from Alexa if you set up a search query slot)
      try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Give a short, punchy 1-sentence voice answer to: Who are you?",
        )
        reply_text = response.text
      except Exception as e:
        reply_text = "Sorry, I had trouble reaching Google Gemini."

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
