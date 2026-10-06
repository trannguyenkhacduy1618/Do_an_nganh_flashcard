// ============================================================
// Offline Dictionary - Content Script
//
// Toàn bộ giao diện nằm ở popup bôi đen (không dùng popup.html trên toolbar).
// Popup gồm:
//   - từ + phiên âm + nghĩa
//   - nhãn nguồn (Offline / Đã lưu / Google)
//   - chọn nhóm + tạo nhóm + nút lưu vào Flashcard
//   - nút mở Flashcard App (khi app chưa chạy)
// ============================================================

let popup = null;

// Lưu lại đoạn text đã bôi đen NGAY khi selection thay đổi.
//
// LÝ DO: trước đây chỉ đọc window.getSelection() trong sự kiện "mouseup".
// Cách đó sai ở 2 tình huống rất thường gặp:
//   1. Bôi đen xong rồi click ra ngoài -> selection đã bị xoá, đọc được rỗng.
//   2. Bôi đen ngược từ phải sang trái, hoặc bôi qua thẻ HTML -> thứ tự
//      anchor/focus bị ngược khiến đoạn lấy ra thiếu ký tự đầu/cuối.
// Đó chính là nguyên nhân "volunteer editors" bị lưu thành "olunteer e".
//
// `stamp` là số thứ tự tăng dần mỗi khi selection THỰC SỰ đổi. Nhờ nó ta
// phân biệt được "selection mới do người dùng vừa tạo" với "selection cũ còn
// sót lại" — đây là chìa khoá để popup KHÔNG tự mở lại khi bấm ra ngoài.
let lastSelection = { text: "", rect: null, stamp: 0 };
let selectionStamp = 0;

// Đánh dấu selection đã bị NGƯỜI DÙNG xoá (bấm ra ngoài, bấm chỗ khác).
// Khi cờ này bật, mouseup sẽ KHÔNG tra từ và KHÔNG mở lại popup.
let selectionCleared = false;

function captureSelection() {
  const sel = window.getSelection();

  // Selection rỗng / đã thu gọn => người dùng đã bỏ chọn.
  if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
    selectionCleared = true;
    return;
  }

  const text = sel.toString();
  if (!text || !text.trim()) {
    selectionCleared = true;
    return;
  }

  // Lấy rect trước khi selection có thể bị thay đổi
  let rect = null;
  try {
    rect = sel.getRangeAt(0).getBoundingClientRect();
  } catch (e) {
    return;
  }

  const trimmed = text.trim();
  // Mỗi lần selection hợp lệ được tạo ra (kể cả trùng nội dung cũ) đều tăng
  // stamp. Nhờ vậy bôi lại đúng từ đã tra trước đó vẫn hiện popup như mong đợi.
  // Việc CHỐNG TRÙNG được xử lý ở mouseup bằng so sánh với stamp lúc mousedown.
  selectionStamp++;
  lastSelection = { text: trimmed, rect: rect, stamp: selectionStamp };

  // Có selection hợp lệ => cờ "đã xoá" tắt.
  selectionCleared = false;
}

// Bắt selection ngay khi người dùng đang kéo chuột / dùng bàn phím
document.addEventListener("selectionchange", captureSelection);
document.addEventListener("mouseup", captureSelection);

