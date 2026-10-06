let dictionaryData = null;
let dictLoadPromise = null;

// 1. Khởi tạo Promise để ép hệ thống xử lý xong file 28MB mới được tra từ
function loadDictionary() {
  if (!dictLoadPromise) {
    dictLoadPromise = fetch(chrome.runtime.getURL('dict.json'))
      .then(response => response.json())
      .then(data => {
        dictionaryData = data;
        return data;
      })
      .catch(err => {
        dictionaryData = {}; // Nếu lỗi thì tạo Object rỗng để không bị sập
        return dictionaryData;
      });
  }
  return dictLoadPromise;
}

// Bắt đầu tải file vào bộ nhớ ngay khi tiện ích thức dậy
loadDictionary();

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // ==========================================
  // LUỒNG 1: TRA TỪ (OFFLINE HOẶC GOOGLE)
  // ==========================================
  if (request.action === "LOOKUP") {
    const text = request.word.toLowerCase().trim();

    // Chờ tải xong từ điển 28MB rồi mới tiến hành tra từ
    loadDictionary().then((dict) => {
      if (dict && dict[text]) {
        // Có sẵn Offline -> Trả về luôn, BỎ QUA check IPA để tránh bị treo
        sendResponse({ 
          success: true, 
          source: "Offline", 
          data: dict[text] 
        });
      } 
      else {
        // Chỉ dùng Google cho TỪ MỚI
        const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=vi&dt=t&dt=rm&q=${encodeURIComponent(text)}`;
        
        fetch(url)
          .then(res => res.json())
          .then(data => {
            const translatedText = data[0].map(item => item[0]).filter(Boolean).join("");
            
            let ipaText = "";
            for (let i = 0; i < data[0].length; i++) {
               if (data[0][i][2]) ipaText = data[0][i][2];
               else if (data[0][i][3]) ipaText = data[0][i][3];
            }
            if (ipaText) ipaText = "/" + ipaText.trim() + "/";

            const newEntry = {
              ipa: ipaText,
              meaning: "- " + translatedText 
            };

            const isWordOrPhrase = text.length <= 25;
            if (isWordOrPhrase && dictionaryData) {
              dictionaryData[text] = newEntry; 
            }

            sendResponse({ 
              success: true, 
              source: isWordOrPhrase ? "Google" : "Google (Câu dài)", 
              data: newEntry 
            });
          })
          .catch(err => {
            // Bỏ qua lỗi Google Translate gọn gàng, không để bị treo
            sendResponse({ success: false });
          });
      }
    });
    return true; // Giữ cổng kết nối chờ xử lý bất đồng bộ
  }

  // ==========================================
  // LUỒNG 2, 3, 4: CHUYỂN SANG IP 127.0.0.1 ĐỂ TRÁNH LỖI MẠNG
  // ==========================================
  if (request.action === "GET_GROUPS") {
    fetch("http://127.0.0.1:5000/groups")
      .then(res => res.json())
      .then(data => sendResponse({ success: true, groups: data.groups }))
      .catch(err => sendResponse({ success: false }));
    return true; 
  }

  if (request.action === "SAVE_WORD") {
    fetch("http://127.0.0.1:5000/save_word", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request.payload)
    })
    .then(res => res.json())
    .then(data => sendResponse({ success: true, data: data }))
    .catch(err => sendResponse({ success: false }));
    return true; 
  }

  if (request.action === "CREATE_GROUP") {
    fetch("http://127.0.0.1:5000/create_group", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request.payload)
    })
    .then(res => res.json())
    .then(data => sendResponse({ success: true, group: data.group }))
    .catch(err => sendResponse({ success: false }));
    return true; 
  }
});