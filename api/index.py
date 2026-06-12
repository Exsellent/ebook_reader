from flask import Flask, render_template, request, jsonify, send_file

from tts import generate_audio
from translate import translate_text
from utils import load_book

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/tts", methods=["POST"])
def tts():
    text = request.json["text"]
    audio_path = generate_audio(text)
    return send_file(audio_path, mimetype="audio/mpeg")

@app.route("/api/translate", methods=["POST"])
def translate():
    text = request.json["text"]
    lang = request.json["lang"]
    return jsonify({"result": translate_text(text, lang)})
