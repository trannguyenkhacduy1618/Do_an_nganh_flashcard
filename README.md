# Do_an_nganh_flashcard

Đồ án ngành Bdu — **Từ điển Offline trên trình duyệt + App Flashcard trên máy tính**.

Hai phần vẫn nằm trong **2 thư mục riêng** và giữ **nguyên giao diện**, nhưng được
nối với nhau qua một **cầu nối HTTP ở cổng 5000**, và **dùng chung một từ điển**
`Browser_Extension/dict.json`:

```
┌─────────────────────────────┐        HTTP (127.0.0.1:5000)        ┌──────────────────────────┐
│   Browser_Extension         │  ──────────────────────────────▶   │   Flash_Card_App         │
│   (Chrome/Edge, MV3)        │   /groups  /create_group           │   (Tkinter + server.py)  │
│   - Bôi đen để tra từ       │   /save_word  /focus               │   - Deck = group         │
│   - Lưu từ vào Flashcard    │   /dict  /add_dict                 │   - Đọc chung dict.json  │
│   - Nút "Mở App"            │  ◀──────────────────────────────   │   - decks/*.json         │
└─────────────────────────────┘        flashcard://open            └──────────────────────────┘
         │                                                                    ▲
         │  ghi từ mới tra qua Google                                         │ đọc & nạp thành thẻ
         └────────────────────▶ Browser_Extension/dict.json ◀────────────────┘
                                (TỪ ĐIỂN DÙNG CHUNG)
```

### Từ điển dùng chung là gì?

`Browser_Extension/dict.json` **không còn là từ điển tĩnh ~28MB** đi kèm extension
(file đó đã cũ và sai). Nó nay là **bộ đệm tra cứu tự lớn dần**:

* Extension tra theo 3 tầng, ưu tiên rẻ nhất:
  1. **`dict.json`** — từ điển chung, tra offline tức thì
  2. **cache** trong `chrome.storage.local` — những từ đã tra trước đây
  3. **Google Translate API** — chỉ gọi khi cả 2 tầng trên đều trống
* Từ nào phải dịch qua Google sẽ được **ghi lại** vào cả `chrome.storage.local`
  và `dict.json` (qua `POST /add_dict`). Lần sau tra từ đó là **offline được ngay**.
* App **đọc chính `dict.json` đó** và biến mỗi từ thành 1 thẻ trong deck
  **"Từ điển"** — nên từ vựng lưu từ extension hiện ra trong app.
* Ngoài `ipa` và `meaning`, mỗi từ còn có thể mang **dữ liệu phong phú** lấy từ
  Google (định nghĩa theo từ loại, từ đồng nghĩa, ví dụ) — xem mục dưới.

### Dữ liệu phong phú (rich data)

Khi tra một **từ tiếng Anh đơn**, extension gọi thêm Google với các tham số
`dt=bd` (từ điển theo từ loại) / `dt=ex` (ví dụ) / `dt=rm` (phiên âm) và lưu vào
`dict.json` thêm 3 khoá **tuỳ chọn** (chỉ ghi khi có dữ liệu):

```json
{
  "volunteer": {
    "ipa": "/ˌvälənˈtir/",
    "meaning": "- chi nguyện quân (Danh từ)\n- tình nguyện (Động từ)",
    "definitions": [
      { "pos": "Danh từ", "definitions": ["a person who freely offers to take part in an enterprise or undertake a task."] },
      { "pos": "Động từ", "definitions": ["freely offer to do something."] }
    ],
    "synonyms": ["blissful", "beatific", "merry", "felicitous"],
    "examples": ["it never paid to volunteer information"]
  }
}
```

* Cấu trúc gốc `{ "từ": { "ipa", "meaning" } }` **vẫn giữ nguyên** — 3 khoá mới
  chỉ được **thêm vào**, nên file cũ vẫn đọc được bình thường.
* **Tất cả** dữ liệu trên chỉ cần **1 request duy nhất** tới Google
  (`dt=t&dt=bd&dt=rm&dt=md&dt=ex`). Trong đó:
  * `data[0]` → bản dịch + **phiên âm** (ô `[i][3]`)
  * `data[1]` → nghĩa tiếng Việt theo từ loại + **từ đồng nghĩa** (danh sách
    "từ nguồn tiếng Anh" ở `block[2][j][1]`, ví dụ `happy` → `blissful`,
    `merry`, `felicitous`…)
  * `data[12]` → **định nghĩa** tiếng Anh theo từ loại (kèm ví dụ gắn định nghĩa)
  * `data[13]` → **câu ví dụ**
* App đọc 3 khoá này và **hiển thị trong thẻ đọc** khi bấm *Show Answer*:
  phiên âm (IPA) dưới câu hỏi, rồi vùng cuộn gồm **ĐỊNH NGHĨA** (theo từ loại),
  **TỪ ĐỒNG NGHĨA** (dạng chip), **VÍ DỤ** (in nghiêng).
