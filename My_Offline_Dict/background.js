let dictionaryData = null;

fetch(chrome.runtime.getURL('dict.json'))
  .then(response => response.json())
  .then(data => {
    dictionaryData = data;
  });

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "LOOKUP") {
    const text = request.word.toLowerCase().trim();
    
    if (dictionaryData && dictionaryData[text]) {
      sendResponse({ 
        success: true, 
        source: "Offline", 
        data: dictionaryData[text] 
      });
    } 
    else {
      const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=vi&dt=t&q=${encodeURIComponent(text)}`;
      
      fetch(url)
        .then(res => res.json())
        .then(data => {
          const translatedText = data[0].map(item => item[0]).join("");
          
          dictionaryData[text] = {
            ipa: "",
            meaning: translatedText
          };

          sendResponse({ 
            success: true, 
            source: "Google ➔ Đã nạp vào Dict", 
            data: dictionaryData[text] 
          });
        })
        .catch(err => {
          sendResponse({ success: false });
        });
    }
  }
  return true; 
});