
import re
import threading
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import easyocr
import numpy as np
from flask import Flask, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates")
)

# Prevent excessively large image uploads.
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

_reader = None
_reader_lock = threading.Lock()
_deck_manager = None


def initialize_mobile(deck_manager):
    """Connect Flask to the existing deck manager."""
    global _deck_manager
    _deck_manager = deck_manager


def get_reader():
    """Initialize EasyOCR once, on demand."""
    global _reader

    if _reader is None:
        with _reader_lock:
            if _reader is None:
                _reader = easyocr.Reader(
                    ["en"],
                    gpu=False,
                    verbose=False
                )

    return _reader


def normalize(text):
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        str(text).lower()
    ).strip()


def get_all_cards():
    """Read cards through the app's existing JSON repository."""
    if _deck_manager is None:
        return []

    cards = []

    for deck in _deck_manager.repo.get_decks():
        deck_name = deck.get("name", "")

        for card in deck.get("cards", []):
            cards.append({
                "question": card.get("question", ""),
                "answer": card.get("answer", ""),
                "deck": deck_name
            })

    return cards



def search_cards(recognized_text, limit=10):
    cards = get_all_cards()

    # Split recognized text into a list of words.
    recognized_words = normalize(recognized_text).split()

    matches = []

    for card in cards:
        question_words = normalize(
            str(card.get("question", ""))
        ).split()

        # Match if any recognized word appears in the question.
        if any(word in question_words for word in recognized_words):
            matches.append(card)

        if len(matches) >= limit:
            break

    return matches


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/scan", methods=["POST"])
def scan_image():
    if _deck_manager is None:
        return jsonify({
            "error": "Flashcard repository is not connected."
        }), 500

    uploaded_file = request.files.get("image")

    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({
            "error": "Please take a photo or select an image."
        }), 400

    try:
        image_bytes = uploaded_file.read()

        if not image_bytes:
            return jsonify({"error": "The uploaded image is empty."}), 400

        # Decode uploaded image using OpenCV.
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            return jsonify({
                "error": "Could not read the image. Try another photo."
            }), 400

        # Resize large images to reduce OCR processing time.
        height, width = image.shape[:2]
        max_dimension = 1200

        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            image = cv2.resize(
                image,
                (
                    int(width * scale),
                    int(height * scale)
                ),
                interpolation=cv2.INTER_AREA
            )

        reader = get_reader()
        rgb_image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )

        ocr_results = reader.readtext(rgb_image)

        recognized_text = " ".join(
            text
            for _, text, confidence in ocr_results
            if confidence >= 0.4
        ).strip()

        if not recognized_text:
            return jsonify({
                "text": "",
                "matches": [],
                "message": (
                    "No text detected. Try better lighting "
                    "or move closer to the word."
                )
            })

        matches = search_cards(recognized_text)

        return jsonify({
            "text": recognized_text,
            "matches": matches,
            "message": (
                "Search complete."
                if matches
                else "No matching flashcards found."
            )
        })

    except Exception:
        app.logger.exception("Photo OCR failed")
        return jsonify({
            "error": (
                "OCR processing failed. Check the server console "
                "for details and try again."
            )
        }), 500


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({
        "error": "Image is too large. Maximum size is 10 MB."
    }), 413


def run_mobile_server(deck_manager, host="0.0.0.0", port=5000):
    """Run Flask in a background thread alongside Tkinter."""
    initialize_mobile(deck_manager)

    app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True
    )


def start_mobile_server(deck_manager, host="0.0.0.0", port=5000):
    thread = threading.Thread(
        target=run_mobile_server,
        args=(deck_manager, host, port),
        daemon=True
    )
    thread.start()
    return thread
