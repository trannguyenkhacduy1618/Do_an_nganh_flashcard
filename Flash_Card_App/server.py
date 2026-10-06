"""Cầu nối HTTP giữa Browser Extension (Offline Dictionary) và Flash Card App.

Extension (xem Browser_Extension/background.js) gọi các endpoint sau trên
http://127.0.0.1:5000 :

    GET  /ping          -> kiểm tra app có đang chạy không
    GET  /groups        -> danh sách "group"  (thực chất là Deck của app)
    POST /create_group  -> tạo group/deck mới        body: {"name": "..."}
    POST /save_word     -> lưu 1 thẻ vào group/deck  body: {"word","ipa","meaning","group_id"}
    POST /focus         -> đưa cửa sổ app lên trước

    GET  /dict          -> đọc TỪ ĐIỂN DÙNG CHUNG (Browser_Extension/dict.json)
    POST /add_dict      -> ghi thêm từ mới vào từ điển chung

Điểm quan trọng: server KHÔNG tự lưu dữ liệu riêng. Nó dùng lại đúng
DeckManager / CardManager của app, nên từ vựng lưu từ extension nằm chung
trong data/storage/decks/*.json và tiến độ trong data/storage/test.db.

Từ điển chung (dict.json) là "bộ đệm tra cứu tự lớn dần": extension tra
dict.json trước, không có mới gọi Google Translate, rồi ghi lại kết quả vào
dict.json qua /add_dict. App đọc cùng file đó để nạp từ vựng (xem
DeckManager.import_from_dict), nên hai bên dùng chung một từ điển.
"""

import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from config import DICT_FILE

# Cấu hình cổng cầu nối - phải khớp với background.js của extension
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 5000

# Khi extension lưu thẻ mà chưa chọn group nào -> dùng deck mặc định này
DEFAULT_GROUP_NAME = "Extension"

# Tên deck được dùng làm tên file json nên phải loại bỏ ký tự không hợp lệ
_INVALID_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _safe_deck_name(name):
    """Chuẩn hoá tên group thành tên deck an toàn cho tên file."""
    name = (name or "").strip()
    name = _INVALID_FILENAME.sub("_", name)
    name = name.strip(". ")  # Windows không cho tên kết thúc bằng dấu chấm
    return name[:80] or DEFAULT_GROUP_NAME


class SharedDictionary:
    """Từ điển dùng chung, đọc/ghi trực tiếp Browser_Extension/dict.json.

    Giữ đúng cấu trúc gốc của file:

        { "hello": { "ipa": "/həˈlō/", "meaning": "- xin chào" }, ... }

    Từ mới tra qua Google Translate sẽ được ghi thêm vào đây, nên file tự lớn
    dần theo thời gian thay vì phải kèm sẵn 1 từ điển tĩnh nặng ~28MB.
    """

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self._cache = None

    def load(self):
        """Đọc toàn bộ từ điển (có cache trong RAM)."""
        with self._lock:
            if self._cache is None:
                self._cache = self._read_file()
            return self._cache

    def _read_file(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError) as error:
            print(f"[Bridge] Không đọc được dict ({self.path}): {error}")
            return {}

    def add_entries(self, entries):
        """Ghi thêm nhiều từ vào từ điển. Trả về (số từ mới, tổng số từ)."""
        if not isinstance(entries, dict) or not entries:
            return 0, len(self.load())

        with self._lock:
            if self._cache is None:
                self._cache = self._read_file()

            added = 0
            for word, value in entries.items():
                if not isinstance(word, str) or not word.strip():
                    continue
                if not isinstance(value, dict):
                    continue
                # Không ghi đè từ đã có -> ưu tiên dữ liệu cũ, tránh làm hỏng nghĩa
                if word not in self._cache:
                    self._cache[word] = value
                    added += 1

            if added:
                self._write_file(self._cache)

            return added, len(self._cache)

    def _write_file(self, data):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Ghi ra file tạm rồi thay thế: tránh làm hỏng dict.json nếu bị ngắt giữa chừng
            tmp = self.path.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp.replace(self.path)
        except OSError as error:
            print(f"[Bridge] Không ghi được dict: {error}")