// Mở app Flashcard trên máy bằng protocol "flashcard://"
// Windows sẽ chạy Flash_Card_App/run_app.bat (tức "python main.py").
// Protocol này được cài 1 lần bằng install_protocol.bat ở thư mục dự án.
function openDesktopApp() {
  const link = document.createElement("a");
  link.href = "flashcard://open";
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

// ============================================================
// LUỒNG CHUỘT: TRA TỪ + ĐÓNG POPUP
//
// Thứ tự sự kiện khi người dùng thao tác chuột:
//   mousedown -> (selectionchange) -> mouseup -> click
//
// Quy tắc:
//   * mousedown RA NGOÀI popup  -> đóng popup NGAY, và đánh dấu "selection cũ"
//     để mouseup theo sau KHÔNG mở lại popup đó nữa.
//   * mouseup  -> chỉ tra từ khi có selection MỚI (stamp tăng so với lần trước).
//
// Đây là chỗ sửa lỗi "bấm ra ngoài mà popup vẫn hiện lại liên tục":
// bản cũ so sánh bằng chuỗi rỗng, nên khi trang không xoá selection cũ
// (bấm chuột phải / bấm vùng trống) nó tưởng là bôi đen mới -> hiện lại popup.
// ============================================================

let lookupSeq = 0;

// Stamp của selection đã được hiển thị lần trước, để không hiện trùng.
let shownStamp = -1;

// Stamp tại thời điểm mousedown — dùng để so sánh ở mouseup.
let pendingStamp = -1;

// Bật khi người dùng chủ động đóng popup (bấm ra ngoài / Esc) trong lúc
// còn request tra từ đang bay. Chặn popup "mọc lại" khi response về muộn.
let suppressResult = false;

// true khi đang có 1 request LOOKUP chưa trả về.
let hasPendingLookup = false;

// Đóng popup (có animation thu nhỏ rồi xoá khỏi DOM).
// `fadingPopup` giữ element đang mờ dần để lần mở popup kế tiếp xoá ngay,
// tránh 2 popup chồng lên nhau khi người dùng thao tác nhanh.
let fadingPopup = null;

function closePopup() {
  if (!popup) return;
  const el = popup;
  popup = null;
  fadingPopup = el;
  el.style.opacity = "0";
  el.style.transform = "translateY(10px) scale(0.95)";
  setTimeout(() => {
    el.remove();
    if (fadingPopup === el) fadingPopup = null;
  }, 300);
}

// Phím Esc -> đóng popup + huỷ hiển thị kết quả đang chờ.
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (!popup && !hasPendingLookup) return;

  closePopup();
  // Đánh dấu để mouseup sau đó không mở lại popup vừa đóng.
  pendingStamp = lastSelection.stamp;
  shownStamp = lastSelection.stamp;
  // Request đang bay (nếu có) về muộn cũng KHÔNG được bật popup lên.
  suppressResult = true;
});

document.addEventListener(
  "mousedown",
  (e) => {
    // Bấm vào chính popup -> không đóng, không làm gì cả.
    if (popup && popup.contains(e.target)) return;

    // Bấm ra ngoài -> đóng popup (nếu đang mở).
    if (popup) closePopup();

    // Đánh dấu: nếu selection hiện tại KHÔNG đổi trong cú click này thì
    // mouseup sau đó sẽ không được coi là bôi đen mới -> không mở lại popup.
    pendingStamp = lastSelection.stamp;
    // Chặn popup của request đang bay (nếu có) hiện lên sau khi đã bấm ra ngoài.
    suppressResult = true;
  },
  true
);

document.addEventListener("mouseup", (e) => {
  // Bấm trong popup (chọn nhóm, bấm nút...) -> bỏ qua hoàn toàn.
  if (popup && popup.contains(e.target)) return;

  // Stamp ngay lúc này; captureSelection đã chạy ở mouseup phía trên
  // nên lastSelection đã phản ánh selection mới nhất.
  const currentStamp = lastSelection.stamp;

  // Không có selection MỚI (stamp không đổi so với lúc mousedown / lần đã hiện)
  // => đây chỉ là cú click bình thường, KHÔNG tra từ, KHÔNG mở popup.
  if (selectionCleared) return;
  if (currentStamp === 0 || currentStamp === pendingStamp || currentStamp === shownStamp) return;

  const word = lastSelection.text;
  if (!word || word.length >= 2500) return;

  const rect = lastSelection.rect;
  if (!rect || (rect.width === 0 && rect.height === 0)) return;

  shownStamp = currentStamp;
  // Chặn luôn mouseup thứ 2 của cùng một cú nhả chuột (trang nhiều link có
  // thể bắn mouseup nhiều lần) -> tránh tra từ trùng và ghi cache 2 lần.
  pendingStamp = currentStamp;
  // Bắt đầu một lần tra MỚI -> cho phép kết quả hiện popup trở lại.
  suppressResult = false;
  hasPendingLookup = true;
  const seq = ++lookupSeq;

  chrome.runtime.sendMessage({ action: "LOOKUP", word }, (response) => {
    if (seq === lookupSeq) hasPendingLookup = false;
    // Có lần bôi đen mới hơn -> bỏ kết quả cũ (chống ghi nhầm vào từ điển).
    if (seq !== lookupSeq) return;
    // Người dùng đã bấm ra ngoài / Esc trong lúc chờ API -> KHÔNG bật popup lên.
    if (suppressResult) return;
    if (response && response.success) {
      showPopup(word, response.data, rect, response);
    }
  });
});

