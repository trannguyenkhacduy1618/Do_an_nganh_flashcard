// ============================================================
// Offline Dictionary - Service Worker
//
// NHIỆM VỤ
//  1. TRA TỪ theo 3 tầng, ưu tiên rẻ nhất:
//        ① dict.json        - từ điển dùng chung với app (đĩa, không cần mạng)
//        ② cache đã tra      - chrome.storage.local (những từ đã gặp)
//        ③ Google Translate  - chỉ gọi khi 2 tầng trên đều trống
//
//  2. TỪ MỚI dịch qua Google sẽ được GHI LẠI để lần sau tra offline được:
//        - vào chrome.storage.local  -> có hiệu lực ngay, không cần app
//        - gửi lên POST /add_dict    -> ghi vào dict.json, app đọc chung
//     Nếu app không chạy thì bỏ qua bước 2, cache vẫn giữ và sẽ đồng bộ sau.
//
//  3. Lưu từ vựng vào Flashcard App qua HTTP cổng 5000.
//
// GHI CHÚ LỊCH SỬ (đã cũ, giữ lại để đối chiếu)
//  - Bản gốc kèm sẵn 1 file dict.json ~28MB tải hết vào RAM mỗi lần khởi động.
//    File đó nay đã cũ/sai và đã bị lược bỏ. Vì vậy dùng chrome.storage.local
//    làm cache thay vì nhồi tất cả vào biến trong bộ nhớ.
//  - Bản gốc có gán `dictionaryData[text] = newEntry` nhưng KHÔNG BAO GIỜ ghi
//    ra đâu cả -> từ mới mất sạch khi service worker ngủ. Đã sửa bằng
//    `chrome.storage.local.set` + `POST /add_dict`.
// ============================================================

const API_BASE = "http://127.0.0.1:5000";
const CACHE_KEY = "dictCache";

// ============================================================
// TẦNG 1: dict.json - từ điển dùng chung với app
// ============================================================

let dictionaryData = null;
let dictLoadPromise = null;

// Đọc dict.json đi kèm extension (bản đóng gói lúc cài).
function _readPackagedDict() {
  return fetch(chrome.runtime.getURL("dict.json"))
    .then((response) => response.json())
    .catch(() => ({}));
}

// Đọc dict MỚI NHẤT từ app (GET /dict) - đây mới là bản app ghi thêm từ vào.
// Trả về null nếu app không chạy.
function _readDictFromApp() {
  return fetch(API_BASE + "/dict")
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => (data && data.dict && typeof data.dict === "object" ? data.dict : null))
    .catch(() => null);
}

// Khởi tạo Promise để chỉ đọc 1 lần, mọi lần tra sau dùng lại.
//
// LƯU Ý: file dict.json đi kèm extension chỉ là bản CHỤP LÚC CÀI. App ghi từ
// mới vào FILE TRÊN ĐĨA, nên bản đóng gói có thể cũ hơn. Vì vậy ưu tiên hỏi
// app (GET /dict); app không chạy thì mới dùng bản đóng gói.
function loadDictionary() {
  if (!dictLoadPromise) {
    dictLoadPromise = _readDictFromApp().then((fromApp) => {
      if (fromApp) {
        dictionaryData = fromApp;
        return dictionaryData;
      }
      return _readPackagedDict().then((data) => {
        dictionaryData = data && typeof data === "object" ? data : {};
        return dictionaryData;
      });
    });
  }
  return dictLoadPromise;
}

// Buộc nạp lại dict.json (dùng sau khi biết app vừa ghi thêm từ).
// Trả về true nếu lấy được bản mới từ app.
function reloadDictionary() {
  return _readDictFromApp().then((fromApp) => {
    if (fromApp) {
      dictionaryData = fromApp;
      // Cập nhật cả promise đã cache để các lần loadDictionary sau dùng bản mới.
      dictLoadPromise = Promise.resolve(dictionaryData);
      return true;
    }
    return false;
  });
}

// ============================================================
// TẦNG 2: cache trong chrome.storage.local (từ mới đã tra)
// ============================================================

function loadCache() {
  return new Promise((resolve) => {
    chrome.storage.local.get(CACHE_KEY, (result) => {
      const cache = result && result[CACHE_KEY];
      resolve(cache && typeof cache === "object" ? cache : {});
    });
  });
}

