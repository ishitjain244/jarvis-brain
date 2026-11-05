from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
  return "Jarvis Backend is Alive!"


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
