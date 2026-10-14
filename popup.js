// Popup controller for InstaReels Downloader

document.addEventListener('DOMContentLoaded', async () => {
  const urlInput = document.getElementById('urlInput');
  const pasteBtn = document.getElementById('pasteBtn');
  const detectTabBtn = document.getElementById('detectTabBtn');
  const downloadBtn = document.getElementById('downloadBtn');
  const btnText = document.getElementById('btnText');
  const btnSpinner = document.getElementById('btnSpinner');
  const statusArea = document.getElementById('statusArea');
  const statusTitle = document.getElementById('statusTitle');
  const statusMessage = document.getElementById('statusMessage');
  const historyList = document.getElementById('historyList');
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');

  // Load download history
  loadHistory();

  // Check current tab to see if user is on Instagram
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url && tab.url.includes('instagram.com')) {
      if (tab.url.includes('/reel/') || tab.url.includes('/p/')) {
        urlInput.value = tab.url;
        showStatus('loading', 'Reel detectado!', 'Link da aba ativa carregado automaticamente.');
      } else {
        detectTabBtn.style.borderColor = 'rgba(240, 148, 51, 0.5)';
      }
    }
  } catch (e) {
    console.log('Erro ao inspecionar aba ativa:', e);
  }

  // Paste from clipboard
  pasteBtn.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && text.includes('instagram.com')) {
        urlInput.value = text.trim();
        showStatus('loading', 'Link colado!', 'Clique em Baixar Vídeo para iniciar.');
      } else if (text) {
        urlInput.value = text.trim();
      }
    } catch (err) {
      // Fallback: prompt or focus
      urlInput.focus();
    }
  });

  // Detect video from active tab
  detectTabBtn.addEventListener('click', async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.url || !tab.url.includes('instagram.com')) {
        showStatus('error', 'Aba não é do Instagram', 'Abra uma aba do Instagram com o Reels desejado.');
        return;
      }

      setLoading(true, 'Detectando vídeo na aba...');

      chrome.tabs.sendMessage(tab.id, { action: 'getCurrentVideoInfo' }, (response) => {
        setLoading(false);
        if (chrome.runtime.lastError || !response) {
          // If content script wasn't reachable, fallback to tab URL
          if (tab.url.includes('/reel/') || tab.url.includes('/p/')) {
            urlInput.value = tab.url;
            showStatus('loading', 'Link capturado!', 'Clique em "Baixar Vídeo MP4".');
          } else {
            showStatus('error', 'Nenhum vídeo ativo', 'Navegue até o Reels que deseja baixar e tente novamente.');
          }
          return;
        }

        if (response.pageUrl) {
          urlInput.value = response.pageUrl;
        }

        if (response.videoSrc) {
          showStatus('loading', 'Vídeo localizado!', 'Iniciando download direto...');
          // Download directly using found video URL
          startDirectDownload(response.videoSrc, response.pageUrl);
        } else {
          showStatus('loading', 'Link capturado!', 'Clique em "Baixar Vídeo MP4".');
        }
      });
    } catch (err) {
      setLoading(false);
      showStatus('error', 'Erro ao detectar', err.message);
    }
  });

  // Handle Download Button
  downloadBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();

    if (!url) {
      showStatus('error', 'Link em branco', 'Por favor, cole um link de vídeo ou Reel do Instagram.');
      urlInput.focus();
      return;
    }

    if (!url.includes('instagram.com') || (!url.includes('/reel') && !url.includes('/p/') && !url.includes('/tv/'))) {
      showStatus('error', 'Link inválido', 'O link precisa ser de um Reel ou Post com vídeo do Instagram.');
      return;
    }

    setLoading(true, 'Localizando vídeo...');
    showStatus('loading', 'Buscando vídeo...', 'Extraindo o arquivo na melhor qualidade disponível...');

    chrome.runtime.sendMessage(
      { action: 'resolveAndDownload', url },
      (response) => {
        setLoading(false);

        if (response && response.success) {
          showStatus(
            'success',
            'Download Iniciado!',
            `O vídeo foi salvo na sua pasta de Downloads como: ${response.filename}`
          );
          loadHistory();
        } else {
          showStatus(
            'error',
            'Falha ao baixar',
            (response && response.error) ? response.error : 'Não foi possível encontrar a mídia. O vídeo pode ser privado.'
          );
        }
      }
    );
  });

  // Start direct download
  function startDirectDownload(videoUrl, pageUrl) {
    setLoading(true, 'Baixando arquivo...');
    chrome.runtime.sendMessage(
      { action: 'downloadDirect', videoUrl, pageUrl },
      (response) => {
        setLoading(false);
        if (response && response.success) {
          showStatus('success', 'Download Iniciado!', `Salvo na pasta Downloads: ${response.filename}`);
          loadHistory();
        } else {
          showStatus('error', 'Erro no download direto', response?.error || 'Tente pelo botão Baixar Vídeo.');
        }
      }
    );
  }

  // UI State helpers
  function setLoading(isLoading, text) {
    if (isLoading) {
      downloadBtn.disabled = true;
      detectTabBtn.disabled = true;
      btnSpinner.classList.remove('hidden');
      btnText.textContent = text || 'Processando...';
    } else {
      downloadBtn.disabled = false;
      detectTabBtn.disabled = false;
      btnSpinner.classList.add('hidden');
      btnText.textContent = 'Baixar Vídeo MP4';
    }
  }

  function showStatus(type, title, message) {
    statusArea.className = `status-card ${type}`;
    statusTitle.textContent = title;
    statusMessage.textContent = message;
    statusArea.classList.remove('hidden');
  }

  // Load and render history
  async function loadHistory() {
    try {
      const data = await chrome.storage.local.get({ history: [] });
      if (!data.history || data.history.length === 0) {
        historyList.innerHTML = '<li class="history-empty">Nenhum download recente.</li>';
        return;
      }

      historyList.innerHTML = '';
      data.history.forEach((item) => {
        const li = document.createElement('li');
        li.className = 'history-item';

        const timeStr = new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        li.innerHTML = `
          <div class="history-item-left">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span class="history-item-name" title="${item.filename}">${item.filename}</span>
          </div>
          <span style="color:#6b7280; font-size:10px;">${timeStr}</span>
        `;
        historyList.appendChild(li);
      });
    } catch (e) {
      console.log('Erro ao carregar histórico:', e);
    }
  }

  // Clear history
  clearHistoryBtn.addEventListener('click', async () => {
    await chrome.storage.local.set({ history: [] });
    loadHistory();
  });
});
