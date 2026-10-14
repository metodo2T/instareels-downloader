import os
import re
import time
import imageio_ffmpeg
import yt_dlp

class InstagramDownloader:
    def __init__(self, output_dir=None):
        if output_dir is None:
            self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos_baixados")
        else:
            self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)
        self.ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    def extract_shortcode(self, url):
        match = re.search(r'/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)', url)
        return match.group(1) if match else None

    def clean_url(self, url):
        # Strips tracking parameters from url
        match = re.search(r'(https?://(?:www\.)?instagram\.com/(?:reel|reels|p|tv)/[A-Za-z0-9_-]+)', url)
        if match:
            return match.group(1) + "/"
        return url.strip()

    def download_video(self, url, progress_callback=None):
        """
        Downloads the video from the Instagram URL.
        progress_callback: function(percent: float, status_str: str)
        Returns: dict with details (filepath, title, shortcode, duration, etc.)
        """
        url = self.clean_url(url)
        shortcode = self.extract_shortcode(url) or f"video_{int(time.time())}"
        
        out_template = os.path.join(self.output_dir, f"Reel_{shortcode}_%(id)s.%(ext)s")

        def ydl_hook(d):
            if progress_callback:
                status = d.get('status')
                if status == 'downloading':
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes', 0)
                    speed = d.get('speed') or 0
                    
                    if total_bytes > 0:
                        percent = (downloaded / total_bytes) * 100.0
                    else:
                        percent = 0.0

                    speed_mb = speed / (1024 * 1024) if speed else 0
                    msg = f"Baixando: {percent:.1f}% ({speed_mb:.2f} MB/s)"
                    progress_callback(percent, msg)
                elif status == 'finished':
                    progress_callback(100.0, "Processando e finalizando o arquivo MP4...")

        ydl_opts = {
            'outtmpl': out_template,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'ffmpeg_location': self.ffmpeg_path,
            'progress_hooks': [ydl_hook],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if progress_callback:
                    progress_callback(5.0, "Conectando ao Instagram...")

                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)

                # Ensure filename has .mp4
                base, _ = os.path.splitext(downloaded_file)
                mp4_file = base + ".mp4"
                final_file = mp4_file if os.path.exists(mp4_file) else downloaded_file

                file_size_mb = os.path.getsize(final_file) / (1024 * 1024) if os.path.exists(final_file) else 0

                return {
                    "success": True,
                    "filepath": final_file,
                    "filename": os.path.basename(final_file),
                    "shortcode": shortcode,
                    "title": info.get('title') or f"Reel {shortcode}",
                    "duration": info.get('duration', 0),
                    "size_mb": round(file_size_mb, 2)
                }

        except Exception as e:
            err_msg = str(e)
            if "Private video" in err_msg or "login" in err_msg.lower():
                err_clean = "Este vídeo é de uma conta privada ou requer login."
            elif "not found" in err_msg.lower():
                err_clean = "Vídeo não encontrado ou link incorreto."
            else:
                err_clean = f"Erro no download: {err_msg[:120]}"

            return {
                "success": False,
                "error": err_clean
            }
