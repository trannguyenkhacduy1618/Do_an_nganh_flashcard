
import re
import threading
from pathlib import Path
from urllib.parse import quote

import cv2
import easyocr
import numpy as np
import requests

from flask import (
    Flask,
    current_app,
    jsonify,
    render_template,
    request,
)

BASE_DIR = Path(__file__).resolve().parent

_reader = None
_reader_lock = threading.Lock()

# --------------------------------------------------
# OCR
# --------------------------------------------------


def get_reader():
    """Initialize EasyOCR once, safely across threads."""
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


# --------------------------------------------------
# HELPERS
# --------------------------------------------------


def normalize(text):
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        str(text).lower()
    ).strip()


def get_all_cards(deck_manager):
    """Get all cards from the existing JSON repository."""
    cards = []

    for deck in deck_manager.repo.get_decks():
        for card in deck.get("cards", []):
            cards.append(
                {
                    **card,
                    "deck": deck.get("name", ""),
                    "deck_id": deck.get("id"),
                }
            )

    return cards


def search_cards(deck_manager, recognized_text, limit=10):
    """Match recognized OCR words against card questions."""
    cards = get_all_cards(deck_manager)
    recognized_words = set(normalize(recognized_text).split())

    matches = []

    for card in cards:
        question = normalize(card.get("question", ""))
        question_words = set(question.split())

        if recognized_words.intersection(question_words):
            matches.append(card)

        if len(matches) >= limit:
            break

    return matches

def get_existing_card(deck_manager, word):
    """Find an exact existing question/name across all decks."""
    normalized_word = normalize(word)

    for card in get_all_cards(deck_manager):
        question = normalize(
            card.get("question", card.get("name", ""))
        )

        if question == normalized_word:
            return card

    return None


# --------------------------------------------------
# SHARED DICTIONARY
# --------------------------------------------------


def get_cached_dictionary_entry(dictionary, word):
    """Read an entry from the extension's shared dictionary."""
    if dictionary is None:
        return None

    try:
        entries = dictionary.load() or {}
        return entries.get(word.lower())
    except Exception:
        return None


def save_dictionary_entry(dictionary, word, phonetic, meaning):
    """Save a new entry into the same dictionary used by the extension."""
    if dictionary is None:
        return

    try:
        dictionary.add_entries({
            word.lower(): {
                "ipa": phonetic or "",
                "meaning": meaning or ""
            }
        })
    except Exception:
        current_app.logger.exception(
            "Could not save word to shared dictionary."
        )


# --------------------------------------------------
# DICTIONARY API
# --------------------------------------------------


def lookup_dictionary(word, dictionary=None):
    """Get Vietnamese translation only."""

    word = word.strip().lower()

    if not word or len(word.split()) != 1:
        return None

    # Check shared dictionary first
    cached = get_cached_dictionary_entry(dictionary, word)

    if cached:
        translation = cached.get("meaning", "").strip()

        if translation:
            return {
                "word": word,
                "translation": translation
            }

    try:
        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": word,
                "langpair": "en|vi",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        translation = data.get(
            "responseData", {}
        ).get("translatedText", "").strip()

        if not translation:
            return None

        # Save to the shared dictionary
        save_dictionary_entry(
            dictionary,
            word,
            "",
            translation,
        )

        return {
            "word": word,
            "translation": translation,
        }

    except requests.RequestException:
        current_app.logger.exception("Translation API failed")
        return None

# --------------------------------------------------
# FLASK APP
# --------------------------------------------------