* Thẻ cũ không có dữ liệu phong phú vẫn hiển thị y như trước — vùng chi tiết tự ẩn.

> Ghi chú kỹ thuật: endpoint dịch **en→en với `dt=bd`** trước đây từng trả về
> đồng nghĩa, nhưng Google **đã bỏ** (hiện trả mảng rỗng). Vì vậy code **không
> gọi request riêng cho đồng nghĩa nữa** — đồng nghĩa lấy ngay từ `data[1]` của
> response en→vi vốn đã phải gọi. Vừa chính xác hơn, vừa tiết kiệm 1 request.

> Không cần app chạy thì cache vẫn hoạt động. Khi app chạy, cache được ghi tiếp
> vào `dict.json` và app nạp lại ngay (không cần khởi động lại).


---

## 1. Cài đặt (làm 1 lần)

### Bước 1 — Đăng ký protocol `flashcard://` (để extension mở được app)

Nhấp đúp vào **`install_protocol.bat`** ở thư mục gốc, hoặc chạy:

```bat
python install_protocol.py
```

Script chỉ ghi vào `HKEY_CURRENT_USER` nên **không cần quyền Administrator**.
Muốn gỡ: `python install_protocol.py --uninstall`

### Bước 2 — Load extension vào trình duyệt

1. Mở `chrome://extensions` (hoặc `edge://extensions`)
2. Bật **Developer mode**
3. Bấm **Load unpacked** → chọn thư mục **`Browser_Extension`**

---

## 2. Sử dụng

### Mở App

Bấm **icon extension** trên thanh công cụ → bấm **"Mở Flashcard App"**.

* App đang chạy → cửa sổ app được đưa lên trước.
* App chưa chạy → tự chạy `Flash_Card_App/run_app.bat` (tức `python main.py`).
  Trình duyệt sẽ hỏi *"Open Flashcard App?"* → bấm **Open**.

> Cũng có thể mở app thủ công: nhấp đúp `Flash_Card_App/run_app.bat`,
> hoặc `cd Flash_Card_App && python main.py`.

### Tra từ & lưu vào Flashcard

1. Bôi đen một từ/cụm từ trên bất kỳ trang web nào → popup hiện ra.
   Nhãn nguồn cho biết từ lấy ở đâu:
   * **Offline** — có sẵn trong `dict.json`
   * **Đã lưu** — đã tra trước đây, nằm trong cache
   * **Google** — từ mới, vừa gọi API (và sẽ được ghi lại để lần sau tra offline)
2. Popup hiện **phiên âm + nghĩa**, kèm các khối **ĐỊNH NGHĨA · <từ loại>**,
   **TỪ ĐỒNG NGHĨA**, **VÍ DỤ** nếu Google trả về (chỉ với từ tiếng Anh đơn).
3. Chọn **nhóm (deck)** ở ô dropdown, hoặc bấm **+** để tạo nhóm mới.
4. Bấm **"+ Lưu vào Flashcard"** → thẻ được ghi thẳng vào app, **kèm cả dữ liệu
   phong phú** (định nghĩa / đồng nghĩa / ví dụ) để app hiển thị lại khi học.
5. Nếu app chưa chạy, popup hiện nút **"Mở Flashcard App"** để bật app ngay.

Trong app, thẻ vừa lưu xuất hiện ở màn hình **Decks** / **Browse** (tự làm mới).

### Quản lý từ điển chung

Toàn bộ giao diện nằm ở **popup bôi đen** — không có popup riêng trên thanh công cụ.
Bôi đen một từ bất kỳ, popup hiện ra cho biết:

* **nhãn nguồn** — `Offline` / `Đã lưu` / `Google`
* ô **chọn nhóm** + nút **+** tạo nhóm, và nút **+ Lưu vào Flashcard**
* nút **Mở Flashcard App** khi app chưa chạy

Để xem/đồng bộ từ điển, mở `Browser_Extension/dict.json` trực tiếp — đây là file
dùng chung, thêm từ vào đây thì cả extension lẫn app đều đọc được.

### Đồng bộ hai chiều (dict.json ⇄ cache)

`dict.json` là **nguồn sự thật** (source of truth) và **giữ nguyên sau khi tắt app**.
Để tránh mất từ khi lưu lúc app chưa chạy, extension đồng bộ theo **hai chiều**:

| Hướng | Cơ chế | Khi nào chạy |
| ----- | ------ | ------------ |
| `dict.json` → cache | `SYNC_DICT` | mỗi lần nạp từ điển |
| cache → `dict.json` | `FLUSH_CACHE_TO_DICT` | khi phát hiện app đang chạy (và khi content script nạp) |

* Khi bạn tra/save một từ, extension **luôn** ghi vào `chrome.storage.local`.
  Nếu app **đang chạy**, nó ghi thẳng vào `dict.json` ngay. Nếu app **chưa chạy**,
  từ nằm tạm trong cache.
