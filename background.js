// Background service worker for InstaReels Downloader

// Helper to extract shortcode from an Instagram URL
function extractShortcode(url) {
  if (!url) return null;
  const match = url.match(/(?:reel|reels|p|tv)\/([A-Za-z0-9_-]+)/i);
  return match ? match[1] : null;
}

// Clean and decode escaped URLs from HTML/JSON
function cleanEscapedUrl(url) {
  if (!url) return null;
  return url
    .replace(/\\u0026/g, '&')
    .replace(/\\/g, '')
    .replace(/&amp;/g, '&');
}

// Save to download history
async function saveToHistory(item) {
  try {
    const data = await chrome.storage.local.get({ history: [] });
    const history = [item, ...data.history.filter(h => h.shortcode !== item.shortcode)].slice(0, 20);
    await chrome.storage.local.set({ history });
  } catch (err) {
    console.error('Erro ao salvar histórico:', err);
  }
}

// Strategy 1: Fetch through Instagram internal endpoint (__d=dis)
async function fetchViaInternalEndpoint(shortcode) {
  try {
    const response = await fetch(`https://www.instagram.com/p/${shortcode}/?__a=1&__d=dis`, {
      headers: {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      credentials: 'include'
    });

    if (!response.ok) return null;
    const json = await response.json();

    // Check item data paths in standard Instagram JSON
    const items = json?.items || json?.graphql?.shortcode_media;
    if (Array.isArray(items) && items.length > 0) {
      const item = items[0];
      if (item.video_versions && item.video_versions.length > 0) {
        return item.video_versions[0].url;
      }
    } else if (items?.video_url) {
      return items.video_url;
    }
  } catch (e) {
    console.log('Strategy 1 failed:', e);
  }
  return null;
}

// Strategy 2: Fetch HTML page and parse metadata / embedded JSON
async function fetchViaHtmlScrape(shortcode) {
  try {
    const response = await fetch(`https://www.instagram.com/reel/${shortcode}/`, {
      headers: {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      },
      credentials: 'include'
    });

    if (!response.ok) return null;
    const html = await response.text();

    // 1. Check og:video meta tags
    const ogMatch = html.match(/<meta[^>]*property=["']og:video(?::secure_url)?["'][^>]*content=["']([^"']+)["']/i);
    if (ogMatch && ogMatch[1] && ogMatch[1].startsWith('http')) {
      return cleanEscapedUrl(ogMatch[1]);
    }

    // 2. Check JSON data inside scripts
    const videoUrlMatches = [
      ...html.matchAll(/"video_url":\s*"([^"]+)"/g),
      ...html.matchAll(/"browser_native_hd_url":\s*"([^"]+)"/g),
      ...html.matchAll(/"browser_native_sd_url":\s*"([^"]+)"/g)
    ];

    for (const match of videoUrlMatches) {
      if (match && match[1]) {
        const decoded = cleanEscapedUrl(match[1]);
        if (decoded.startsWith('http') && (decoded.includes('.mp4') || decoded.includes('fbcdn') || decoded.includes('cdninstagram'))) {
          return decoded;
        }
      }
    }
  } catch (e) {
    console.log('Strategy 2 failed:', e);
  }
  return null;
}

// Strategy 3: Render via background tab fallback (Guaranteed if logged in or public)
async function fetchViaBackgroundTab(shortcode) {
  return new Promise(async (resolve) => {
    let tab = null;
    let timer = null;

    const cleanup = async () => {
      if (timer) clearTimeout(timer);
      if (tab && tab.id) {
        try {
          await chrome.tabs.remove(tab.id);
        } catch (_) {}
      }
    };

    try {
      tab = await chrome.tabs.create({
        url: `https://www.instagram.com/reel/${shortcode}/`,
        active: false
      });

      // Poll the tab for <video> element
      const maxAttempts = 16;
      let attempts = 0;

      const checkTab = async () => {
        attempts++;
        if (attempts > maxAttempts) {
          await cleanup();
          return resolve(null);
        }

        try {
          const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => {
              const video = document.querySelector('video');
              if (video && video.src && !video.src.startsWith('blob:')) {
                return video.src;
              }
              const source = video ? video.querySelector('source') : null;
              if (source && source.src) {
                return source.src;
              }
              return null;
            }
          });

          if (results && results[0] && results[0].result) {
            const videoUrl = results[0].result;
            await cleanup();
            return resolve(videoUrl);
          }
        } catch (err) {
          // Tab might still be loading
        }

        timer = setTimeout(checkTab, 500);
      };

      // Start checking after 1.5 seconds to let DOM mount
      timer = setTimeout(checkTab, 1500);
    } catch (e) {
      await cleanup();
      resolve(null);
    }
  });
}

// Main function to resolve video URL from an Instagram link
async function resolveInstagramVideo(url) {
  const shortcode = extractShortcode(url);
  if (!shortcode) {
    throw new Error('Link do Instagram inválido. Certifique-se de que é um link de Reel ou Post.');
  }

  console.log(`[InstaDownloader] Tentando resolver vídeo para shortcode: ${shortcode}`);

  // Try Strategy 1
  let videoUrl = await fetchViaInternalEndpoint(shortcode);

  // Try Strategy 2
  if (!videoUrl) {
    videoUrl = await fetchViaHtmlScrape(shortcode);
  }

  // Try Strategy 3 (Render fallback)
  if (!videoUrl) {
    console.log('[InstaDownloader] Usando fallback com aba em background...');
    videoUrl = await fetchViaBackgroundTab(shortcode);
  }

  if (!videoUrl) {
    throw new Error('Não foi possível extrair o vídeo. O perfil pode ser privado ou o Instagram bloqueou o acesso temporariamente.');
  }

  return { videoUrl, shortcode };
}

// Download video using Chrome Downloads API
function triggerDownload(videoUrl, shortcode) {
  const filename = `instagram_reel_${shortcode || Date.now()}.mp4`;

  return new Promise((resolve, reject) => {
    chrome.downloads.download(
      {
        url: videoUrl,
        filename: filename,
        saveAs: false
      },
      (downloadId) => {
        if (chrome.runtime.lastError) {
          return reject(new Error(chrome.runtime.lastError.message));
        }
        resolve({ downloadId, filename });
      }
    );
  });
}

// Message Listener
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'downloadDirect') {
    // Direct URL provided (e.g. from content script)
    const shortcode = extractShortcode(request.pageUrl) || 'video_' + Date.now();
    triggerDownload(request.videoUrl, shortcode)
      .then(async (res) => {
        await saveToHistory({
          shortcode,
          url: request.pageUrl || request.videoUrl,
          filename: res.filename,
          timestamp: Date.now()
        });
        sendResponse({ success: true, downloadId: res.downloadId, filename: res.filename });
      })
      .catch((err) => {
        sendResponse({ success: false, error: err.message });
      });
    return true; // Keep message channel open for async response
  }

  if (request.action === 'resolveAndDownload') {
    (async () => {
      try {
        const { videoUrl, shortcode } = await resolveInstagramVideo(request.url);
        const res = await triggerDownload(videoUrl, shortcode);
        await saveToHistory({
          shortcode,
          url: request.url,
          filename: res.filename,
          timestamp: Date.now()
        });
        sendResponse({ success: true, downloadId: res.downloadId, filename: res.filename, videoUrl });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (request.action === 'extractUrlOnly') {
    (async () => {
      try {
        const { videoUrl, shortcode } = await resolveInstagramVideo(request.url);
        sendResponse({ success: true, videoUrl, shortcode });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }
});
