
import re
import threading
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
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


def search_cards_and_words(deck_manager, recognized_text, limit=10):
    """Find display cards and all matching OCR words in one deck pass."""
    cards = get_all_cards(deck_manager)
    recognized_words = set(normalize(recognized_text).split())
    matches = []
    deck_words = set()

    for card in cards:
        question = normalize(
            card.get("question", card.get("name", ""))
        )
        question_words = set(question.split())
        deck_words.update(question_words)

        if recognized_words.intersection(question_words) and len(matches) < limit:
            matches.append(card)

    matched_words = sorted(recognized_words.intersection(deck_words))
    return matches, matched_words

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


@lru_cache(maxsize=512)
def translate_to_vietnamese(text):
    """Translate a short English phrase to Vietnamese."""
    text = str(text or "").strip()
    if not text:
        return ""

    try:
        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text[:450], "langpair": "en|vi"},
            timeout=3.5,
        )
        response.raise_for_status()
        data = response.json()
        return (
            data.get("responseData", {})
            .get("translatedText", "")
            .strip()
        )
    except (requests.RequestException, ValueError, AttributeError):
        return ""


@lru_cache(maxsize=512)
def _fetch_dictionary_entry(word):
    """Fetch English dictionary data."""
    response = requests.get(
        f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word)}",
        headers={"User-Agent": "FlashcardScanner/1.0"},
        timeout=5,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    entries = response.json()
    return entries[0] if isinstance(entries, list) and entries else None


@lru_cache(maxsize=256)
def _fetch_wikipedia_summary(word):
    """Fetch optional Wikipedia explanation and thumbnail."""
    try:
        response = requests.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(word),
            headers={"User-Agent": "FlashcardScanner/1.0"},
            timeout=2.5,
        )
        if not response.ok:
            return {}, ""
        data = response.json()
        return data, data.get("extract", "") or ""
    except (requests.RequestException, ValueError, AttributeError):
        return {}, ""


def lookup_dictionary(word, dictionary=None):
    """Return a temporary structured result; never save it to a deck."""
    word = str(word or "").strip()
    if not word or len(word.split()) != 1:
        return None

    try:
        # Fetch dictionary and Wikipedia data at the same time.
        with ThreadPoolExecutor(max_workers=2) as pool:
            dictionary_future = pool.submit(_fetch_dictionary_entry, word)
            wikipedia_future = pool.submit(_fetch_wikipedia_summary, word)
            entry = dictionary_future.result()
            wiki, wikipedia_summary = wikipedia_future.result()

        if not entry:
            return None

        meanings = entry.get("meanings", [])
        pronunciation = entry.get("phonetic", "") or ""
        for phonetic in entry.get("phonetics", []):
            if phonetic.get("text"):
                pronunciation = phonetic["text"]
                break

        part_of_speech = ""
        english_definition = ""
        example_text = ""
        synonyms = []

        for meaning in meanings:
            if not part_of_speech:
                part_of_speech = meaning.get("partOfSpeech", "")
            for item in meaning.get("definitions", []):
                if not english_definition and item.get("definition"):
                    english_definition = item["definition"].strip()
                if not example_text and item.get("example"):
                    example_text = item["example"].strip()
                synonyms.extend(item.get("synonyms", []))
            synonyms.extend(meaning.get("synonyms", []))

        if not english_definition:
            return None

        # Translate all visible text concurrently instead of waiting for each
        # translation request one by one. Limit the Wikipedia text for speed.
        short_wiki_summary = wikipedia_summary[:450]
        with ThreadPoolExecutor(max_workers=4) as pool:
            headword_future = pool.submit(translate_to_vietnamese, word)
            definition_future = pool.submit(
                translate_to_vietnamese, english_definition
            )
            example_future = pool.submit(
                translate_to_vietnamese, example_text
            )
            how_future = pool.submit(
                translate_to_vietnamese, short_wiki_summary
            ) if short_wiki_summary else None

            headword_translation = headword_future.result()
            definition_translation = definition_future.result()
            example_translation = example_future.result()
            how_it_works_vi = how_future.result() if how_future else ""

        definition = english_definition
        if definition_translation:
            definition = f"{definition_translation}\n\n{english_definition}"

        related_terms = list(dict.fromkeys(
            str(item).strip() for item in synonyms if str(item).strip()
        ))[:12]

        images = []
        links = [
            {
                "title": "Nguồn từ điển (Dictionary API)",
                "url": "https://api.dictionaryapi.dev/api/v2/entries/en/"
                + quote(word),
            },
            {
                "title": f"Tìm tài liệu chính thức về {word}",
                "url": "https://www.google.com/search?q="
                + quote(word + " official documentation"),
            },
            {
                "title": f"Tìm kiếm Wikipedia: {word}",
                "url": "https://en.wikipedia.org/w/index.php?search="
                + quote(word),
            },
        ]

        thumbnail = wiki.get("thumbnail", {}).get("source")
        if thumbnail:
            images.append({"title": f"Hình minh họa: {word}", "url": thumbnail})
        wiki_url = wiki.get("content_urls", {}).get("desktop", {}).get("page")
        if wiki_url:
            links.append({"title": "Bài viết Wikipedia", "url": wiki_url})

        return {
            "id": None,
            "question": entry.get("word", word),
            "word": entry.get("word", word),
            "answer": headword_translation or "Chưa có bản dịch",
            "translation": headword_translation or "Chưa có bản dịch",
            "pronunciation": pronunciation,
            "part_of_speech": part_of_speech,
            "definition": definition,
            "example": {
                "text": example_text,
                "translation": example_translation,
            },
            "how_it_works": how_it_works_vi or (
                f"{definition_translation}\n\n"
                "Đây là phần giải thích ngắn dựa trên định nghĩa của thuật ngữ."
                if definition_translation else
                "Chưa tìm thấy phần giải thích tiếng Việt cho thuật ngữ này."
            ),
            "applications": [],
            "related_terms": related_terms,
            "common_mistakes": [],
            "images": images,
            "links": links,
            "deck": "Kết quả trực tuyến (chưa lưu)",
        }

    except (requests.RequestException, ValueError, TypeError, KeyError):
        current_app.logger.exception(
            "Online dictionary lookup failed for %s", word
        )
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

            matches, matched_words = search_cards_and_words(
                deck_manager,
                recognized_text
            )

            return jsonify({
                "text": recognized_text,
                "matches": matches,
                "matched_words": matched_words,
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