function saveToCache(word, entry) {
  return loadCache().then((cache) => {
    cache[word] = entry;
    return new Promise((resolve) => {
      chrome.storage.local.set({ [CACHE_KEY]: cache }, resolve);
    });
  });
}

// Gửi từ mới lên app để ghi vào dict.json (app đọc chung file này).
// App không chạy -> bỏ qua êm, cache vẫn đã giữ từ đó.
function pushToSharedDict(word, entry) {
  return fetch(API_BASE + "/add_dict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entries: { [word]: entry } }),
  })
    .then((res) => (res.ok ? res.json() : null))
    .catch(() => null);
}

// ============================================================
// BÓC TÁCH DỮ LIỆU TỪ GOOGLE TRANSLATE
//
// Response của endpoint translate_a/single là mảng không có nhãn, vị trí các
// phần phụ thuộc vào tham số `dt=` đã gửi. Cấu trúc (với dt=t,rm,bd,md,ex):
//
//   data[0]  -> các đoạn dịch; data[0][i][2]/[3] là phiên âm
//   data[1]  -> từ điển theo từ loại: [ [pos, [nghĩa...], ..., ] , ... ]
//   data[12] -> định nghĩa gốc (Oxford): [ [pos, [[định nghĩa, id], ...]], ... ]
//   data[13] -> câu ví dụ: [ [ [câu có <b>từ</b>, ...] ] ]
//
// Vì đây là API không chính thức, mọi truy cập đều phải phòng thủ: chỉ số có
// thể thiếu, phần tử có thể null. Không bao giờ giả định là có.
// ============================================================

// Dịch nhãn từ loại sang tiếng Việt cho dễ đọc khi học
const POS_VI = {
  noun: "Danh từ",
  verb: "Động từ",
  adjective: "Tính từ",
  adverb: "Trạng từ",
  pronoun: "Đại từ",
  preposition: "Giới từ",
  conjunction: "Liên từ",
  interjection: "Thán từ",
  exclamation: "Thán từ",
  determiner: "Hạn định từ",
  numeral: "Số từ",
  article: "Mạo từ",
  abbreviation: "Viết tắt",
  prefix: "Tiền tố",
  suffix: "Hậu tố",
};

function posLabel(pos) {
  if (!pos) return "";
  const key = String(pos).toLowerCase().trim();
  return POS_VI[key] || pos;
}

// Bỏ thẻ HTML (<b>, </b>) mà Google chèn vào câu ví dụ
function stripTags(html) {
  return String(html || "").replace(/<[^>]*>/g, "").trim();
}