def create_app(deck_manager, card_manager, dictionary=None):
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
    )

    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    app.config["DECK_MANAGER"] = deck_manager
    app.config["CARD_MANAGER"] = card_manager
    app.config["SHARED_DICTIONARY"] = dictionary

    # ----------------------------------------------
    # INDEX
    # ----------------------------------------------

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    # ----------------------------------------------
    # GET DECKS
    # ----------------------------------------------

    @app.route("/api/decks", methods=["GET"])
    def get_decks():
        decks = deck_manager.repo.get_decks()

        return jsonify(
            [
                {
                    "id": deck.get("id"),
                    "name": deck.get("name", ""),
                }
                for deck in decks
            ]
        )

    # ----------------------------------------------
    # OCR SCAN
    # ----------------------------------------------

    @app.route("/api/scan", methods=["POST"])
    def scan_image():

        uploaded_file = request.files.get("image")

        if uploaded_file is None or not uploaded_file.filename:
            return jsonify({
                "error": "Please take a photo or select an image."
            }), 400

        try:
            image_bytes = uploaded_file.read()

            if not image_bytes:
                return jsonify({
                    "error": "The uploaded image is empty."
                }), 400

            image_array = np.frombuffer(
                image_bytes,
                dtype=np.uint8
            )

            image = cv2.imdecode(
                image_array,
                cv2.IMREAD_COLOR
            )

            if image is None:
                return jsonify({
                    "error": "Could not read the image."
                }), 400

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

            rgb_image = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2RGB
            )

            reader = get_reader()
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
                    "message": "No text detected."
                })

            matches = search_cards(
                deck_manager,
                recognized_text
            )

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
                "error": "OCR processing failed. Check the server console."
            }), 500

    # ----------------------------------------------
    # LOOK UP SELECTED WORD
    # ----------------------------------------------

    @app.route("/api/lookup", methods=["GET"])
    def lookup_word():

        word = request.args.get("word", "").strip()

        if not word or len(word.split()) != 1:
            return jsonify({
                "error": "Please select a single word."
            }), 400

        # Check existing cards first.
        existing_card = get_existing_card(
            deck_manager,
            word
        )

        if existing_card:
            return jsonify({
                "exists": True,
                "card": existing_card,
            })

        # Word does not exist in any deck.
        definition = lookup_dictionary(
            word,
            current_app.config["SHARED_DICTIONARY"]
        )

        if definition is None:
            return jsonify({
                "error": "No dictionary definition or translation found."
            }), 404

        return jsonify({
            "exists": False,
            "definition": definition,
        })

    # ----------------------------------------------
    # ADD WORD TO SELECTED DECK
    # ----------------------------------------------

    @app.route("/api/add-card", methods=["POST"])
    def add_card():
        data = request.get_json(silent=True) or {}

        if not isinstance(data, dict):
            return jsonify({"error": "Invalid request data."}), 400

        word = str(data.get("word", "")).strip().lower()
        deck_id = data.get("deck_id")

        if not word or len(word.split()) != 1:
            return jsonify({"error": "Invalid word."}), 400

        if deck_id is None or str(deck_id).strip() == "":
            return jsonify({"error": "Please select a deck."}), 400

        # Check duplicates across all decks
        existing = get_existing_card(deck_manager, word)

        if existing:
            return jsonify({
                "error": (
                    f"'{word}' already exists in "
                    f"deck '{existing.get('deck', '')}'."
                )
            }), 409

        # Find selected deck
        selected_deck = next(
            (
                deck for deck in deck_manager.repo.get_decks()
                if str(deck.get("id")) == str(deck_id)
            ),
            None
        )

        if selected_deck is None:
            return jsonify({"error": "Selected deck was not found."}), 404

        # Get Vietnamese translation
        definition = lookup_dictionary(
            word,
            current_app.config["SHARED_DICTIONARY"]
        )

        if not definition:
            return jsonify({
                "error": "Could not retrieve Vietnamese translation."
            }), 404

        word = definition["word"]

        try:
            card = card_manager.add_card(
                selected_deck["id"],
                word,
                definition["translation"]
            )

            if card is None:
                return jsonify({"error": "Card creation failed."}), 500

            return jsonify({
                "success": True,
                "message": "Card added successfully.",
                "word": word,
                "translation": definition["translation"],
                "deck": selected_deck.get("name", "")
            })

        except Exception:
            app.logger.exception("Add card failed")

            return jsonify({
                "error": "Failed to save card. Check the server console."
            }), 500
    # ----------------------------------------------
    # UPLOAD ERROR
    # ----------------------------------------------

    @app.errorhandler(413)
    def file_too_large(_error):
        return jsonify({
            "error": "Image is too large. Maximum size is 10 MB."
        }), 413

    return app


# --------------------------------------------------
# START SERVER
# --------------------------------------------------


def start_mobile_server(
    deck_manager,
    card_manager,
    dictionary=None,
    host="0.0.0.0",
    port=7909
):
    """Run Flask in a background thread alongside Tkinter."""
    mobile_app = create_app(
        deck_manager,
        card_manager,
        dictionary,
    )

    thread = threading.Thread(
        target=lambda: mobile_app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        ),
        daemon=True
    )

    thread.start()
    return thread