// ============================================================
// POPUP
// ============================================================

function showPopup(word, data, rect, response) {
  // Xoá cả popup đang mờ dần (nếu có) để không bị chồng 2 lớp.
  if (popup) popup.remove();
  if (fadingPopup) {
    fadingPopup.remove();
    fadingPopup = null;
  }

  popup = document.createElement("div");
  popup.style.cssText = `
    position: fixed; z-index: 2147483647;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #1f2937; padding: 16px; border-radius: 16px;
    min-width: 280px; max-width: min(500px, 90vw); max-height: min(600px, 75vh);
    overflow-y: auto; word-wrap: break-word;
    background: rgba(255, 255, 255, 0.65);
    backdrop-filter: blur(16px) saturate(180%);
    -webkit-backdrop-filter: blur(16px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.8);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12), inset 0 0 0 1px rgba(255, 255, 255, 0.5);
    opacity: 0;
  `;

  // Nhãn nguồn:
  //  - "Offline"   : có sẵn trong dict.json (từ điển dùng chung với app)
  //  - "Đã lưu"    : đã tra trước đây, nằm trong cache chrome.storage.local
  //  - "Google..." : từ mới, phải gọi API
  let sourceText = "Offline";
  if (response && response.source) {
    sourceText = response.source;
  } else {
    sourceText = word.length <= 25 ? "Google" : "Google (Câu dài)";
  }

  const isWordOrPhrase = word.length <= 25;

  const actionAreaHTML = isWordOrPhrase
    ? `<div id="flashcard-action-area" style="margin-top: 12px; min-height: 64px; display: flex; flex-direction: column; justify-content: center; gap: 8px;">
         <span style="font-size: 13px; color: #6b7280; text-align: center;">Đang kết nối Desktop App...</span>
       </div>`
    : "";

  popup.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 8px; border-bottom: 1px solid rgba(0,0,0,0.06); padding-bottom: 8px;">
      <div style="font-weight: 800; font-size: 19px; color: #111827; letter-spacing: -0.5px; word-break: break-word;">${escapeHtml(word)}</div>
      <div style="display: flex; align-items: center; gap: 6px; flex: none;">
        <span style="font-size: 9px; background: rgba(0,0,0,0.05); padding: 4px 8px; border-radius: 12px; color: #4b5563; font-weight: 700; text-transform: uppercase; white-space: nowrap;">${escapeHtml(sourceText)}</span>
        <button id="flashcard-close" title="Đóng (Esc)" style="border: none; background: rgba(0,0,0,0.05); color: #6b7280; width: 22px; height: 22px; border-radius: 50%; font-size: 13px; line-height: 1; cursor: pointer; padding: 0; flex: none;">✕</button>
      </div>
    </div>
    <div style="color: #2563eb; font-size: 13px; font-weight: 600; margin-bottom: 12px; font-family: monospace;">${escapeHtml(data.ipa || "")}</div>
    <div style="font-size: 14.5px; line-height: 1.6; white-space: pre-wrap; color: #374151;">${escapeHtml(data.meaning || "")}</div>
    ${renderRichData(data)}
    ${actionAreaHTML}
  `;

  document.body.appendChild(popup);

  // Không cho thao tác trong popup "rò" ra trang (chọn text trang, kéo thả...)
  popup.addEventListener("mousedown", (ev) => ev.stopPropagation());
  popup.addEventListener("mouseup", (ev) => ev.stopPropagation());

  const btnClose = popup.querySelector("#flashcard-close");
  if (btnClose) btnClose.addEventListener("click", () => closePopup());

  if (isWordOrPhrase) {
    renderActionArea(popup, word, data);
  }

  positionPopup(popup, rect);
}

// Escape để từ vựng/tên nhóm không phá vỡ HTML của popup
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Hiển thị thêm định nghĩa / từ đồng nghĩa / ví dụ (nếu có).
// Thẻ cũ chỉ có ipa + meaning nên hàm này phải chịu được dữ liệu thiếu.
function renderRichData(data) {
  const parts = [];

  // --- Định nghĩa theo từ loại ---
  const definitions = Array.isArray(data.definitions) ? data.definitions : [];
  for (const block of definitions) {
    if (!block || !Array.isArray(block.definitions) || !block.definitions.length) continue;

    const heading = block.pos ? `ĐỊNH NGHĨA · ${block.pos}` : "ĐỊNH NGHĨA";
    const items = block.definitions
      .map(
        (d) => `
        <div style="display: flex; gap: 7px; margin-bottom: 4px;">
          <span style="color: #2563eb; font-weight: 700; flex: none;">•</span>
          <span style="flex: 1; font-size: 13px; line-height: 1.5; color: #374151;">${escapeHtml(d)}</span>
        </div>`
      )
      .join("");

    parts.push(sectionBlock(heading, items));
  }

  // --- Từ đồng nghĩa (dạng chip) ---
  const synonyms = Array.isArray(data.synonyms) ? data.synonyms : [];
  if (synonyms.length) {
    const chips = synonyms
      .map(
        (s) =>
          `<span style="display: inline-block; background: #eef2ff; border: 1px solid #c7d2fe; color: #1d4ed8; font-size: 11.5px; font-weight: 600; padding: 3px 9px; border-radius: 999px; margin: 0 4px 4px 0;">${escapeHtml(s)}</span>`
      )
      .join("");
    parts.push(sectionBlock("TỪ ĐỒNG NGHĨA", `<div style="line-height: 1.9;">${chips}</div>`));
  }

  // --- Ví dụ ---
  const examples = Array.isArray(data.examples) ? data.examples : [];
  if (examples.length) {
    const items = examples
      .map(
        (e) => `
        <div style="display: flex; gap: 7px; margin-bottom: 4px;">
          <span style="color: #10b981; font-weight: 700; flex: none;">“</span>
          <span style="flex: 1; font-size: 12.5px; line-height: 1.5; color: #4b5563; font-style: italic;">${escapeHtml(e)}</span>
        </div>`
      )
      .join("");
    parts.push(sectionBlock("VÍ DỤ", items));
  }

  return parts.join("");
}

function sectionBlock(heading, innerHtml) {
  return `
    <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(0,0,0,0.06);">
      <div style="font-size: 9.5px; font-weight: 800; letter-spacing: 0.5px; color: #9ca3af; margin-bottom: 6px;">${escapeHtml(heading)}</div>
      ${innerHtml}
    </div>
  `;
}

// ============================================================
// KHU VỰC LƯU THẺ (chọn nhóm / tạo nhóm / lưu / mở app)
// ============================================================

// Lấy group; nếu app đang tắt -> hiện thông báo + nút mở app.
// Tự thử lại 1 lần sau 1.5s phòng khi app vừa bật.
function renderActionArea(popupEl, word, data, attempt = 0) {
  if (!popup || popup !== popupEl) return;

  const actionArea = popupEl.querySelector("#flashcard-action-area");
  if (!actionArea) return;

  actionArea.innerHTML = `<span style="font-size: 13px; color: #6b7280; text-align: center;">Đang kết nối Desktop App...</span>`;

  chrome.runtime.sendMessage({ action: "GET_GROUPS" }, (res) => {
    // Popup đã bị đóng hoặc thay bằng cái khác trong lúc chờ
    if (!popup || popup !== popupEl) return;

    if (!res || !res.success || !res.groups) {
      if (attempt === 0) {
        setTimeout(() => renderActionArea(popupEl, word, data, 1), 1500);
        return;
      }
      showAppOffline(actionArea, word, data);
      return;
    }

    // App vừa online -> đẩy những từ đã tra lúc app tắt vào dict.json.
    flushCacheToDict();

    renderSaveForm(actionArea, word, data, res.groups);
  });
}

// ============================================================
// ĐỒNG BỘ CACHE -> dict.json (khép kín vòng lặp)
//
// Từ tra khi app TẮT chỉ nằm trong chrome.storage.local (cache) và trước đây
// KHÔNG BAO GIỜ được ghi vào dict.json -> dict mãi không đổi. Hàm này đẩy
// toàn bộ cache lên app, chạy 1 lần mỗi phiên khi phát hiện app đã bật.
// ============================================================
let hasFlushedDict = false;

function flushCacheToDict() {
  if (hasFlushedDict) return;
  hasFlushedDict = true;

  chrome.runtime.sendMessage({ action: "FLUSH_CACHE_TO_DICT" }, (res) => {
    if (res && res.success) {
      if (res.added) {
        console.log(`[Flashcard] Đã đồng bộ ${res.added} từ mới vào dict.json`);
      }
    } else {
      // App chưa chạy -> thử lại lần sau (đừng khoá vĩnh viễn).
      hasFlushedDict = false;
    }
  });
}

// Thử đồng bộ ngay khi content script vừa nạp trên trang: nếu app đang chạy,
// từ đã tra lúc app tắt sẽ được đẩy vào dict.json ngay, không cần bôi đen gì.
// (Nếu app chưa chạy, request thất bại êm và cờ được reset để thử lại sau.)
flushCacheToDict();

function showAppOffline(actionArea, word, data) {
  actionArea.innerHTML = `
    <div style="color: #ef4444; font-size: 13.5px; text-align: center; font-weight: 600;">🚫 Chưa kết nối được App</div>
    <button id="btn-open-app" style="padding: 9px; border: none; border-radius: 8px; background: #2563eb; color: white; font-weight: 700; font-size: 13px; cursor: pointer;">Mở Flashcard App</button>
    <span style="font-size: 11.5px; color: #6b7280; text-align: center;">Mở app rồi lưu lại từ này</span>
  `;

  const btnOpenApp = actionArea.querySelector("#btn-open-app");
  if (!btnOpenApp) return;

  btnOpenApp.addEventListener("click", () => {
    // Gọi đồng bộ ngay trong cú click để giữ "user gesture",
    // nhờ đó trình duyệt cho phép mở protocol flashcard://
    openDesktopApp();
    btnOpenApp.innerText = "Đang mở App...";
    btnOpenApp.style.background = "#9ca3af";

    // Thử lại trong lúc chờ app khởi động
    let tries = 0;
    const timer = setInterval(() => {
      tries++;

      // Popup bị đóng trong lúc chờ -> dừng
      if (!popup || !document.body.contains(actionArea)) {
        clearInterval(timer);
        return;
      }

      chrome.runtime.sendMessage({ action: "GET_GROUPS" }, (r) => {
        if (!popup || !document.body.contains(actionArea)) {
          clearInterval(timer);
          return;
        }
        if (r && r.success && r.groups) {
          clearInterval(timer);
          // Vừa mở app xong -> đồng bộ cache vào dict.json.
          flushCacheToDict();
          renderSaveForm(actionArea, word, data, r.groups);
        }
      });

      if (tries >= 12) {
        clearInterval(timer);
        btnOpenApp.innerText = "Mở Flashcard App";
        btnOpenApp.style.background = "#2563eb";
      }
    }, 1000);
  });
}

function renderSaveForm(actionArea, word, data, groups) {
  const optionsHTML = groups
    .map((g) => `<option value="${g.id}">${escapeHtml(g.name)}</option>`)
    .join("");

  actionArea.innerHTML = `
    <div style="display: flex; gap: 8px;">
      <select id="group-select" style="flex: 1; padding: 8px; border-radius: 8px; border: 1px solid #d1d5db; font-size: 13.5px; outline: none; background: #f9fafb; font-weight: 500; cursor: pointer;">
        ${optionsHTML || '<option value="" disabled selected>Chưa có nhóm</option>'}
      </select>
      <button id="btn-toggle-new-group" style="padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 8px; background: white; font-weight: bold; cursor: pointer; color: #374151;" title="Tạo nhóm mới">+</button>
    </div>

    <div id="new-group-area" style="display: none; gap: 8px;">
      <input type="text" id="new-group-input" placeholder="Nhập tên nhóm mới..." style="flex: 1; padding: 8px; border-radius: 8px; border: 1px solid #d1d5db; outline: none; font-size: 13px;" />
    </div>

    <button id="btn-save-flashcard" style="padding: 10px; border: none; border-radius: 8px; background: #10b981; color: white; font-weight: 700; cursor: pointer; transition: all 0.2s;">+ Lưu vào Flashcard</button>
  `;

  const btnSave = actionArea.querySelector("#btn-save-flashcard");
  const groupSelect = actionArea.querySelector("#group-select");
  const btnToggleNewGroup = actionArea.querySelector("#btn-toggle-new-group");
  const newGroupArea = actionArea.querySelector("#new-group-area");
  const inputNewGroup = actionArea.querySelector("#new-group-input");

  btnToggleNewGroup.addEventListener("click", () => {
    newGroupArea.style.display = newGroupArea.style.display === "none" ? "flex" : "none";
    if (newGroupArea.style.display === "flex") inputNewGroup.focus();
  });

  const executeCreateGroup = (name, callback) => {
    chrome.runtime.sendMessage({ action: "CREATE_GROUP", payload: { name } }, (createRes) => {
      if (createRes && createRes.success && createRes.group) {
        if (groupSelect.querySelector("option[disabled]")) groupSelect.innerHTML = "";
        const newOption = document.createElement("option");
        newOption.value = createRes.group.id;
        newOption.innerText = createRes.group.name;
        groupSelect.appendChild(newOption);
        groupSelect.value = createRes.group.id;

        newGroupArea.style.display = "none";
        inputNewGroup.value = "";
        if (callback) callback(createRes.group.id);
      } else {
        if (callback) callback(null);
      }
    });
  };

  const executeSaveCard = (targetGroupId) => {
    // Gửi KÈM dữ liệu phong phú (định nghĩa / đồng nghĩa / ví dụ) để app
    // hiển thị lại trong thẻ đọc. Thiếu 3 trường này thì thẻ lưu xong sẽ
    // mất hết phần trực quan dù popup đã tra được.
    const payload = {
      word,
      ipa: data.ipa || "",
      meaning: data.meaning,
      group_id: targetGroupId,
    };
    if (Array.isArray(data.definitions) && data.definitions.length) {
      payload.definitions = data.definitions;
    }
    if (Array.isArray(data.synonyms) && data.synonyms.length) {
      payload.synonyms = data.synonyms;
    }
    if (Array.isArray(data.examples) && data.examples.length) {
      payload.examples = data.examples;
    }

    chrome.runtime.sendMessage(
      {
        action: "SAVE_WORD",
        payload,
      },
      (saveRes) => {
        if (saveRes && saveRes.success) {
          btnSave.innerText = "Đã lưu ✓";
          btnSave.style.background = "#3b82f6";
        } else {
          btnSave.innerText = "Lỗi lưu thẻ";
          btnSave.style.background = "#ef4444";
        }
        btnSave.style.opacity = "1";
      }
    );
  };

  btnSave.addEventListener("click", () => {
    const newName = inputNewGroup.value.trim();
    btnSave.style.opacity = "0.7";

    if (newGroupArea.style.display !== "none" && newName) {
      btnSave.innerText = "Đang tạo nhóm & lưu...";
      executeCreateGroup(newName, (newGroupId) => {
        if (newGroupId) {
          executeSaveCard(newGroupId);
        } else {
          btnSave.innerText = "Lỗi tạo nhóm";
          btnSave.style.background = "#ef4444";
        }
      });
      return;
    }

    if (!groupSelect.value) {
      btnSave.innerText = "Chọn hoặc tạo nhóm trước!";
      btnSave.style.background = "#f59e0b";
      setTimeout(() => {
        btnSave.innerText = "+ Lưu vào Flashcard";
        btnSave.style.background = "#10b981";
      }, 1500);
      return;
    }

    btnSave.innerText = "Đang lưu...";
    executeSaveCard(groupSelect.value);
  });
}

// ============================================================
// VỊ TRÍ POPUP
// ============================================================

function positionPopup(popupEl, rect) {
  const popupRect = popupEl.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  let leftPos = rect.left;
  if (leftPos + popupRect.width > viewportWidth - 20) leftPos = viewportWidth - popupRect.width - 20;
  if (leftPos < 20) leftPos = 20;

  let topPos = rect.bottom + 10;
  if (topPos + popupRect.height > viewportHeight - 20) {
    const spaceAbove = rect.top;
    const spaceBelow = viewportHeight - rect.bottom;
    if (spaceAbove > spaceBelow || spaceAbove > popupRect.height + 20) {
      topPos = rect.top - popupRect.height - 10;
    } else {
      topPos = viewportHeight - popupRect.height - 20;
    }
  }
  if (topPos < 20) topPos = 20;

  popupEl.style.left = `${leftPos}px`;
  popupEl.style.top = `${topPos}px`;
  popupEl.style.transform = "translateY(10px) scale(0.95)";
  popupEl.style.transition =
    "opacity 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)";

  requestAnimationFrame(() => {
    popupEl.style.opacity = "1";
    popupEl.style.transform = "translateY(0) scale(1)";
  });
}
