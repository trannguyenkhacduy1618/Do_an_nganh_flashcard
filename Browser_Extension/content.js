let popup = null;

// 1. Lắng nghe sự kiện click bên ngoài để đóng popup
document.addEventListener("mousedown", (e) => {
  if (popup && !popup.contains(e.target)) {
    popup.style.opacity = '0';
    popup.style.transform = 'translateY(10px) scale(0.95)';
    setTimeout(() => { if (popup) { popup.remove(); popup = null; } }, 300); 
  }
});

// 2. Lắng nghe sự kiện bôi đen từ vựng
document.addEventListener("mouseup", (e) => {
  if (popup && popup.contains(e.target)) return;

  const selectedText = window.getSelection().toString().trim();
  if (selectedText.length > 0 && selectedText.length < 2500) {
    const range = window.getSelection().getRangeAt(0);
    const rect = range.getBoundingClientRect();
    
    chrome.runtime.sendMessage({ action: "LOOKUP", word: selectedText }, (response) => {
      if (response && response.success) {
        showPopup(selectedText, response.data, rect, response);
      }
    });
  }
});

// 3. Hàm hiển thị Popup giao diện tra từ và quản lý nhóm
function showPopup(word, data, rect, response) {
  if (popup) popup.remove();
  
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

  // KHẮC PHỤC: Xác định chuẩn xác nhãn nguồn, không bị ép mặc định thành Offline
  let sourceText = "Offline";
  if (response && response.source) {
    sourceText = response.source;
  } else {
    sourceText = word.length <= 25 ? "Google" : "Google (Câu dài)";
  }

  const isWordOrPhrase = word.length <= 25;
  
  const actionAreaHTML = isWordOrPhrase ? 
    `<div id="flashcard-action-area" style="margin-top: 12px; min-height: 64px; display: flex; flex-direction: column; justify-content: center; gap: 8px;">
        <span style="font-size: 13px; color: #6b7280; text-align: center;">Đang kết nối Desktop App...</span>
     </div>` : '';

  popup.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; border-bottom: 1px solid rgba(0,0,0,0.06); padding-bottom: 8px;">
      <div style="font-weight: 800; font-size: 19px; color: #111827; letter-spacing: -0.5px;">${word}</div>
      <span style="font-size: 9px; background: rgba(0,0,0,0.05); padding: 4px 8px; border-radius: 12px; color: #4b5563; font-weight: 700; text-transform: uppercase;">${sourceText}</span>
    </div>
    <div style="color: #2563eb; font-size: 13px; font-weight: 600; margin-bottom: 12px; font-family: monospace;">${data.ipa || ''}</div>
    <div style="font-size: 14.5px; line-height: 1.6; white-space: pre-wrap; color: #374151;">${data.meaning}</div>
    ${actionAreaHTML}
  `;

  document.body.appendChild(popup);

  if (isWordOrPhrase) {
    const actionArea = popup.querySelector("#flashcard-action-area");
    
    chrome.runtime.sendMessage({ action: "GET_GROUPS" }, (res) => {
      if (res && res.success && res.groups) {
        const groups = res.groups;
        const optionsHTML = groups.map(g => `<option value="${g.id}">${g.name}</option>`).join("");
        
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

        const btnSave = popup.querySelector("#btn-save-flashcard");
        const groupSelect = popup.querySelector("#group-select");
        const btnToggleNewGroup = popup.querySelector("#btn-toggle-new-group");
        const newGroupArea = popup.querySelector("#new-group-area");
        const inputNewGroup = popup.querySelector("#new-group-input");

        btnToggleNewGroup.addEventListener("click", () => {
           newGroupArea.style.display = newGroupArea.style.display === "none" ? "flex" : "none";
           if (newGroupArea.style.display === "flex") inputNewGroup.focus();
        });

        const executeCreateGroup = (name, callback) => {
           chrome.runtime.sendMessage({ action: "CREATE_GROUP", payload: { name: name } }, (createRes) => {
             if (createRes && createRes.success && createRes.group) {
                if (groupSelect.querySelector('option[disabled]')) groupSelect.innerHTML = '';
                const newOption = document.createElement("option");
                newOption.value = createRes.group.id;
                newOption.innerText = createRes.group.name;
                groupSelect.appendChild(newOption);
                groupSelect.value = createRes.group.id;
                
                newGroupArea.style.display = "none";
                inputNewGroup.value = "";
                if(callback) callback(createRes.group.id);
             } else {
                if(callback) callback(null);
             }
           });
        };

        const executeSaveCard = (targetGroupId) => {
          chrome.runtime.sendMessage({
            action: "SAVE_WORD",
            payload: { word: word, ipa: data.ipa || "", meaning: data.meaning, group_id: targetGroupId }
          }, (saveRes) => {
            if (saveRes && saveRes.success) {
              btnSave.innerText = "Đã lưu ✓";
              btnSave.style.background = "#3b82f6";
              btnSave.style.opacity = "1";
            } else {
              btnSave.innerText = "Lỗi lưu thẻ";
              btnSave.style.background = "#ef4444";
              btnSave.style.opacity = "1";
            }
          });
        };

        btnSave.addEventListener("click", () => {
          const newName = inputNewGroup.value.trim();
          btnSave.style.opacity = "0.7";
          
          if (newGroupArea.style.display !== "none" && newName) {
              btnSave.innerText = "Đang tạo nhóm & lưu...";
              executeCreateGroup(newName, (newGroupId) => {
                  if (newGroupId) executeSaveCard(newGroupId);
                  else { btnSave.innerText = "Lỗi tạo nhóm"; btnSave.style.background = "#ef4444"; }
              });
          } else {
              if (!groupSelect.value) {
                  btnSave.innerText = "Chọn hoặc tạo nhóm trước!";
                  btnSave.style.background = "#f59e0b";
                  setTimeout(() => { btnSave.innerText = "+ Lưu vào Flashcard"; btnSave.style.background = "#10b981"; }, 1500);
                  return;
              }
              btnSave.innerText = "Đang lưu...";
              executeSaveCard(groupSelect.value);
          }
        });
      } else {
        actionArea.innerHTML = `<div style="color: #ef4444; font-size: 13.5px; text-align: center; font-weight: 600;">🚫 Không kết nối được App!</div>`;
      }
    });
  }

  // --- Tính tọa độ Popup ---
  const popupRect = popup.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  let leftPos = rect.left;
  if (leftPos + popupRect.width > viewportWidth - 20) leftPos = viewportWidth - popupRect.width - 20; 
  if (leftPos < 20) leftPos = 20;

  let topPos = rect.bottom + 10; 
  if (topPos + popupRect.height > viewportHeight - 20) {
    const spaceAbove = rect.top; 
    const spaceBelow = viewportHeight - rect.bottom; 
    if (spaceAbove > spaceBelow || spaceAbove > popupRect.height + 20) topPos = rect.top - popupRect.height - 10;
    else topPos = viewportHeight - popupRect.height - 20;
  }
  if (topPos < 20) topPos = 20;

  popup.style.left = `${leftPos}px`;
  popup.style.top = `${topPos}px`;
  popup.style.transform = 'translateY(10px) scale(0.95)';
  popup.style.transition = 'opacity 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)';

  requestAnimationFrame(() => {
    popup.style.opacity = '1';
    popup.style.transform = 'translateY(0) scale(1)';
  });
}