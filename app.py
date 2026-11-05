from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
  return jsonify({
      "status": "online",
      "message": "Jarvis Cloud Brain is active and ready for online tasks!",
  })


# This route will handle incoming commands from Alexa or web services later
@app.route("/command", methods=["POST"])
def handle_command():
  data = request.get_json() or {}
  user_query = data.get("query", "No query provided")

  # For now, we will just echo back a confirmation response
  return jsonify({
      "status": "success",
      "received_query": user_query,
      "reply": (
          f"I received your online instruction: '{user_query}'. Gmail and"
          " browser integrations are coming up next!"
      ),
  })


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
