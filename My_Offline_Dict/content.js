let popup = null;

document.addEventListener("mousedown", (e) => {
  if (popup && !popup.contains(e.target)) {
    popup.style.opacity = '0';
    popup.style.transform = 'translateY(10px) scale(0.95)';
    
    setTimeout(() => {
      if (popup) {
        popup.remove();
        popup = null;
      }
    }, 250); 
  }
});

document.addEventListener("mouseup", (e) => {
  const selectedText = window.getSelection().toString().trim();

  if (selectedText.length > 0 && selectedText.length < 250) {
    const range = window.getSelection().getRangeAt(0);
    const rect = range.getBoundingClientRect();

    chrome.runtime.sendMessage({ action: "LOOKUP", word: selectedText }, (response) => {
      if (response && response.success) {
        showPopup(selectedText, response.data, rect, response);
      }
    });
  }
});

function showPopup(word, data, rect, response) {
  if (popup) popup.remove();

  popup = document.createElement("div");
  
  popup.style.cssText = `
    position: fixed;
    top: ${rect.bottom + 10}px;
    left: ${Math.min(rect.left, window.innerWidth - 300)}px;
    width: 280px;
    max-height: 250px;
    overflow-y: auto;
    z-index: 2147483647;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #1f2937;
    padding: 16px;
    border-radius: 16px;
    
    background: rgba(255, 255, 255, 0.65);
    backdrop-filter: blur(16px) saturate(180%);
    -webkit-backdrop-filter: blur(16px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.8);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12), inset 0 0 0 1px rgba(255, 255, 255, 0.5);
    
    opacity: 0;
    transform: translateY(10px) scale(0.95);
    transition: opacity 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  `;

  const sourceText = response && response.source ? response.source : "Offline";

  popup.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; border-bottom: 1px solid rgba(0,0,0,0.06); padding-bottom: 8px;">
      <div style="font-weight: 800; font-size: 19px; color: #111827; letter-spacing: -0.5px;">${word}</div>
      <span style="font-size: 9px; background: rgba(0,0,0,0.05); padding: 4px 8px; border-radius: 12px; color: #4b5563; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">${sourceText}</span>
    </div>
    <div style="color: #2563eb; font-size: 13px; font-weight: 600; margin-bottom: 12px; font-family: monospace;">${data.ipa || ''}</div>
    <div style="font-size: 14.5px; line-height: 1.6; white-space: pre-wrap; color: #374151; font-weight: 450;">${data.meaning}</div>
  `;

  document.body.appendChild(popup);

  requestAnimationFrame(() => {
    popup.style.opacity = '1';
    popup.style.transform = 'translateY(0) scale(1)';
  });
}