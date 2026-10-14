// Content script to detect videos and inject download buttons on Instagram

const DOWNLOAD_ICON_SVG = `
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
  <polyline points="7 10 12 15 17 10"></polyline>
  <line x1="12" y1="15" x2="12" y2="3"></line>
</svg>
`;

const CHECK_ICON_SVG = `
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="20 6 9 17 4 12"></polyline>
</svg>
`;

// Helper to find video src
function extractVideoUrl(videoEl) {
  if (!videoEl) return null;
  if (videoEl.src && !videoEl.src.startsWith('blob:')) {
    return videoEl.src;
  }
  const source = videoEl.querySelector('source');
  if (source && source.src) {
    return source.src;
  }
  return null;
}

// Injects the download button next to a video
function injectButtonForVideo(videoEl) {
  if (!videoEl || videoEl.dataset.hasDlButton) return;

  // Find a suitable parent container
  let container = videoEl.closest('article') || 
                  videoEl.closest('div[role="dialog"]') || 
                  videoEl.parentElement?.parentElement;

  if (!container) return;

  // Ensure relative positioning on the container
  const computedStyle = window.getComputedStyle(container);
  if (computedStyle.position === 'static') {
    container.style.position = 'relative';
  }

  // Avoid duplicate buttons in container
  if (container.querySelector('.insta-dl-btn-container')) {
    videoEl.dataset.hasDlButton = 'true';
    return;
  }

  const btnContainer = document.createElement('div');
  btnContainer.className = 'insta-dl-btn-container';

  const btn = document.createElement('button');
  btn.className = 'insta-dl-btn';
  btn.innerHTML = `${DOWNLOAD_ICON_SVG}<span>Baixar Vídeo</span>`;

  btn.addEventListener('click', async (e) => {
    e.preventDefault();
    e.stopPropagation();

    const videoSrc = extractVideoUrl(videoEl);
    const pageUrl = window.location.href;

    btn.classList.add('loading');
    btn.innerHTML = `<span>Baixando...</span>`;

    if (videoSrc) {
      chrome.runtime.sendMessage(
        {
          action: 'downloadDirect',
          videoUrl: videoSrc,
          pageUrl: pageUrl
        },
        (response) => {
          btn.classList.remove('loading');
          if (response && response.success) {
            btn.classList.add('success');
            btn.innerHTML = `${CHECK_ICON_SVG}<span>Baixado!</span>`;
            setTimeout(() => {
              btn.classList.remove('success');
              btn.innerHTML = `${DOWNLOAD_ICON_SVG}<span>Baixar Vídeo</span>`;
            }, 3000);
          } else {
            alert('Falha ao baixar vídeo direto. Tentando via link...');
            triggerFallbackDownload(pageUrl, btn);
          }
        }
      );
    } else {
      triggerFallbackDownload(pageUrl, btn);
    }
  });

  btnContainer.appendChild(btn);
  container.appendChild(btnContainer);
  videoEl.dataset.hasDlButton = 'true';
}

function triggerFallbackDownload(pageUrl, btn) {
  chrome.runtime.sendMessage(
    {
      action: 'resolveAndDownload',
      url: pageUrl
    },
    (res) => {
      btn.classList.remove('loading');
      if (res && res.success) {
        btn.classList.add('success');
        btn.innerHTML = `${CHECK_ICON_SVG}<span>Baixado!</span>`;
        setTimeout(() => {
          btn.classList.remove('success');
          btn.innerHTML = `${DOWNLOAD_ICON_SVG}<span>Baixar Vídeo</span>`;
        }, 3000);
      } else {
        btn.innerHTML = `${DOWNLOAD_ICON_SVG}<span>Erro</span>`;
        alert('Erro ao baixar vídeo: ' + (res?.error || 'Não foi possível encontrar a mídia.'));
      }
    }
  );
}

// Scan for videos on the page
function scanVideos() {
  const videos = document.querySelectorAll('video');
  videos.forEach((video) => {
    injectButtonForVideo(video);
  });
}

// Continuous observer for infinite scroll / SPA navigation
const observer = new MutationObserver(() => {
  scanVideos();
});

observer.observe(document.body, {
  childList: true,
  subtree: true
});

// Run initial scan
scanVideos();
setInterval(scanVideos, 2000);

// Helper for popup: find the most visible video on screen
function getMostVisibleVideo() {
  const videos = Array.from(document.querySelectorAll('video'));
  let bestVideo = null;
  let maxVisibleHeight = 0;

  for (const v of videos) {
    const rect = v.getBoundingClientRect();
    const visibleTop = Math.max(0, rect.top);
    const visibleBottom = Math.min(window.innerHeight, rect.bottom);
    const visibleHeight = Math.max(0, visibleBottom - visibleTop);

    if (visibleHeight > maxVisibleHeight) {
      maxVisibleHeight = visibleHeight;
      bestVideo = v;
    }
  }

  return bestVideo || videos[0] || null;
}

// Listen for queries from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getCurrentVideoInfo') {
    const activeVideo = getMostVisibleVideo();
    const videoSrc = extractVideoUrl(activeVideo);
    sendResponse({
      pageUrl: window.location.href,
      videoSrc: videoSrc,
      hasVideo: !!activeVideo
    });
    return true;
  }
});