* Ngay khi app **bật lên** (content script phát hiện `/ping` thành công),
  `FLUSH_CACHE_TO_DICT` đẩy mọi từ trong cache **còn thiếu** trong `dict.json`
  sang `POST /add_dict` → `dict.json` được cập nhật, và **giữ nguyên** sau khi
  tắt app.
* `loadDictionary()` đọc từ **app trước** (`GET /dict`) rồi mới tới file đóng gói
  trong extension — nên không bao giờ đọc phải bản snapshot cũ.
* `/add_dict` **không ghi đè** từ đã có → chạy lại flush nhiều lần vẫn an toàn,
  không sinh trùng lặp.

---

## 3. Cấu trúc thư mục

```
Do_an_nganh_flashcard-main/
├── Browser_Extension/          # Extension (giao diện nằm ở popup bôi đen)
│   ├── manifest.json
│   ├── background.js           # tra 3 tầng + ghi dict + gọi API cổng 5000
│   ├── content.js              # popup bôi đen: tra từ, lưu thẻ, mở app
│   └── dict.json               # ★ TỪ ĐIỂN DÙNG CHUNG (tự lớn dần)
│
├── Flash_Card_App/             # App Tkinter (giữ nguyên giao diện)
│   ├── main.py                 # + khởi động bridge, nạp dict, single-instance
│   ├── server.py               # ★ CẦU NỐI HTTP + quản lý dict dùng chung
│   ├── run_app.bat             # chạy app (được protocol flashcard:// gọi)
│   ├── config.py               # DICT_FILE trỏ sang Browser_Extension/dict.json
│   ├── data/  logic/  ui/
│
├── install_protocol.py         # đăng ký / gỡ flashcard://
└── install_protocol.bat        # nhấp đúp để cài
```

---

## 4. API của cầu nối (cổng 5000)

| Method | Endpoint        | Body                                      | Trả về                          |
|--------|-----------------|-------------------------------------------|---------------------------------|
| GET    | `/ping`         | –                                         | `{success, running}`            |
| GET    | `/groups`       | –                                         | `{groups: [{id, name}]}`        |
| POST   | `/create_group` | `{name}`                                  | `{group: {id, name}}`           |
| POST   | `/save_word`    | `{word, ipa, meaning, definitions, synonyms, examples, group_id}` | `{success, deck, card_id}` |
| POST   | `/focus`        | –                                         | `{success}`                     |
| GET    | `/dict`         | –                                         | `{count, dict: {từ: {...}}}`    |
| POST   | `/add_dict`     | `{entries: {từ: {ipa, meaning, definitions?, synonyms?, examples?}}}` | `{added, count}` |

`definitions` / `synonyms` / `examples` là **tuỳ chọn** — vắng mặt thì thẻ chỉ có
`ipa` + `meaning` như trước.

Chi tiết xem `Flash_Card_App/server.py`.

---

## 5. Ghi chú

* Cổng **5000** được hard-code trong cả `server.py` và `background.js`
  (`BRIDGE_PORT` / `API_BASE`). Đổi cổng thì phải sửa cả hai chỗ.
* `server.py` chỉ dùng thư viện chuẩn Python (`http.server`) — **không cần pip install**.
* Nếu cổng 5000 bị chiếm, app vẫn mở bình thường, chỉ là extension không kết nối được
  (xem log ở cửa sổ console).
* `/add_dict` **không ghi đè** từ đã có → chạy lại nhiều lần vẫn an toàn, nghĩa cũ
  không bị thay bằng dữ liệu rác.
* Deck **"Từ điển"** trong app chỉ **thêm** thẻ mới, không sửa/xoá thẻ cũ → tiến độ
  học trong `test.db` không bị mất.
* Từ do Google trả về **rỗng** sẽ bị bỏ qua, không ghi vào `dict.json` — tránh tạo ra
  entry rác kiểu `{"ipa": "", "meaning": "-"}`.
* Dữ liệu phong phú (định nghĩa/đồng nghĩa/ví dụ) có thể vắng với một số từ —
  khi đó thẻ chỉ hiện `ipa` + `meaning`, không có vùng chi tiết.
* App **tương thích ngược**: thẻ cũ thiếu `definitions`/`synonyms`/`examples` vẫn
  hiển thị đúng, vùng chi tiết tự ẩn thay vì hiện khung rỗng.
* Việc tra từ có **chống race**: nếu bạn bôi đen liên tiếp nhiều lần, kết quả của lần
  cũ về muộn sẽ bị bỏ, không ghi nhầm từ vào từ điển.
* File `manifest.json` ở thư mục gốc là file cũ, **không dùng** — manifest thật nằm ở
  `Browser_Extension/manifest.json`.
* **Mẹo**: nếu bạn tra/lưu từ trong lúc app **chưa chạy**, từ đó nằm trong cache của
  extension. Chỉ cần **mở app lên** (hoặc tải lại trang) là extension tự đẩy sang
  `dict.json` — không cần thao tác gì thêm. `dict.json` giữ nguyên thay đổi đó
  **kể cả sau khi tắt app**.
