from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data" / "storage"
DECKS_DIR = DATA_DIR / "decks"
DB_FILE = DATA_DIR / "test.db"

# Từ điển DÙNG CHUNG cho cả extension lẫn app.
#
# Trước đây file này là 1 từ điển tĩnh ~28MB đi kèm extension. Hiện tại nó đã
# cũ và không còn đúng, nên được chuyển thành **bộ đệm tra cứu tự lớn dần**:
#   - Extension tra cứu theo thứ tự: dict.json -> cache -> Google Translate API
#   - Từ nào dịch qua Google sẽ được ghi lại vào đây (qua POST /add_dict)
#   - App đọc chính file này để nạp từ vựng (xem DeckManager.import_from_dict)
# Nhờ vậy cả hai bên dùng chung 1 từ điển thống nhất, vẫn giữ cấu trúc gốc
# dạng { "từ": { "ipa": "/.../", "meaning": "- nghĩa" } }.
#
# Đường dẫn tương đối từ Flash_Card_App/ ra Browser_Extension/dict.json
DICT_FILE = BASE_DIR.parent / "Browser_Extension" / "dict.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DECKS_DIR.mkdir(parents=True, exist_ok=True)