class ApiServer:
    """HTTP server chạy trong thread nền, chia sẻ DeckManager/CardManager với UI."""

    def __init__(
        self,
        deck_manager,
        card_manager,
        on_change=None,
        on_focus=None,
        host=BRIDGE_HOST,
        port=BRIDGE_PORT,
        dictionary=None,
    ):
        self.deck_manager = deck_manager
        self.card_manager = card_manager
        # Callback được gọi (từ thread khác) khi dữ liệu thay đổi
        self.on_change = on_change
        self.on_focus = on_focus
        self.host = host
        self.port = port

        # Từ điển dùng chung với extension.
        # Nhận từ ngoài vào để UI và server dùng CHUNG một instance - nếu mỗi
        # bên tự tạo riêng thì cache trong RAM sẽ lệch nhau, khiến từ mới thêm
        # qua /add_dict không xuất hiện khi app nạp lại dict.
        self.dictionary = dictionary if dictionary is not None else SharedDictionary(DICT_FILE)

        self._httpd = None
        self._thread = None
        # Bảo vệ ghi file json khi có nhiều request cùng lúc
        self._write_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Truy vấn dữ liệu (group <=> deck)
    # ------------------------------------------------------------------

    def _decks(self):
        return self.deck_manager.get_decks()

    def _find_deck_by_id(self, deck_id):
        try:
            deck_id = int(deck_id)
        except (TypeError, ValueError):
            return None
        for deck in self._decks():
            if deck.get("id") == deck_id:
                return deck
        return None

    def _find_deck_by_name(self, name):
        for deck in self._decks():
            if deck.get("name") == name:
                return deck
        return None

    def _get_or_create_deck(self, name):
        name = _safe_deck_name(name)
        deck = self._find_deck_by_name(name)
        if deck:
            return deck
        return self.deck_manager.create_deck(name)

    def list_groups(self):
        return [
            {"id": deck.get("id"), "name": deck.get("name")}
            for deck in self._decks()
        ]

    # ------------------------------------------------------------------
    # Từ điển dùng chung
    # ------------------------------------------------------------------

    def get_dict(self):
        """Toàn bộ từ điển chung (extension dùng để đồng bộ cache)."""
        data = self.dictionary.load()
        return {"success": True, "count": len(data), "dict": data}

    def add_dict(self, entries):
        """Thêm từ mới vào từ điển chung rồi nạp lại vào app."""
        added, total = self.dictionary.add_entries(entries)
        if added:
            # Từ mới cũng trở thành thẻ trong app -> làm mới giao diện
            self._notify()
        return {"success": True, "added": added, "count": total}

    def create_group(self, name):
        deck = self._get_or_create_deck(name)
        if deck is None:
            return None
        self._notify()
        return {"id": deck.get("id"), "name": deck.get("name")}

    def save_word(self, payload):
        """Lưu 1 thẻ (word/ipa/meaning + dữ liệu phong phú) vào group tương ứng."""
        word = (payload.get("word") or "").strip()
        if not word:
            return {"success": False, "error": "Thiếu từ vựng"}

        meaning = (payload.get("meaning") or "").strip()
        ipa = (payload.get("ipa") or "").strip()

        # Gộp IPA + nghĩa thành phần "answer" của thẻ để không mất thông tin
        if ipa and meaning:
            answer = f"{ipa}\n{meaning}"
        else:
            answer = ipa or meaning or "(không có nghĩa)"

        # Dữ liệu phong phú do extension gửi kèm (có thể thiếu -> bỏ qua)
        extra = {}
        if ipa:
            extra["ipa"] = ipa
        for key in ("definitions", "synonyms", "examples"):
            value = payload.get(key)
            if isinstance(value, list) and value:
                extra[key] = value

        with self._write_lock:
            deck = self._find_deck_by_id(payload.get("group_id"))
            if deck is None:
                deck = self._get_or_create_deck(DEFAULT_GROUP_NAME)
            if deck is None:
                return {"success": False, "error": "Không tạo được group"}

            # Tránh thêm trùng thẻ trong cùng 1 deck
            for card in deck.get("cards", []):
                if card.get("question") == word:
                    return {
                        "success": True,
                        "duplicate": True,
                        "deck": deck.get("name"),
                        "card_id": card.get("id"),
                    }

            card = self.card_manager.add_card(deck["id"], word, answer, extra=extra)

        self._notify()
        return {
            "success": True,
            "duplicate": False,
            "deck": deck.get("name"),
            "card_id": card.get("id") if card else None,
        }

    def focus(self):
        if self.on_focus:
            try:
                self.on_focus()
            except Exception as error:  # pragma: no cover - chỉ log
                print("[Bridge] Lỗi focus:", error)

    def _notify(self):
        if self.on_change:
            try:
                self.on_change()
            except Exception as error:  # pragma: no cover - chỉ log
                print("[Bridge] Lỗi thông báo UI:", error)

    # ------------------------------------------------------------------
    # Vòng đời server
    # ------------------------------------------------------------------

    def start(self):
        try:
            self._httpd = _BridgeServer((self.host, self.port), _BridgeHandler)
        except OSError as error:
            print(
                f"[Bridge] Không mở được cổng {self.port}: {error}\n"
                f"[Bridge] App vẫn chạy bình thường, chỉ là extension sẽ "
                f"không kết nối được."
            )
            return False

        self._httpd.api = self
        self._httpd.daemon_threads = True
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="flashcard-bridge",
            daemon=True,
        )
        self._thread.start()
        print(f"[Bridge] Đang lắng nghe tại http://{self.host}:{self.port}")
        return True

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None


