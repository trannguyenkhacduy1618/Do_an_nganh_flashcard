import queue
import urllib.request

import tkinter as tk

from ui.main_window import MainWindow

from data.json_repository import JsonRepository
from data.database import Database

from logic.deck_manager import DeckManager
from logic.card_manager import CardManager

from config import DB_FILE, DECKS_DIR, DICT_FILE
from server import ApiServer, SharedDictionary, BRIDGE_HOST, BRIDGE_PORT


class UiBridge:
    """Cho phép thread của HTTP server yêu cầu main thread cập nhật giao diện.

    Tkinter không thread-safe, nên mọi thao tác lên widget phải được đẩy
    vào queue và thực thi trên main thread qua root.after().
    """

    def __init__(self, root, interval=150):
        self.root = root
        self.interval = interval
        self._queue = queue.Queue()
        self._poll()

    def _poll(self):
        try:
            while True:
                callback = self._queue.get_nowait()
                try:
                    callback()
                except Exception as error:  # pragma: no cover - chỉ log
                    print("[Bridge] Lỗi cập nhật UI:", error)
        except queue.Empty:
            pass
        self.root.after(self.interval, self._poll)

    def post(self, callback):
        self._queue.put(callback)


def _another_instance_running():
    """Kiểm tra xem app đã chạy sẵn chưa (qua cổng cầu nối)."""
    try:
        url = f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/ping"
        with urllib.request.urlopen(url, timeout=0.6) as response:
            return response.status == 200
    except Exception:
        return False


def _focus_existing_instance():
    try:
        url = f"http://{BRIDGE_HOST}:{BRIDGE_PORT}/focus"
        request = urllib.request.Request(
            url,
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(request, timeout=0.6).read()
    except Exception:
        pass


def main():
    # Nếu app đang chạy -> chỉ đưa cửa sổ cũ lên trước, không mở thêm cửa sổ mới.
    # (Nhờ vậy bấm "Mở App" trên extension nhiều lần vẫn an toàn.)
    if _another_instance_running():
        _focus_existing_instance()
        return

    database = Database(str(DB_FILE))
    json_repo = JsonRepository(str(DECKS_DIR))

    database.initialize()

    deck_manager = DeckManager(json_repo)
    card_manager = CardManager(
        json_repo,
        database
    )

    # Từ điển dùng chung với extension (Browser_Extension/dict.json).
    # Nạp từ có sẵn trong dict vào app ngay lúc khởi động.
    shared_dict = SharedDictionary(DICT_FILE)

    def sync_dict_into_app():
        """Đọc dict.json và thêm các từ MỚI vào deck 'Từ điển' của app."""
        dict_data = shared_dict.load()
        added, total, deck_name = deck_manager.import_from_dict(dict_data)
        if added:
            print(f"[Dict] Đã nạp {added} từ mới từ dict.json -> deck '{deck_name}' ({total} thẻ)")
        return added

    sync_dict_into_app()

    root = tk.Tk()

    root.title("User 1 - Anki")
    root.geometry("820x760")
    root.minsize(300, 500)

    app = MainWindow(
        root,
        deck_manager,
        card_manager,
        database
    )

    # Cầu nối UI: server chạy ở thread khác sẽ đẩy việc cập nhật vào đây
    ui_bridge = UiBridge(root)

    def on_external_change():
        """Extension vừa lưu từ mới -> nạp thêm vào app rồi làm mới màn hình."""
        sync_dict_into_app()
        ui_bridge.post(app.refresh_current_view)

    def on_external_focus():
        """Extension yêu cầu đưa app lên trước."""
        ui_bridge.post(app.focus_window)

    server = ApiServer(
        deck_manager,
        card_manager,
        on_change=on_external_change,
        on_focus=on_external_focus,
        # Dùng CHUNG instance với UI: nếu để server tự tạo instance riêng thì
        # cache RAM của hai bên lệch nhau và từ mới thêm qua /add_dict sẽ không
        # được nạp lại vào app.
        dictionary=shared_dict,
    )
    server.start()

    def on_close():
        server.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()


if __name__ == "__main__":
    main()