function parseTranslateResponse(data) {
  // ---- 1. Bản dịch ----
  const meaning = data[0]
    .map((item) => item && item[0])
    .filter(Boolean)
    .join("")
    .trim();

  // ---- 2. Phiên âm (IPA) ----
  // Google trả về dạng: data[0] = [
  //     ["nghĩa", "từ gốc", null, null, 10],
  //     [null,    null,      null, "ˈjərnē"]        <-- IPA nằm ở index 3
  // ]
  // Thực tế index 3 mới chứa IPA (index 2 gần như luôn null), NHƯNG để chắc chắn
  // ta chọn ô nào "trông giống IPA" (có ký tự phiên âm) thay vì index cứng —
  // Google có thể đổi vị trí bất cứ lúc nào.
  const IPA_HINT = /[/ˈˌəɪʊɛɔæɑʌθðʃʒŋɜɚɝʤʧɹɾɲɟɡʼˈˌː]/;
  let ipa = "";
  for (const part of data[0]) {
    if (!Array.isArray(part)) continue;
    for (let k = 2; k <= 3; k++) {
      const v = part[k];
      if (typeof v === "string" && v.trim()) {
        const s = v.trim();
        // Ưu tiên giá trị trông giống IPA; nếu chưa có gì thì nhận tạm.
        if (!ipa || (!IPA_HINT.test(ipa) && IPA_HINT.test(s))) ipa = s;
      }
    }
  }
  ipa = ipa ? "/" + ipa.replace(/^\/+|\/+$/g, "") + "/" : "";

  // ---- 3. Từ điển theo từ loại (data[1]) ----
  // Mỗi phần tử: [pos, [nghĩa tiếng Việt...], [[nghĩa, [từ nguồn tiếng Anh]], ...], từ gốc, index]
  //
  // block[1] = NGHĨA tiếng Việt.
  // block[2][i][1] = các TỪ TIẾNG ANH cùng góp vào nghĩa đó -> đây là nguồn
  // đồng nghĩa đáng tin cậy (và miễn phí, vì nằm ngay trong response này).
  // Ví dụ "happy" -> meaning "hạnh phúc" -> ["happy","blissful","beatific","merry",...]
  const posBlocks = [];
  const synonymSeen = new Set();
  const synonyms = [];
  const baseWord = String(data[0] && data[0][0] && data[0][0][1] || "").toLowerCase().trim();

  const dictSection = Array.isArray(data[1]) ? data[1] : [];
  for (const block of dictSection) {
    if (!Array.isArray(block)) continue;

    const pos = posLabel(block[0]);
    const meanings = Array.isArray(block[1]) ? block[1].filter(Boolean) : [];

    if (meanings.length) {
      posBlocks.push({ pos, meanings });
    }

    // Gom từ nguồn tiếng Anh làm đồng nghĩa, bỏ chính từ gốc và từ trùng.
    for (const group of Array.isArray(block[2]) ? block[2] : []) {
      if (!Array.isArray(group) || !Array.isArray(group[1])) continue;
      for (const src of group[1]) {
        if (typeof src !== "string") continue;
        const s = src.trim();
        if (!s || s.toLowerCase() === baseWord) continue;
        const key = s.toLowerCase();
        if (synonymSeen.has(key)) continue;
        synonymSeen.add(key);
        synonyms.push(s);
      }
    }
  }

  // ---- 4. Định nghĩa gốc (data[12]) ----
  // Mỗi phần tử: [pos, [[định nghĩa, id, câu ví dụ], ...], từ gốc, index]
  // item[0] = định nghĩa; item[2] = câu ví dụ gắn với định nghĩa đó.
  const definitions = [];
  const defExamples = [];
  const defSection = Array.isArray(data[12]) ? data[12] : [];
  for (const block of defSection) {
    if (!Array.isArray(block)) continue;

    const pos = posLabel(block[0]);
    const defs = [];
    for (const item of Array.isArray(block[1]) ? block[1] : []) {
      if (!Array.isArray(item)) continue;
      if (item[0]) {
        const text = String(item[0]).trim();
        if (text) defs.push(text);
      }
      if (typeof item[2] === "string" && item[2].trim()) {
        const ex = stripTags(item[2]);
        if (ex) defExamples.push(ex);
      }
    }
    if (defs.length) definitions.push({ pos, definitions: defs });
  }

  // ---- 5. Câu ví dụ (data[13]) ----
  // data[13] là nguồn ví dụ chính; nếu vắng thì lấy ví dụ gắn với định nghĩa.
  const examples = [];
  const exSection = Array.isArray(data[13]) ? data[13] : [];
  for (const group of exSection) {
    if (!Array.isArray(group)) continue;
    for (const item of group) {
      if (Array.isArray(item) && item[0]) {
        const text = stripTags(item[0]);
        if (text && !examples.includes(text)) examples.push(text);
      }
    }
  }
  for (const ex of defExamples) {
    if (!examples.includes(ex)) examples.push(ex);
  }

  // ---- 6. Gộp nghĩa ----
  // Giữ trường `meaning` dạng chuỗi như cũ (tương thích ngược với dict cũ),
  // đồng thời thêm `pos` để biết nghĩa nào thuộc từ loại nào.
  let meaningText = "- " + meaning;
  if (posBlocks.length) {
    const flat = [];
    for (const block of posBlocks) {
      for (const m of block.meanings) {
        flat.push(block.pos ? `${m} (${block.pos})` : m);
      }
    }
    if (flat.length) meaningText = flat.map((m) => "- " + m).join("\n");
  }

  return {
    ipa,
    meaning: meaningText,
    // Các trường mở rộng - dict cũ không có, app phải đọc phòng thủ
    definitions,
    synonyms: synonyms.slice(0, 12), // lấy từ block[2] của data[1] (xem mục 3)
    examples: examples.slice(0, 5),
  };
}