class _BridgeServer(ThreadingHTTPServer):
    """ThreadingHTTPServer nhưng không in traceback khi client tự ngắt kết nối.

    Trình duyệt/extension thường huỷ request giữa chừng (đóng popup, timeout),
    gây ConnectionAbortedError - đây là chuyện bình thường, không phải lỗi.
    """

    daemon_threads = True

    def handle_error(self, request, client_address):
        error = sys.exc_info()[1]
        if isinstance(error, (ConnectionError, TimeoutError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


class _BridgeHandler(BaseHTTPRequestHandler):
    server_version = "FlashCardBridge/1.0"

    # Tắt log mặc định cho gọn console
    def log_message(self, fmt, *args):
        return

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    @property
    def api(self):
        return self.server.api

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _path(self):
        return urlparse(self.path).path.rstrip("/") or "/"

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    def do_OPTIONS(self):
        self._send_json({"success": True})

    def do_GET(self):
        path = self._path()

        if path in ("/", "/ping"):
            self._send_json({"success": True, "running": True, "app": "FlashCard App"})
        elif path == "/groups":
            self._send_json({"groups": self.api.list_groups()})
        elif path == "/dict":
            self._send_json(self.api.get_dict())
        else:
            self._send_json({"success": False, "error": "not found"}, 404)

    def do_POST(self):
        path = self._path()
        data = self._read_json()

        if path == "/create_group":
            group = self.api.create_group(data.get("name", ""))
            if group is None:
                self._send_json({"success": False, "error": "Không tạo được group"}, 400)
            else:
                self._send_json({"success": True, "group": group})

        elif path == "/save_word":
            result = self.api.save_word(data)
            self._send_json(result, 200 if result.get("success") else 400)

        elif path == "/add_dict":
            self._send_json(self.api.add_dict(data.get("entries")))

        elif path == "/focus":
            self.api.focus()
            self._send_json({"success": True})

        else:
            self._send_json({"success": False, "error": "not found"}, 404)