// ============================================================
// TỪ ĐỒNG NGHĨA
//
// LƯU Ý (đã kiểm chứng): endpoint dịch en->en với dt=bd trước đây từng trả về
// danh sách đồng nghĩa, nhưng Google ĐÃ BỎ — hiện gọi chỉ trả về mảng rỗng.
// Vì vậy KHÔNG còn request riêng cho đồng nghĩa.
//
// Thay vào đó, đồng nghĩa được lấy ngay trong parseTranslateResponse() từ
// data[1][i][2][j][1] (danh sách "từ nguồn tiếng Anh" của bản dịch en->vi).
// Vừa chính xác hơn, vừa tiết kiệm 1 request.
// ============================================================

// ============================================================
// TRA TỪ 3 TẦNG
// ============================================================

// Chống race: mỗi lần bôi đen tăng số này. Response về muộn của lần
// bôi đen TRƯỚC sẽ bị bỏ, không ghi từ sai vào từ điển.
let lookupSeq = 0;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // ==========================================
  // LUỒNG 1: TRA TỪ (dict.json -> cache -> Google)
  // ==========================================
  if (request.action === "LOOKUP") {
    const seq = ++lookupSeq;
    const text = request.word.toLowerCase().trim();

    // Từ đã tra xong, kết quả không còn mới nhất -> trả luôn kết quả cũ
    // (vẫn đúng nội dung) nhưng KHÔNG ghi vào từ điển.
    const isStale = () => seq !== lookupSeq;

    Promise.all([loadDictionary(), loadCache()]).then(([dictFile, cache]) => {
      // --- Tầng 1: từ điển chung ---
      if (dictFile && dictFile[text]) {
        sendResponse({ success: true, source: "Offline", data: dictFile[text] });
        return;
      }

      // --- Tầng 2: cache những từ đã tra trước đây ---
      if (cache && cache[text]) {
        sendResponse({ success: true, source: "Đã lưu", data: cache[text] });
        return;
      }

      // --- Tầng 3: Google Translate (chỉ cho từ mới) ---
      // dt=t  : bản dịch
      // dt=rm : phiên âm (IPA)
      // dt=bd : từ điển theo từ loại
      // dt=md : định nghĩa gốc (Oxford)
      // dt=ex : câu ví dụ
      const url =
        "https://translate.googleapis.com/translate_a/single" +
        `?client=gtx&sl=auto&tl=vi&dt=t&dt=rm&dt=bd&dt=md&dt=ex&q=${encodeURIComponent(text)}`;

      // Chỉ 1 request: bản dịch + phiên âm + định nghĩa + đồng nghĩa + ví dụ
      // đều nằm trong cùng response này (xem parseTranslateResponse).
      fetch(url)
        .then((res) => res.json())
        .then((data) => {
          if (isStale()) return;

          if (!data || !Array.isArray(data[0])) {
            sendResponse({ success: false });
            return;
          }

          const parsed = parseTranslateResponse(data);

          // Google đôi khi trả rỗng (bị chặn tạm, từ quá lạ, ký tự đặc biệt).
          // Ghi vào từ điển lúc này sẽ tạo ra thẻ rác kiểu "meaning: '-'".
          if (!parsed.meaning) {
            sendResponse({ success: false });
            return;
          }

          const newEntry = parsed;
          const isWordOrPhrase = text.length <= 25;

          // Từ / cụm từ ngắn (<= 25 ký tự) được lưu để lần sau tra offline.
          // Cụm 2-3 từ như "volunteer editors" vẫn là từ vựng hợp lệ -> phải lưu.
          // Chỉ bỏ qua CÂU DÀI, vì lưu câu vào từ điển là vô nghĩa.
          if (isWordOrPhrase) {
            saveToCache(text, newEntry);
            pushToSharedDict(text, newEntry);
          }

          sendResponse({
            success: true,
            source: isWordOrPhrase ? "Google" : "Google (Câu dài)",
            data: newEntry,
          });
        })
        .catch(() => {
          // Bỏ qua lỗi Google Translate gọn gàng, không để bị treo
          if (!isStale()) sendResponse({ success: false });
        });
    });

    return true; // Giữ cổng kết nối chờ xử lý bất đồng bộ
  }

  // ==========================================
  // LUỒNG 2, 3, 4: CHUYỂN SANG IP 127.0.0.1 ĐỂ TRÁNH LỖI MẠNG
  // (đây là cầu nối HTTP do Flash Card App mở ở cổng 5000)
  // ==========================================
  if (request.action === "GET_GROUPS") {
    fetch(API_BASE + "/groups")
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => sendResponse({ success: true, groups: data.groups }))
      .catch(() => sendResponse({ success: false }));
    return true;
  }

  if (request.action === "SAVE_WORD") {
    fetch(API_BASE + "/save_word", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request.payload),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then((result) =>
        sendResponse({
          success: result.ok && result.data && result.data.success !== false,
          data: result.data,
        })
      )
      .catch(() => sendResponse({ success: false }));
    return true;
  }

  if (request.action === "CREATE_GROUP") {
    fetch(API_BASE + "/create_group", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request.payload),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then((result) => {
        if (result.ok && result.data && result.data.group) {
          sendResponse({ success: true, group: result.data.group });
        } else {
          sendResponse({ success: false });
        }
      })
      .catch(() => sendResponse({ success: false }));
    return true;
  }

  // ==========================================
  // LUỒNG 5: ĐỒNG BỘ TỪ ĐIỂN
  // App có thể đã được thêm từ ở máy khác, nên kéo dict.json về cache.
  // Chỉ thêm từ CHƯA có, không ghi đè cache sẵn có.
  // ==========================================
  if (request.action === "SYNC_DICT") {
    Promise.all([loadDictionary(), loadCache()])
      .then(([dictFile, cache]) => {
        let added = 0;
        for (const [word, entry] of Object.entries(dictFile)) {
          if (!(word in cache)) {
            cache[word] = entry;
            added++;
          }
        }

        if (added === 0) {
          sendResponse({ success: true, added: 0, total: Object.keys(cache).length });
          return;
        }

        chrome.storage.local.set({ [CACHE_KEY]: cache }, () => {
          sendResponse({
            success: true,
            added,
            total: Object.keys(cache).length,
          });
        });
      })
      .catch(() => sendResponse({ success: false }));
    return true;
  }

  // ==========================================
  // LUỒNG 6: ĐẨY CACHE LÊN dict.json (chiều ngược của SYNC_DICT)
  //
  // VẤN ĐỀ ĐÃ SỬA: từ mới chỉ được ghi vào dict.json nếu app ĐANG CHẠY đúng
  // lúc tra từ. Nếu app tắt lúc đó, từ chỉ nằm trong chrome.storage.local và
  // TRƯỚC ĐÂY KHÔNG BAO GIỜ được đồng bộ trở lại -> dict.json mãi không đổi.
  //
  // Action này đẩy mọi từ có trong cache mà CHƯA có trong dict.json lên app,
  // qua POST /add_dict. App sẽ tự nạp lại. Chạy khi app vừa khởi động (xem
  // content.js) nên vòng lặp được khép kín, không cần người dùng thao tác.
  //
  // KHÔNG ghi đè: /add_dict ở phía app cũng chỉ thêm từ chưa có.
  // ==========================================
  if (request.action === "FLUSH_CACHE_TO_DICT") {
    // Nạp lại dict MỚI NHẤT từ app trước, để không đẩy trùng những từ app đã có.
    Promise.all([reloadDictionary().then(() => loadDictionary()), loadCache()])
      .then(([dictFile, cache]) => {
        const missing = {};
        for (const [word, entry] of Object.entries(cache)) {
          if (!(word in dictFile)) missing[word] = entry;
        }

        const missingCount = Object.keys(missing).length;
        if (missingCount === 0) {
          sendResponse({ success: true, added: 0, total: Object.keys(cache).length });
          return;
        }

        fetch(API_BASE + "/add_dict", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ entries: missing }),
        })
          .then((res) => (res.ok ? res.json() : null))
          .then((data) => {
            // Ghi thành công -> cập nhật bản dict.json đang giữ trong RAM
            // để lần sau không đẩy lại những từ này.
            if (data && data.success) {
              for (const [word, entry] of Object.entries(missing)) {
                dictionaryData[word] = entry;
              }
            }
            sendResponse({
              success: !!(data && data.success),
              added: (data && data.added) || 0,
              total: Object.keys(cache).length,
            });
          })
          .catch(() => sendResponse({ success: false, added: 0 }));
      })
      .catch(() => sendResponse({ success: false, added: 0 }));
    return true;
  }
});

// Nạp sẵn từ điển khi service worker thức dậy
loadDictionary();
